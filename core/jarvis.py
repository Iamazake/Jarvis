# -*- coding: utf-8 -*-
"""
JARVIS - Classe Principal
O assistente virtual completo

Autor: JARVIS Team
Versão: 3.0.0
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from pathlib import Path

from .orchestrator import Orchestrator
from .context_manager import ContextManager
from .config import Config

logger = logging.getLogger(__name__)


class Jarvis:
    """
    Classe principal do JARVIS - O assistente virtual
    
    Uso:
        jarvis = Jarvis()
        await jarvis.start()
        response = await jarvis.process("Olá Jarvis!")
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = Config(config_path)
        self.orchestrator = Orchestrator(self.config)
        self.context = ContextManager()
        
        self._running = False
        self._start_time: Optional[datetime] = None
        self._callbacks: Dict[str, list] = {
            'on_message': [],
            'on_response': [],
            'on_error': [],
            'on_proactive': []
        }
        
        # Estado do assistente
        self.name = self.config.get('JARVIS_NAME', 'Jarvis')
        self.wake_word = self.config.get('JARVIS_WAKE_WORD', 'jarvis')
        self.language = self.config.get('JARVIS_LANGUAGE', 'pt-BR')
        
        logger.info(f"🤖 {self.name} inicializado")
    
    async def start(self):
        """Inicia o JARVIS e todos os módulos"""
        if self._running:
            logger.warning("JARVIS já está rodando")
            return
        
        logger.info(f"🚀 Iniciando {self.name}...")
        self._start_time = datetime.now()
        self._running = True
        
        # Inicializa o orquestrador (carrega todos os módulos)
        await self.orchestrator.start()
        
        # Inicia loop de autonomia (ações proativas)
        asyncio.create_task(self._autonomy_loop())
        
        logger.info(f"✅ {self.name} pronto!")
        return self
    
    async def stop(self):
        """Para o JARVIS graciosamente"""
        if not self._running:
            return
        
        logger.info(f"🛑 Parando {self.name}...")
        self._running = False
        
        await self.orchestrator.stop()
        
        logger.info(f"👋 {self.name} finalizado")
    
    async def process(self, message: str, source: str = "cli", metadata: Dict = None) -> str:
        """
        Processa uma mensagem do usuário
        
        Args:
            message: Texto da mensagem
            source: Origem (cli, voice, whatsapp)
            metadata: Dados extras (contato, etc)
        
        Returns:
            Resposta do JARVIS
        """
        if not self._running:
            return "⚠️ JARVIS não está ativo. Use jarvis.start() primeiro."
        
        metadata = metadata or {}
        
        # Notifica callbacks
        await self._emit('on_message', message, source, metadata)
        
        try:
            # Adiciona ao contexto
            self.context.add_message('user', message, source)
            
            # Verifica se há rascunho pendente e o usuário quer enviar
            pending_draft = self.context.get_session("pending_draft")
            if pending_draft and self._is_draft_confirm(message):
                self.context.set_session("pending_draft", None)
                wm = self.orchestrator.modules.get('whatsapp')
                if wm:
                    result = await wm.send_message(pending_draft['to'], pending_draft['message'])
                    response = f"🤖 *Enviando o rascunho...*\n\n{result}"
                    self.context.add_message('assistant', response, source)
                    return response
                return "❌ Módulo WhatsApp não disponível."

            # Processa via orquestrador (pode retornar metadata para contexto)
            result = await self.orchestrator.process(
                message=message,
                context=self.context.get_context(),
                source=source,
                metadata=metadata
            )
            if isinstance(result, tuple) and len(result) >= 2:
                response, out_meta = result[0], result[1] or {}
            else:
                response, out_meta = result, {}

            # Plano de execução: travar ou limpar
            if out_meta.get("pending_plan") is not None:
                self.context.set_pending_plan(out_meta["pending_plan"])
            if out_meta.get("clear_pending_plan"):
                self.context.clear_pending_plan()

            # Sugestão de envio ("Quer que eu envie para X?" → guardar para próximo "sim")
            if out_meta.get("set_suggested_send") is not None:
                self.context.set_session("suggested_send", out_meta["set_suggested_send"])
            if out_meta.get("clear_suggested_send"):
                self.context.set_session("suggested_send", None)

            # Atualiza contexto de curto prazo (ex: último contato mencionado)
            if out_meta.get("last_contact"):
                self.context.set_last_contact(out_meta["last_contact"])
            if out_meta.get("monitored_contact"):
                self.context.add_monitored_contact(out_meta["monitored_contact"])
            if out_meta.get("last_intent"):
                self.context.set_last_intent(out_meta["last_intent"])

            # Cache: última mensagem enviada para contato
            if out_meta.get("last_contact") and out_meta.get("sent_text"):
                self.context.update_last_message(
                    out_meta["last_contact"], out_meta["sent_text"], from_me=True
                )

            # Draft (modo copiloto) — guarda no contexto da sessão
            if out_meta.get("draft"):
                self.context.set_session("pending_draft", out_meta["draft"])

            # Adiciona resposta ao contexto
            self.context.add_message('assistant', response, source)
            
            # Notifica callbacks
            await self._emit('on_response', response, source)
            
            return response
            
        except Exception as e:
            logger.error(f"Erro ao processar: {e}")
            await self._emit('on_error', str(e))
            return f"Desculpe, ocorreu um erro: {str(e)}"
    
    @staticmethod
    def _is_draft_confirm(message: str) -> bool:
        """Detecta se o usuário quer enviar o rascunho pendente."""
        msg = message.strip().lower()
        confirms = [
            'envia', 'envie', 'envia aí', 'envie aí', 'pode enviar',
            'manda', 'mande', 'envia isso', 'pode mandar',
            'sim', 'sim envia', 'ok envia', 'ok manda',
            'envia isso aí', 'pode enviar sim', 'envia sim',
            'yes', 'ok', 'confirma', 'confirme',
        ]
        return msg in confirms

    async def _autonomy_loop(self):
        """Loop para ações proativas (sugestões, lembretes, etc)"""
        while self._running:
            try:
                # Verifica a cada 60 segundos por ações proativas
                await asyncio.sleep(60)
                
                if not self._running:
                    break
                
                # Pede ao orquestrador para verificar ações proativas
                proactive = await self.orchestrator.check_proactive()
                
                if proactive:
                    await self._emit('on_proactive', proactive)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no loop de autonomia: {e}")
    
    def on(self, event: str, callback: Callable):
        """
        Registra callback para eventos
        
        Events:
            - on_message: Quando recebe mensagem
            - on_response: Quando gera resposta
            - on_error: Quando ocorre erro
            - on_proactive: Ação proativa (lembrete, sugestão)
        """
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    async def _emit(self, event: str, *args):
        """Emite evento para callbacks registrados"""
        for callback in self._callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args)
                else:
                    callback(*args)
            except Exception as e:
                logger.error(f"Erro em callback {event}: {e}")
    
    @property
    def uptime(self) -> str:
        """Retorna tempo de atividade formatado"""
        if not self._start_time:
            return "Não iniciado"
        
        delta = datetime.now() - self._start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return f"{hours}h {minutes}m {seconds}s"
    
    @property
    def status(self) -> Dict[str, Any]:
        """Retorna status completo do JARVIS"""
        return {
            'name': self.name,
            'running': self._running,
            'uptime': self.uptime,
            'modules': self.orchestrator.get_modules_status() if self._running else {},
            'context_size': len(self.context.messages),
            'version': '3.0.0'
        }
    
    def __repr__(self):
        status = "🟢 Online" if self._running else "🔴 Offline"
        return f"<Jarvis '{self.name}' {status}>"


# Singleton para acesso global
_jarvis_instance: Optional[Jarvis] = None

def get_jarvis() -> Jarvis:
    """Retorna instância global do JARVIS"""
    global _jarvis_instance
    if _jarvis_instance is None:
        _jarvis_instance = Jarvis()
    return _jarvis_instance
