# -*- coding: utf-8 -*-
"""Detecção de idioma e tradução (OpenAI se disponível)."""
import logging
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


def _config_get(c, key, default=None):
    return c.get(key, default) if hasattr(c, 'get') and callable(getattr(c, 'get')) else getattr(c, key, default)


class Language(Enum):
    PT = 'pt'
    EN = 'en'
    ES = 'es'
    FR = 'fr'
    UNKNOWN = 'unknown'


class Translator:
    def __init__(self, config):
        self.config = config
        self._openai_available = bool(_config_get(config, 'OPENAI_API_KEY'))
        try:
            import openai
        except ImportError:
            self._openai_available = False

    def detect_language(self, text: str) -> Language:
        if not text or len(text.strip()) < 3:
            return Language.UNKNOWN
        text_lower = text.strip().lower()
        pt_words = ['é', 'ã', 'õ', 'ç', 'que', 'não', 'uma', 'para', 'com', 'por', 'como', 'mais', 'mas', 'foi']
        en_words = ['the', 'is', 'are', 'was', 'were', 'have', 'has', 'will', 'would', 'could', 'this', 'that']
        es_words = ['el', 'la', 'los', 'las', 'que', 'en', 'un', 'es', 'por', 'con', 'para', 'una']
        scores = {
            Language.PT: sum(1 for w in pt_words if w in text_lower),
            Language.EN: sum(1 for w in en_words if w in text_lower),
            Language.ES: sum(1 for w in es_words if w in text_lower),
        }
        best = max(scores.items(), key=lambda x: x[1])
        return best[0] if best[1] > 0 else Language.UNKNOWN

    def translate(self, text: str, target_lang: str = 'pt', source_lang: Optional[str] = None) -> str:
        if not text or not text.strip():
            return ""
        target_lang = target_lang.lower()[:2]
        lang_names = {'pt': 'português', 'en': 'inglês', 'es': 'espanhol', 'fr': 'francês'}
        target_name = lang_names.get(target_lang, target_lang)
        if self._openai_available:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=_config_get(self.config, 'OPENAI_API_KEY'))
                prompt = f"Traduza o seguinte texto para {target_name}. Responda apenas com a tradução.\n\n{text}"
                resp = client.chat.completions.create(
                    model=_config_get(self.config, 'OPENAI_MODEL', 'gpt-4o-mini'),
                    messages=[{'role': 'user', 'content': prompt}],
                    max_tokens=1000
                )
                return (resp.choices[0].message.content or text).strip()
            except Exception as e:
                logger.warning("Tradução API falhou: %s", e)
        return f"[Tradução para {target_name} requer OPENAI_API_KEY. Original: {text[:80]}...]"
