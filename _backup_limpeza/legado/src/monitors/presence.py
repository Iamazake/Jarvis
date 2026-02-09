"""
Presence Monitor - Rastreia status online/offline de contatos
"""

from typing import Set, Dict, List, Optional
from datetime import datetime
from collections import defaultdict
from .base import AbstractMonitor, logger


class PresenceMonitor(AbstractMonitor):
    """
    Monitora status de presença (online/offline) de contatos.
    Mantém histórico e estatísticas de quando estão online.
    """
    
    def __init__(self, notifier_jid: str, contacts: Set[str] = None,
                 notify_on_online: bool = False,
                 notify_on_offline: bool = False,
                 cooldown_seconds: int = 300):
        """
        Args:
            notifier_jid: JID que recebe alertas
            contacts: Set de JIDs a monitorar (None = monitora todos)
            notify_on_online: Notificar quando contato ficar online
            notify_on_offline: Notificar quando contato ficar offline
            cooldown_seconds: Intervalo mínimo entre notificações do mesmo contato
        """
        super().__init__(notifier_jid, "PresenceMonitor")
        self.contacts: Optional[Set[str]] = contacts
        self.notify_on_online = notify_on_online
        self.notify_on_offline = notify_on_offline
        self.cooldown = cooldown_seconds
        
        # Tracking de presença
        self._current_status: Dict[str, str] = {}  # jid -> 'available' | 'unavailable'
        self._last_online: Dict[str, datetime] = {}  # jid -> última vez online
        self._last_offline: Dict[str, datetime] = {}  # jid -> última vez offline
        self._last_notification: Dict[str, datetime] = {}  # jid -> última notificação
        
        # Histórico de presença
        self._presence_log: List[dict] = []
    
    def add_contact(self, jid: str):
        """Adiciona contato ao monitoramento de presença"""
        if self.contacts is None:
            self.contacts = set()
        if '@' not in jid:
            jid = f"{jid}@s.whatsapp.net"
        self.contacts.add(jid)
    
    def remove_contact(self, jid: str):
        """Remove contato do monitoramento"""
        if self.contacts:
            if '@' not in jid:
                jid = f"{jid}@s.whatsapp.net"
            self.contacts.discard(jid)
    
    def monitor_all(self):
        """Configura para monitorar presença de todos"""
        self.contacts = None
    
    def _should_monitor(self, jid: str) -> bool:
        """Verifica se deve monitorar este JID"""
        if self.contacts is None:
            return True
        return jid in self.contacts
    
    def _can_notify(self, jid: str) -> bool:
        """Verifica cooldown de notificações"""
        last = self._last_notification.get(jid)
        if last is None:
            return True
        return (datetime.now() - last).seconds >= self.cooldown
    
    def update(self, event: dict) -> None:
        """
        Processa eventos de presença.
        
        event['data']['status']: 'available' | 'unavailable' | 'composing' | 'recording'
        """
        if not self.enabled or event.get('type') != 'presence':
            return
        
        sender = event.get('sender', '')
        if not self._should_monitor(sender):
            return
        
        data = event.get('data', {})
        status = data.get('status', 'unknown')
        push_name = event.get('push_name', sender.split('@')[0])
        now = datetime.now()
        
        # Ignora status de digitação/gravando (muito frequente)
        if status in ('composing', 'recording', 'paused'):
            return
        
        # Verifica se houve mudança de status
        previous = self._current_status.get(sender)
        if status == previous:
            return
        
        # Atualiza status atual
        self._current_status[sender] = status
        
        # Registra no log
        log_entry = {
            'jid': sender,
            'push_name': push_name,
            'status': status,
            'previous': previous,
            'timestamp': now.isoformat()
        }
        self._presence_log.append(log_entry)
        
        # Limita histórico
        if len(self._presence_log) > 5000:
            self._presence_log = self._presence_log[-2500:]
        
        # Atualiza timestamps
        if status == 'available':
            self._last_online[sender] = now
            
            if self.notify_on_online and self._can_notify(sender):
                self._last_notification[sender] = now
                alert = f"🟢 {push_name} está online!"
                self.notify(alert)
                
        elif status == 'unavailable':
            self._last_offline[sender] = now
            
            # Calcula tempo online
            online_time = None
            if sender in self._last_online:
                delta = now - self._last_online[sender]
                online_time = delta.seconds
            
            if self.notify_on_offline and self._can_notify(sender):
                self._last_notification[sender] = now
                alert = f"🔴 {push_name} ficou offline"
                if online_time:
                    mins = online_time // 60
                    secs = online_time % 60
                    alert += f" (ficou {mins}m{secs}s online)"
                self.notify(alert)
    
    def get_status(self, jid: str) -> Optional[str]:
        """Retorna status atual de um contato"""
        if '@' not in jid:
            jid = f"{jid}@s.whatsapp.net"
        return self._current_status.get(jid)
    
    def get_last_seen(self, jid: str) -> Optional[datetime]:
        """Retorna quando o contato foi visto online pela última vez"""
        if '@' not in jid:
            jid = f"{jid}@s.whatsapp.net"
        return self._last_online.get(jid)
    
    def get_online_contacts(self) -> List[str]:
        """Retorna lista de contatos atualmente online"""
        return [jid for jid, status in self._current_status.items() 
                if status == 'available']
    
    def get_presence_log(self, jid: str = None, limit: int = 100) -> List[dict]:
        """
        Retorna log de presença.
        
        Args:
            jid: Filtrar por contato específico (None = todos)
            limit: Número máximo de registros
        """
        if jid:
            if '@' not in jid:
                jid = f"{jid}@s.whatsapp.net"
            filtered = [e for e in self._presence_log if e['jid'] == jid]
            return filtered[-limit:]
        return self._presence_log[-limit:]
    
    def get_statistics(self, jid: str) -> dict:
        """Calcula estatísticas de presença de um contato"""
        if '@' not in jid:
            jid = f"{jid}@s.whatsapp.net"
        
        entries = [e for e in self._presence_log if e['jid'] == jid]
        
        if not entries:
            return {'error': 'Sem dados para este contato'}
        
        online_count = sum(1 for e in entries if e['status'] == 'available')
        offline_count = sum(1 for e in entries if e['status'] == 'unavailable')
        
        return {
            'jid': jid,
            'total_events': len(entries),
            'online_events': online_count,
            'offline_events': offline_count,
            'first_seen': entries[0]['timestamp'],
            'last_seen': entries[-1]['timestamp'],
            'current_status': self._current_status.get(jid, 'unknown')
        }
    
    def __repr__(self):
        contacts_str = "todos" if self.contacts is None else str(len(self.contacts))
        online = len(self.get_online_contacts())
        return f"<PresenceMonitor contacts={contacts_str} online={online} enabled={self.enabled}>"
