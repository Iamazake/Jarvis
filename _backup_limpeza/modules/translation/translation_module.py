# -*- coding: utf-8 -*-
"""
Translation Module - Módulo de Tradução e Suporte Multilíngue
Detecção de idioma e tradução

Autor: JARVIS Team
Versão: 3.1.0
"""

from typing import Dict, Any, Optional

from core.logger import get_logger
from .translator import Translator, Language

logger = get_logger(__name__)


class TranslationModule:
    """
    Módulo de tradução.
    
    Funcionalidades:
    - Detecção automática de idioma
    - Tradução de mensagens (via API quando disponível)
    - Respostas no idioma do usuário
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._running = False
        self.status = '🔴'
        self.translator = Translator(config)
    
    async def start(self):
        """Inicializa o módulo."""
        logger.info("🌐 Iniciando módulo de tradução...")
        self._running = True
        self.status = '🟢'
        logger.info("✅ Módulo de tradução pronto")
    
    async def stop(self):
        """Para o módulo."""
        self._running = False
        self.status = '🔴'
    
    def detect(self, text: str) -> Language:
        """Detecta idioma do texto."""
        return self.translator.detect_language(text)
    
    def translate(self, text: str, target_lang: str = 'pt', source_lang: Optional[str] = None) -> str:
        """Traduz texto."""
        return self.translator.translate(text, target_lang=target_lang, source_lang=source_lang)
    
    async def process(
        self,
        message: str,
        intent,
        context: Dict,
        metadata: Dict
    ) -> str:
        """Processa comandos do módulo."""
        msg_lower = message.lower().strip()
        
        if 'detectar idioma' in msg_lower or 'qual idioma' in msg_lower:
            lang = self.detect(message)
            return f"🌐 Idioma detectado: **{lang.value}**"
        
        if 'traduzir' in msg_lower or 'traduza' in msg_lower:
            # Extrair texto e idioma alvo se possível
            to_translate = message.replace('traduzir', '').replace('traduza', '').strip()
            if ' para ' in to_translate:
                part, target = to_translate.split(' para ', 1)
                to_translate = part.strip()
                target = target.strip().lower()[:2]
            else:
                target = 'pt'
            if not to_translate:
                return "Use: 'traduzir [texto] para [pt/en/es]'"
            result = self.translate(to_translate, target_lang=target)
            return f"🌐 **Tradução** ({target}):\n{result}"
        
        return "Comandos: 'detectar idioma [texto]', 'traduzir [texto] para pt'"
    
    def is_available(self) -> bool:
        return self._running
