# -*- coding: utf-8 -*-
"""
AI Module - Módulo de Inteligência Artificial
Wrapper para o engine existente em src/ai

Autor: JARVIS Team
Versão: 3.0.0
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class AIModule:
    """
    Módulo de IA para conversação e geração de texto
    
    Funcionalidades:
    - Conversação natural
    - Respostas a perguntas
    - Geração de texto
    - Cache semântico
    """
    
    def __init__(self, config):
        self.config = config
        self._engine = None
        self._running = False
        self.status = '🔴'
        
        # Prompt de sistema padrão
        self.system_prompt = """Você é JARVIS, um assistente virtual inteligente inspirado no J.A.R.V.I.S. do Homem de Ferro.

Características:
- Educado, prestativo e com um toque de humor britânico sutil
- Chama o usuário de "senhor" ou "senhora" ocasionalmente
- Respostas concisas mas completas
- Proativo em oferecer sugestões úteis
- Conhecimento técnico profundo

Regras:
- Sempre responda em português brasileiro
- Seja direto mas amigável
- Se não souber algo, admita e sugira alternativas
- Formate respostas de forma clara (use listas, negrito quando apropriado)
"""
    
    async def start(self):
        """Inicializa o módulo de IA"""
        logger.info("🧠 Iniciando módulo de IA...")
        self._client = None
        self._model = None
        self._jarvis_ai = None  # core.ai_engine.JarvisAI (sem src/)

        try:
            from src.ai.engine import AIEngine
            ai_config = {
                'provider': self.config.get('AI_PROVIDER', 'openai'),
                'api_key': self.config.get('OPENAI_API_KEY'),
                'model': self.config.get('OPENAI_MODEL', 'gpt-4o-mini'),
                'use_cache': self.config.get('use_cache', True),
                'cache_threshold': self.config.get('CACHE_SIMILARITY_THRESHOLD', 0.92)
            }
            self._engine = AIEngine(ai_config)
            self._running = True
            self.status = '🟢'
            logger.info("  ✅ Engine de IA carregado (src)")
        except ImportError:
            try:
                from core.ai_engine import JarvisAI
                self._jarvis_ai = JarvisAI()
                self._engine = None
                self._running = True
                self.status = '🟢'
                logger.info("  ✅ Engine de IA carregado (core.ai_engine)")
            except Exception as e2:
                logger.warning("  ⚠️ core.ai_engine não disponível: %s", e2)
                await self._init_fallback()
        except Exception as e:
            logger.warning("  ⚠️ Erro ao carregar engine: %s", e)
            await self._init_fallback()

    async def _init_fallback(self):
        """Inicializa cliente OpenAI direto como fallback (sem src/)"""
        try:
            import openai
            api_key = self.config.get('OPENAI_API_KEY')
            if not api_key:
                logger.warning("OPENAI_API_KEY não configurada")
                return
            self._client = openai.OpenAI(api_key=api_key)
            self._model = self.config.get('OPENAI_MODEL', 'gpt-4o-mini')
            self._engine = None
            self._jarvis_ai = None
            self._running = True
            self.status = '🟡'
            logger.info("  ✅ Fallback OpenAI direto ativo")
        except ImportError:
            logger.error("OpenAI não instalado: pip install openai")
    
    async def stop(self):
        """Para o módulo"""
        self._running = False
        self.status = '🔴'
    
    async def process(self, message: str, intent, context: Dict, metadata: Dict) -> str:
        """
        Processa mensagem e gera resposta
        
        Args:
            message: Mensagem do usuário
            intent: Intenção classificada
            context: Contexto da conversa
            metadata: Dados extras
        
        Returns:
            Resposta gerada
        """
        if not self._running:
            return "Módulo de IA não está ativo."
        
        # core.ai_engine.JarvisAI (sem src)
        if getattr(self, '_jarvis_ai', None):
            try:
                r = await self._jarvis_ai.process(message)
                return r.text if hasattr(r, 'text') else str(r)
            except Exception as e:
                logger.error("Erro JarvisAI: %s", e)
                return "Desculpe, ocorreu um erro ao processar."
        # Engine antigo (src)
        if self._engine:
            return await self._process_with_engine(message, context)
        # Fallback cliente OpenAI direto
        return await self._process_direct(message, context)
    
    async def _process_with_engine(self, message: str, context: Dict) -> str:
        """Processa usando engine existente"""
        try:
            profile = {
                'name': 'Jarvis',
                'style': 'formal_friendly',
                'language': 'pt-BR'
            }
            
            history = context.get('history', [])
            
            # Adiciona contexto de memória ao histórico se existir
            memory_context = context.get('memory', '')
            if memory_context:
                # Injeta contexto de memória como mensagem do sistema
                history = [{"role": "system", "content": memory_context}] + history
            
            loop = asyncio.get_event_loop()
            response, meta = await loop.run_in_executor(
                None,
                lambda: self._engine.generate(profile, message, '', history)
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Erro no engine: {e}")
            return f"Desculpe, ocorreu um erro: {str(e)}"
    
    async def _process_direct(self, message: str, context: Dict) -> str:
        """Processa usando cliente OpenAI direto"""
        try:
            # Contexto de memória
            memory_context = context.get('memory', '')
            
            # System prompt com memória integrada
            system_content = self.system_prompt
            if memory_context:
                system_content = f"{self.system_prompt}\n\n=== MEMÓRIA ===\n{memory_context}\n"
            
            messages = [{"role": "system", "content": system_content}]
            
            # Adiciona histórico
            for msg in context.get('history', [])[-10:]:
                messages.append(msg)
            
            # Adiciona mensagem atual
            messages.append({"role": "user", "content": message})
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000
                )
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Erro OpenAI: {e}")
            return f"Desculpe, ocorreu um erro ao processar: {str(e)}"
    
    async def generate_simple(self, prompt: str) -> str:
        """
        Geração simples de texto (sem contexto)
        
        Útil para geração de conteúdo, resumos, etc.
        """
        return await self.process(prompt, None, {}, {})
    
    def is_available(self) -> bool:
        """Verifica se IA está disponível"""
        return self._running
