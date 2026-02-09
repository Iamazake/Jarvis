"""
JARVIS Monitors - Sistema de Monitoramento
Implementa Observer Pattern para reagir a eventos WhatsApp
"""

from .base import AbstractMonitor
from .keyword import KeywordMonitor
from .contact import ContactMonitor
from .media import MediaMonitor
from .presence import PresenceMonitor
from .manager import MonitorManager, load_monitors_from_config

__all__ = [
    'AbstractMonitor',
    'KeywordMonitor',
    'ContactMonitor', 
    'MediaMonitor',
    'PresenceMonitor',
    'MonitorManager',
    'load_monitors_from_config'
]
