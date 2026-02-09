# -*- coding: utf-8 -*-
"""
Módulo IA - Strategy Pattern
Diferentes provedores de IA com interface unificada
"""

from .engine import AIEngine
from .providers import OpenAIProvider, ClaudeProvider, OllamaProvider, ProviderFactory

__all__ = ['AIEngine', 'OpenAIProvider', 'ClaudeProvider', 'OllamaProvider', 'ProviderFactory']
