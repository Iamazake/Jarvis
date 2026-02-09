# -*- coding: utf-8 -*-
"""Módulo de Tradução e detecção de idioma."""
import logging
from typing import Dict, Any, Optional
from .translator import Translator, Language

logger = logging.getLogger(__name__)


class TranslationModule:
    def __init__(self, config):
        self.config = config
        self._running = False
        self.status = '🔴'
        self.translator = Translator(config)

    async def start(self):
        logger.info("🌐 Iniciando módulo de tradução...")
        self._running = True
        self.status = '🟢'

    async def stop(self):
        self._running = False
        self.status = '🔴'

    def detect(self, text: str) -> Language:
        return self.translator.detect_language(text)

    def translate(self, text: str, target_lang: str = 'pt', source_lang: Optional[str] = None) -> str:
        return self.translator.translate(text, target_lang=target_lang, source_lang=source_lang)

    async def process(self, message: str, intent, context: Dict, metadata: Dict) -> str:
        msg_lower = message.lower().strip()
        if 'detectar idioma' in msg_lower or 'qual idioma' in msg_lower:
            lang = self.detect(message)
            return f"🌐 Idioma detectado: **{lang.value}**"
        if 'traduzir' in msg_lower or 'traduza' in msg_lower:
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
        return "Comandos: 'detectar idioma', 'traduzir [texto] para [pt/en/es]'"
