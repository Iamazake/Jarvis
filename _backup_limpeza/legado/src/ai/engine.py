# -*- coding: utf-8 -*-
"""
AI Engine - Motor de IA com Cache Semântico
Facade Pattern: Interface unificada para IA + Cache

Autor: JARVIS Team
Versão: 4.0.0
"""

import time
import logging
from typing import List, Dict, Tuple, Optional

from .providers import AIProvider, ProviderFactory

logger = logging.getLogger(__name__)

# Tentar importar cache
try:
    from src.cache import SemanticCache
    HAS_CACHE = True
except ImportError:
    HAS_CACHE = False
    SemanticCache = None


class AIEngine:
    """
    Motor de IA com Cache Semântico
    
    Uso:
        engine = AIEngine({"provider": "openai", "api_key": "..."})
        response, meta = engine.generate(profile, "Oi!", "Responda com carinho")
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.provider: Optional[AIProvider] = None
        self.cache = None
        
        self._setup_provider()
        self._setup_cache()
    
    def _setup_provider(self):
        """Configura provider de IA"""
        provider_type = self.config.get("provider", "openai")
        self.provider = ProviderFactory.create(provider_type, self.config)
        
        if self.provider and self.provider.is_available():
            logger.info(f"✅ IA: {provider_type}")
        else:
            logger.warning(f"⚠️ IA indisponível: {provider_type}")
    
    def _setup_cache(self):
        """Configura cache semântico"""
        if not self.config.get("use_cache", True) or not HAS_CACHE:
            return
        
        try:
            self.cache = SemanticCache()
            logger.info("✅ Cache semântico ativo")
        except Exception as e:
            logger.warning(f"⚠️ Cache: {e}")
    
    def generate(self,
                 profile: Dict,
                 message: str,
                 instruction: str = "",
                 history: List[Dict] = None) -> Tuple[str, Dict]:
        """Gera resposta usando IA"""
        start_time = time.time()
        
        # Tentar cache primeiro
        if self.cache:
            try:
                cached = self.cache.get(message)
                if cached:
                    logger.info("⚡ Cache hit!")
                    return cached, {"source": "cache", "time_ms": 1}
            except:
                pass
        
        # Gerar com IA
        if not self.provider or not self.provider.is_available():
            return self._fallback(profile), {"source": "fallback"}
        
        system = self._build_system_prompt(profile)
        messages = self._build_messages(profile, message, instruction, history)
        
        response, metadata = self.provider.generate(system, messages)
        
        if not response:
            response = self._fallback(profile)
            metadata["source"] = "fallback"
        else:
            metadata["source"] = "ai"
            if self.cache:
                try:
                    self.cache.set(message, response)
                except:
                    pass
        
        metadata["time_ms"] = int((time.time() - start_time) * 1000)
        return response, metadata
    
    def _build_system_prompt(self, profile: Dict) -> str:
        """Constrói prompt do sistema"""
        tone = profile.get("tone", "casual")
        emoji = profile.get("emoji_frequency", "moderado")
        context = profile.get("context", "")
        
        prompt = f"""Você escreve mensagens de WhatsApp em nome do usuário.

ESTILO:
- Tom: {tone}
- Emojis: {emoji}

REGRAS:
1. Escreva APENAS a mensagem, sem explicações
2. Seja natural e humano
3. Mantenha consistência
"""
        if context:
            prompt += f"\nCONTEXTO: {context}"
        
        return prompt
    
    def _build_messages(self, profile: Dict, message: str, instruction: str, history: List[Dict] = None) -> List[Dict]:
        """Constrói mensagens para API"""
        messages = []
        
        if history:
            messages.extend(history[-10:])
        
        content = f'Mensagem de {profile.get("name", "contato")}: "{message}"\n'
        content += instruction if instruction else "Responda naturalmente."
        
        messages.append({"role": "user", "content": content})
        return messages
    
    def _fallback(self, profile: Dict) -> str:
        """Resposta fallback"""
        tone = profile.get("tone", "casual")
        fallbacks = {
            "carinhoso": "Amor, já te respondo! 💕",
            "profissional": "Obrigado, retorno em breve.",
            "casual": "Opa! Já respondo!",
        }
        return fallbacks.get(tone, "Já respondo!")
