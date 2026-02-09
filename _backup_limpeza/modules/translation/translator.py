# -*- coding: utf-8 -*-
"""
Translator - Tradutor e Detecção de Idioma
Detecção de idioma e tradução (API ou fallback)

Autor: JARVIS Team
Versão: 3.1.0
"""

from typing import Optional, Tuple
from enum import Enum

from core.logger import get_logger

logger = get_logger(__name__)


class Language(Enum):
    PT = 'pt'
    EN = 'en'
    ES = 'es'
    FR = 'fr'
    UNKNOWN = 'unknown'


class Translator:
    """
    Tradutor com detecção de idioma.
    
    Usa OpenAI ou libs locais se configuradas; senão detecção simples por léxico.
    """
    
    def __init__(self, config: dict):
        self.config = config
        self._openai_available = False
        try:
            import openai
            self._openai_available = bool(config.get('OPENAI_API_KEY'))
        except ImportError:
            pass
    
    def detect_language(self, text: str) -> Language:
        """
        Detecta idioma do texto.
        Fallback: heurística por palavras comuns.
        """
        if not text or len(text.strip()) < 3:
            return Language.UNKNOWN
        
        text_lower = text.strip().lower()
        
        pt_words = ['é', 'ã', 'õ', 'ç', 'que', 'não', 'uma', 'para', 'com', 'por', 'como', 'mais', 'mas', 'foi', 'ele', 'ela', 'ou', 'se', 'ao', 'su']
        en_words = ['the', 'is', 'are', 'was', 'were', 'have', 'has', 'will', 'would', 'could', 'this', 'that', 'with', 'from', 'for']
        es_words = ['el', 'la', 'los', 'las', 'que', 'en', 'un', 'es', 'por', 'con', 'para', 'una', 'del', 'al', 'como']
        
        scores = {
            Language.PT: sum(1 for w in pt_words if w in text_lower),
            Language.EN: sum(1 for w in en_words if w in text_lower),
            Language.ES: sum(1 for w in es_words if w in text_lower),
        }
        
        best = max(scores.items(), key=lambda x: x[1])
        if best[1] > 0:
            return best[0]
        return Language.UNKNOWN
    
    def translate(self, text: str, target_lang: str = 'pt', source_lang: Optional[str] = None) -> str:
        """
        Traduz texto para o idioma alvo.
        
        Se OpenAI disponível, usa API; senão retorna texto com aviso.
        """
        if not text or not text.strip():
            return ""
        
        target_lang = target_lang.lower()[:2]
        lang_names = {'pt': 'português', 'en': 'inglês', 'es': 'espanhol', 'fr': 'francês'}
        target_name = lang_names.get(target_lang, target_lang)
        
        if self._openai_available:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.config.get('OPENAI_API_KEY'))
                prompt = f"Traduza o seguinte texto para {target_name}. Responda apenas com a tradução, sem explicações.\n\n{text}"
                resp = client.chat.completions.create(
                    model=self.config.get('OPENAI_MODEL', 'gpt-4o-mini'),
                    messages=[{'role': 'user', 'content': prompt}],
                    max_tokens=1000
                )
                return (resp.choices[0].message.content or text).strip()
            except Exception as e:
                logger.warning(f"Tradução via API falhou: {e}")
        
        return f"[Tradução para {target_name} requer API. Texto original: {text[:100]}...]"
    
    def translate_to_pt(self, text: str) -> str:
        """Conveniência: traduz para português."""
        return self.translate(text, target_lang='pt')
