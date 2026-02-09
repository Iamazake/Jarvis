"""
Contact Monitor - Monitora atividade de contatos específicos
"""

from typing import Set, Dict, Optional
from datetime import datetime
from .base import AbstractMonitor


class ContactMonitor(AbstractMonitor):
    """
    Monitora quando contatos específicos enviam mensagens.
    Útil para não perder mensagens de pessoas importantes.
    """
    
    def __init__(self, notifier_jid: str, contacts: Set[str] = None,
                 notify_on_message: bool = True, 
                 notify_on_online: bool = True):
        """
        Args:
            notifier_jid: JID que recebe alertas
            contacts: Set de JIDs a monitorar (formato: 5511999999999@s.whatsapp.net)
            notify_on_message: Notificar quando enviar mensagem
            notify_on_online: Notificar quando ficar online
        """
        super().__init__(notifier_jid, "ContactMonitor")
        self.contacts: Set[str] = contacts or set()
        self.notify_on_message = notify_on_message
        self.notify_on_online = notify_on_online
        
        # Histórico de último contato
        self._last_seen: Dict[str, datetime] = {}
        self._last_message: Dict[str, dict] = {}
    
    def add_contact(self, jid: str, name: str = None):
        """
        Adiciona contato ao monitoramento.
        JID formato: 5511999999999@s.whatsapp.net ou só o número
        """
        # Normaliza JID
        if '@' not in jid:
            jid = f"{jid}@s.whatsapp.net"
        self.contacts.add(jid)
    
    def remove_contact(self, jid: str):
        """Remove contato do monitoramento"""
        if '@' not in jid:
            jid = f"{jid}@s.whatsapp.net"
        self.contacts.discard(jid)
    
    def update(self, event: dict) -> None:
        """
        Processa eventos de mensagem e presença.
        """
        if not self.enabled:
            return
        
        sender = event.get('sender', '')
        event_type = event.get('type')
        
        # Verifica se é contato monitorado
        if sender not in self.contacts:
            return
        
        push_name = event.get('push_name', sender.split('@')[0])
        
        if event_type == 'message' and self.notify_on_message:
            data = event.get('data', {})
            text = data.get('text', '[mídia]')
            preview = text[:80] + ('...' if len(text) > 80 else '')
            
            # Atualiza histórico
            self._last_message[sender] = {
                'text': text,
                'timestamp': datetime.now()
            }
            
            alert = (
                f"📨 Mensagem de contato monitorado!\n"
                f"👤 {push_name}\n"
                f"💬 {preview}"
            )
            self.notify(alert)
            
        elif event_type == 'presence' and self.notify_on_online:
            data = event.get('data', {})
            status = data.get('status', 'unknown')
            
            if status == 'available':
                # Verifica se estava offline antes (evita spam)
                last = self._last_seen.get(sender)
                now = datetime.now()
                
                if last is None or (now - last).seconds > 300:  # 5 min cooldown
                    self._last_seen[sender] = now
                    alert = f"🟢 {push_name} está online agora!"
                    self.notify(alert)
    
    def get_last_seen(self, jid: str) -> Optional[datetime]:
        """Retorna último momento que o contato foi visto online"""
        if '@' not in jid:
            jid = f"{jid}@s.whatsapp.net"
        return self._last_seen.get(jid)
    
    def get_last_message(self, jid: str) -> Optional[dict]:
        """Retorna última mensagem do contato"""
        if '@' not in jid:
            jid = f"{jid}@s.whatsapp.net"
        return self._last_message.get(jid)
    
    def list_contacts(self) -> list:
        """Lista contatos monitorados"""
        return list(self.contacts)
    
    def __repr__(self):
        return f"<ContactMonitor contacts={len(self.contacts)} enabled={self.enabled}>"
