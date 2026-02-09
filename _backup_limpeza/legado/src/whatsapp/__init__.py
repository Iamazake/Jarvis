# -*- coding: utf-8 -*-
"""
Módulo WhatsApp - Facade Pattern
Expõe interface simplificada para automação do WhatsApp
"""

from .client import WhatsAppClient
from .handlers import MessageHandler, ContactProfile

__all__ = ['WhatsAppClient', 'MessageHandler', 'ContactProfile']
