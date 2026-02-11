# -*- coding: utf-8 -*-
"""
JARVIS - Classe Principal
O assistente virtual completo

Autor: JARVIS Team
Versão: 3.0.0
"""

import asyncio
import logging
import os
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
        
        # Task do loop de autonomia (cancelada explicitamente em stop())
        self._autonomy_task: Optional[asyncio.Task] = None
        
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
        
        # Inicia loop de autonomia (ações proativas); evita duplicata se start() chamado 2x
        existing = getattr(self, '_autonomy_task', None)
        if existing is not None and not existing.done():
            logger.warning("Loop de autonomia já em execução, não criando outra task")
        else:
            self._autonomy_task = asyncio.create_task(
                self._autonomy_loop(), name="jarvis_autonomy_loop"
            )
        
        logger.info(f"✅ {self.name} pronto!")
        return self
    
    async def stop(self):
        """Para o JARVIS graciosamente"""
        if not self._running:
            return
        
        logger.info(f"🛑 Parando {self.name}...")
        self._running = False
        
        # Cancelar e aguardar task de autonomia com timeout para shutdown determinístico
        task = getattr(self, '_autonomy_task', None)
        if task is not None:
            task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=2.0)
            except asyncio.CancelledError:
                pass
            except asyncio.TimeoutError:
                logger.warning("Timeout aguardando _autonomy_loop encerrar (2s)")
        
        await self.orchestrator.stop()
        
        # Diagnóstico opcional: tasks pendentes no loop (JARVIS_DIAG=1)
        if os.getenv('JARVIS_DIAG', '').strip().lower() in ('1', 'true', 'yes'):
            try:
                loop = asyncio.get_running_loop()
                pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
                if pending:
                    logger.debug("Tasks pendentes após stop: %s", [t.get_name() for t in pending])
            except Exception as e:
                logger.debug("Dump tasks falhou: %s", e)
        
        logger.info(f"👋 {self.name} finalizado")

    async def apply_out_meta(self, out_meta: Dict) -> None:
        """
        Aplica metadados de saída ao contexto (usado por process() e por handlers MCP).
        Atualiza pending_plan, suggested_send, last_contact, autopilot, etc.
        """
        if not out_meta:
            return
        if out_meta.get("pending_plan") is not None:
            self.context.set_pending_plan(out_meta["pending_plan"])
        if out_meta.get("clear_pending_plan"):
            self.context.clear_pending_plan()
        if out_meta.get("set_suggested_send") is not None:
            self.context.set_session("suggested_send", out_meta["set_suggested_send"])
        if out_meta.get("clear_suggested_send"):
            self.context.set_session("suggested_send", None)
        if out_meta.get("last_contact"):
            self.context.set_last_contact(out_meta["last_contact"])
        if out_meta.get("monitored_contact"):
            self.context.add_monitored_contact(out_meta["monitored_contact"])
        if out_meta.get("remove_monitored_contact"):
            self.context.remove_monitored_contact(out_meta["remove_monitored_contact"])
        if out_meta.get("monitored_jid"):
            self.context.set_last_monitored_jid(out_meta["monitored_jid"])
            if out_meta.get("monitored_contact"):
                self.context.set_active_target(
                    out_meta["monitored_jid"], out_meta["monitored_contact"]
                )
        if out_meta.get("last_intent"):
            self.context.set_last_intent(out_meta["last_intent"])
        if out_meta.get("last_contact") and out_meta.get("sent_text"):
            self.context.update_last_message(
                out_meta["last_contact"], out_meta["sent_text"], from_me=True
            )
        if out_meta.get("enable_autopilot"):
            ap = out_meta["enable_autopilot"]
            jid = (ap.get("jid") or "").strip()
            display_name = (ap.get("contact") or "").strip()
            tone = ap.get("tone") or "fofinho"
            ttl = int(
                ap.get("ttl_minutes")
                or self.config.get("AUTOPILOT_DEFAULT_TTL_MINUTES", 120)
            )
            if jid and "@" in jid:
                self.context.enable_autopilot(
                    jid,
                    display_name=display_name or None,
                    tone=tone,
                    ttl_minutes=ttl,
                )
                if display_name:
                    self.context.set_active_target(jid, display_name)
            elif display_name:
                self.context.enable_autopilot(
                    display_name,
                    display_name=display_name,
                    tone=tone,
                    ttl_minutes=ttl,
                )
        if out_meta.get("disable_autopilot"):
            ap = out_meta["disable_autopilot"]
            contact = (ap.get("contact") or "").strip()
            if contact:
                ok, removed_info = self.context.disable_autopilot(contact)
                if ok and removed_info and removed_info.get("jid") and removed_info.get("created_at"):
                    try:
                        await asyncio.wait_for(self._generate_summary_on_disable(removed_info), timeout=3.0)
                    except asyncio.TimeoutError:
                        logger.warning("Timeout ao gerar resumo ao desativar autopilot (jid=%s)", removed_info.get("jid"))
                    except Exception as e:
                        logger.warning("Falha ao gerar resumo ao desativar autopilot: %s", e)
        if out_meta.get("update_autopilot_tone"):
            ut = out_meta["update_autopilot_tone"]
            jid = (ut.get("jid") or "").strip()
            contact = (ut.get("contact") or "").strip()
            tone = (ut.get("tone") or "profissional").strip()
            if jid or contact:
                self.context.update_autopilot_tone(jid or contact, tone)
        if out_meta.get("draft"):
            self.context.set_session("pending_draft", out_meta["draft"])

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
            # Adiciona ao contexto (metadata com jid para histórico por contato no WhatsApp)
            self.context.add_message('user', message, source, metadata)
            
            # Verifica se há rascunho pendente e o usuário quer enviar
            pending_draft = self.context.get_session("pending_draft")
            if pending_draft and self._is_draft_confirm(message):
                self.context.set_session("pending_draft", None)
                wm = self.orchestrator.modules.get('whatsapp')
                if wm:
                    result = await wm.send_message(pending_draft['to'], pending_draft['message'])
                    response = f"🤖 *Enviando o rascunho...*\n\n{result}"
                    self.context.add_message('assistant', response, source, metadata)
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

            await self.apply_out_meta(out_meta)

            # Nunca responder "não tenho capacidade" em fluxos WhatsApp; substituir por mensagem útil
            response = self._sanitize_whatsapp_response(response)

            if response is None and os.getenv('JARVIS_DIAG', '').strip().lower() in ('1', 'true', 'yes'):
                logger.info(
                    "no_response: pipeline returned None intent=%s",
                    out_meta.get('last_intent', ''),
                )

            # Adiciona resposta ao contexto (e ao histórico por JID quando WhatsApp)
            self.context.add_message('assistant', response, source, metadata)
            
            # Notifica callbacks
            await self._emit('on_response', response, source)
            
            return response
            
        except Exception as e:
            logger.error(f"Erro ao processar: {e}")
            await self._emit('on_error', str(e))
            return f"Desculpe, ocorreu um erro: {str(e)}"

    async def _generate_summary_on_disable(self, removed_info: Dict) -> None:
        """Chama API para gerar resumo do período em que o autopilot esteve ativo (fire-and-forget)."""
        try:
            import aiohttp
            api_url = os.getenv("JARVIS_API_URL", "http://127.0.0.1:5000").rstrip("/")
            period_start = removed_info.get("created_at")
            if hasattr(period_start, "strftime"):
                period_start = period_start.strftime("%Y-%m-%d %H:%M:%S")
            period_end = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            headers = {}
            if os.getenv("JARVIS_INTERNAL_SECRET"):
                headers["X-Jarvis-Internal"] = os.getenv("JARVIS_INTERNAL_SECRET")
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"{api_url}/internal/generate-autopilot-summary",
                    json={"jid": removed_info["jid"], "period_start": period_start, "period_end": period_end},
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                )
        except Exception as e:
            logger.warning("Falha ao gerar resumo ao desativar autopilot: %s", e)
    
    @staticmethod
    def _sanitize_whatsapp_response(response: str) -> str:
        """Substitui respostas proibidas (ex.: 'não tenho capacidade de monitorar') por mensagem útil."""
        if not response or not isinstance(response, str):
            return response
        r = response.strip().lower()
        forbidden = (
            'não tenho a capacidade',
            'não tenho capacidade',
            'não posso monitorar',
            'não consigo monitorar',
            'não tenho como monitorar',
            'capacidade de monitorar',
            'monitorar pessoas',
            'monitorar interações',
        )
        if any(f in r for f in forbidden):
            return (
                "Não consegui identificar o contato. Diga o nome de quem você quer monitorar ou ativar autopilot "
                "(ex.: monitore o contato Tchuchuca e quando ela mandar mensagem, entretenha)."
            )
        return response

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
