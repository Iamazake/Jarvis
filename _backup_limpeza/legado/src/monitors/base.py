"""
Base Monitor - Abstract Observer
Todos os monitores herdam desta classe
"""

from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime
import threading
import queue
import requests
import logging

logger = logging.getLogger('jarvis.monitors')


class AbstractMonitor(ABC):
    """
    Base class para todos os monitores.
    Implementa Observer Pattern - recebe eventos e reage.
    """
    
    def __init__(self, notifier_jid: str, name: str = "monitor"):
        """
        Args:
            notifier_jid: WhatsApp JID que recebe as notificações
            name: Nome identificador do monitor
        """
        self.notifier = notifier_jid
        self.name = name
        self.enabled = True
        self._notification_queue = queue.Queue()
        self._start_notification_worker()
    
    def _start_notification_worker(self):
        """Worker thread para enviar notificações sem bloquear"""
        def worker():
            while True:
                try:
                    text = self._notification_queue.get(timeout=1)
                    if text is None:  # Poison pill
                        break
                    self._send_notification(text)
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"[{self.name}] Erro no worker: {e}")
        
        self._worker = threading.Thread(target=worker, daemon=True)
        self._worker.start()
    
    def _send_notification(self, text: str) -> bool:
        """Envia notificação via WhatsApp API"""
        try:
            response = requests.post(
                "http://localhost:3001/send",
                json={"to": self.notifier, "message": f"🔔 [{self.name}] {text}"},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"[{self.name}] Falha ao notificar: {e}")
            return False
    
    def notify(self, text: str):
        """Adiciona notificação à fila (não bloqueante)"""
        if self.enabled:
            self._notification_queue.put(text)
    
    @abstractmethod
    def update(self, event: dict) -> None:
        """
        Chamado pelo Observer quando há um evento.
        
        Args:
            event: {
                'type': 'message' | 'presence' | 'media',
                'sender': str (WhatsApp JID),
                'push_name': str (nome do contato),
                'timestamp': int,
                'data': dict (dados específicos do evento)
            }
        """
        pass
    
    def enable(self):
        """Ativa o monitor"""
        self.enabled = True
        logger.info(f"[{self.name}] Ativado")
    
    def disable(self):
        """Desativa o monitor"""
        self.enabled = False
        logger.info(f"[{self.name}] Desativado")
    
    def toggle(self) -> bool:
        """Alterna estado do monitor"""
        self.enabled = not self.enabled
        return self.enabled
    
    def __repr__(self):
        status = "✅" if self.enabled else "❌"
        return f"<{self.__class__.__name__} {status} notify={self.notifier}>"
