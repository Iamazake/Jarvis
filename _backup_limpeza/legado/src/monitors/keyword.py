"""
Keyword Monitor - Detecta palavras-chave nas mensagens
"""

import re
from typing import List, Set
from .base import AbstractMonitor


class KeywordMonitor(AbstractMonitor):
    """
    Monitora mensagens buscando palavras-chave específicas.
    Útil para detectar assuntos importantes em conversas de grupo.
    """
    
    def __init__(self, notifier_jid: str, keywords: List[str], 
                 case_sensitive: bool = False, whole_word: bool = True):
        """
        Args:
            notifier_jid: JID que recebe alertas
            keywords: Lista de palavras/frases a monitorar
            case_sensitive: Se True, diferencia maiúsculas/minúsculas
            whole_word: Se True, só detecta palavras inteiras (não parciais)
        """
        super().__init__(notifier_jid, "KeywordMonitor")
        self.keywords: Set[str] = set(keywords)
        self.case_sensitive = case_sensitive
        self.whole_word = whole_word
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compila regex patterns para busca eficiente"""
        self._patterns = {}
        for kw in self.keywords:
            pattern = re.escape(kw)
            if self.whole_word:
                pattern = rf'\b{pattern}\b'
            flags = 0 if self.case_sensitive else re.IGNORECASE
            self._patterns[kw] = re.compile(pattern, flags)
    
    def add_keyword(self, keyword: str):
        """Adiciona nova palavra-chave"""
        self.keywords.add(keyword)
        pattern = re.escape(keyword)
        if self.whole_word:
            pattern = rf'\b{pattern}\b'
        flags = 0 if self.case_sensitive else re.IGNORECASE
        self._patterns[keyword] = re.compile(pattern, flags)
    
    def remove_keyword(self, keyword: str):
        """Remove palavra-chave"""
        self.keywords.discard(keyword)
        self._patterns.pop(keyword, None)
    
    def update(self, event: dict) -> None:
        """
        Processa evento de mensagem.
        Se encontrar keyword, envia notificação.
        """
        if not self.enabled or event.get('type') != 'message':
            return
        
        data = event.get('data', {})
        text = data.get('text', '')
        
        if not text:
            return
        
        # Busca keywords no texto
        found = []
        for kw, pattern in self._patterns.items():
            if pattern.search(text):
                found.append(kw)
        
        if found:
            sender = event.get('push_name', event.get('sender', 'Desconhecido'))
            preview = text[:100] + ('...' if len(text) > 100 else '')
            
            alert = (
                f"⚠️ Palavra detectada!\n"
                f"👤 De: {sender}\n"
                f"🔑 Keywords: {', '.join(found)}\n"
                f"💬 Mensagem: {preview}"
            )
            self.notify(alert)
    
    def list_keywords(self) -> List[str]:
        """Retorna lista de keywords ativas"""
        return list(self.keywords)
    
    def __repr__(self):
        return f"<KeywordMonitor keywords={len(self.keywords)} enabled={self.enabled}>"
