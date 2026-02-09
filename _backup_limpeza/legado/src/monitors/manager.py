"""
Monitor Manager - Gerenciador Central de Monitors
Implementa Facade Pattern
"""

import json
from pathlib import Path
from typing import List, Optional
import logging

from .base import AbstractMonitor

logger = logging.getLogger('jarvis.monitors')


class MonitorManager:
    """
    Gerenciador central de monitors.
    Implementa Facade Pattern para simplificar uso.
    """
    
    _instance = None  # Singleton
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._monitors = []
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._monitors: List[AbstractMonitor] = []
        self._initialized = True
    
    def add(self, monitor: AbstractMonitor):
        """Adiciona monitor ao gerenciador"""
        self._monitors.append(monitor)
        logger.info(f"Monitor adicionado: {monitor}")
    
    def remove(self, monitor: AbstractMonitor):
        """Remove monitor"""
        if monitor in self._monitors:
            self._monitors.remove(monitor)
            logger.info(f"Monitor removido: {monitor}")
    
    def dispatch(self, event: dict):
        """
        Envia evento para todos os monitors (Observer pattern).
        Chamado pelo handlers.py quando recebe mensagem/evento.
        """
        for monitor in self._monitors:
            try:
                monitor.update(event)
            except Exception as e:
                logger.error(f"Erro no {monitor.name}: {e}")
    
    def enable_all(self):
        """Ativa todos os monitors"""
        for m in self._monitors:
            m.enable()
    
    def disable_all(self):
        """Desativa todos os monitors"""
        for m in self._monitors:
            m.disable()
    
    def list_monitors(self) -> List[str]:
        """Lista monitors ativos"""
        return [repr(m) for m in self._monitors]
    
    def get_monitor(self, name: str) -> Optional[AbstractMonitor]:
        """Busca monitor por nome"""
        for m in self._monitors:
            if m.name == name:
                return m
        return None
    
    def clear(self):
        """Remove todos os monitors"""
        self._monitors.clear()
    
    def __len__(self):
        return len(self._monitors)
    
    def __repr__(self):
        return f"<MonitorManager monitors={len(self._monitors)}>"


def load_monitors_from_config(config_path: str = "config/monitors.json") -> MonitorManager:
    """
    Carrega configuração e cria monitors.
    Factory function para setup inicial.
    
    Returns:
        MonitorManager configurado com todos os monitors
    """
    # Imports locais para evitar circular
    from .keyword import KeywordMonitor
    from .contact import ContactMonitor
    from .media import MediaMonitor
    from .presence import PresenceMonitor
    
    config_file = Path(config_path)
    
    if not config_file.exists():
        logger.warning(f"Config não encontrada: {config_path}")
        return MonitorManager()
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    notifier = config.get('notifier', '')
    manager = MonitorManager()
    manager.clear()  # Limpa monitors anteriores
    
    # Keyword Monitor
    kw_config = config.get('keywords', {})
    if kw_config.get('enabled', False):
        kw_monitor = KeywordMonitor(
            notifier_jid=notifier,
            keywords=kw_config.get('words', []),
            case_sensitive=kw_config.get('case_sensitive', False),
            whole_word=kw_config.get('whole_word', True)
        )
        manager.add(kw_monitor)
        logger.info(f"KeywordMonitor carregado: {len(kw_config.get('words', []))} palavras")
    
    # Contact Monitor
    ct_config = config.get('contacts', {})
    if ct_config.get('enabled', False):
        ct_monitor = ContactMonitor(
            notifier_jid=notifier,
            contacts=set(ct_config.get('jids', [])),
            notify_on_message=ct_config.get('notify_on_message', True),
            notify_on_online=ct_config.get('notify_on_online', True)
        )
        manager.add(ct_monitor)
        logger.info(f"ContactMonitor carregado: {len(ct_config.get('jids', []))} contatos")
    
    # Media Monitor
    md_config = config.get('media', {})
    if md_config.get('enabled', False):
        contacts = md_config.get('contacts')
        md_monitor = MediaMonitor(
            notifier_jid=notifier,
            contacts=set(contacts) if contacts else None,
            save_path=md_config.get('save_path', 'data/media'),
            notify_on_media=md_config.get('notify_on_media', True),
            save_media=md_config.get('save_media', True)
        )
        manager.add(md_monitor)
        logger.info("MediaMonitor carregado")
    
    # Presence Monitor
    pr_config = config.get('presence', {})
    if pr_config.get('enabled', False):
        contacts = pr_config.get('contacts')
        pr_monitor = PresenceMonitor(
            notifier_jid=notifier,
            contacts=set(contacts) if contacts else None,
            notify_on_online=pr_config.get('notify_on_online', False),
            notify_on_offline=pr_config.get('notify_on_offline', False),
            cooldown_seconds=pr_config.get('cooldown_seconds', 300)
        )
        manager.add(pr_monitor)
        logger.info("PresenceMonitor carregado")
    
    logger.info(f"MonitorManager inicializado com {len(manager)} monitors")
    return manager
