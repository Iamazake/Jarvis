# -*- coding: utf-8 -*-
"""
Reminder Scheduler - Agendador de Lembretes
Gerencia lembretes e notificações

Autor: JARVIS Team
Versão: 3.1.0
"""

import asyncio
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from core.logger import get_logger
from core.event_bus import get_event_bus, EventType, Event

logger = get_logger(__name__)


@dataclass
class Reminder:
    """Representa um lembrete"""
    id: str
    message: str
    time: datetime
    recurring: Optional[str] = None  # 'daily', 'weekly', 'monthly'
    created_at: datetime = field(default_factory=datetime.now)
    last_triggered: Optional[datetime] = None
    enabled: bool = True
    
    def should_trigger(self, now: datetime) -> bool:
        """Verifica se deve ser acionado"""
        if not self.enabled:
            return False
        
        if now >= self.time:
            # Se não é recorrente, só aciona uma vez
            if not self.recurring:
                return self.last_triggered is None
            
            # Se é recorrente, verifica intervalo
            if self.last_triggered:
                if self.recurring == 'daily':
                    return (now - self.last_triggered).days >= 1
                elif self.recurring == 'weekly':
                    return (now - self.last_triggered).days >= 7
                elif self.recurring == 'monthly':
                    return (now - self.last_triggered).days >= 30
            
            return True
        
        return False
    
    def get_next_occurrence(self) -> datetime:
        """Calcula próxima ocorrência"""
        if not self.recurring:
            return self.time
        
        now = datetime.now()
        next_time = self.time
        
        while next_time <= now:
            if self.recurring == 'daily':
                next_time += timedelta(days=1)
            elif self.recurring == 'weekly':
                next_time += timedelta(weeks=1)
            elif self.recurring == 'monthly':
                next_time += timedelta(days=30)
        
        return next_time


class ReminderScheduler:
    """
    Agendador de lembretes
    """
    
    def __init__(self):
        self._reminders: Dict[str, Reminder] = {}
        self._next_id = 1
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Inicia o scheduler"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Reminder scheduler iniciado")
    
    async def stop(self):
        """Para o scheduler"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Reminder scheduler parado")
    
    async def _scheduler_loop(self):
        """Loop principal do scheduler"""
        while self._running:
            try:
                await self._check_reminders()
                await asyncio.sleep(60)  # Verifica a cada minuto
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no scheduler loop: {e}", exc_info=True)
                await asyncio.sleep(60)
    
    async def _check_reminders(self):
        """Verifica lembretes que devem ser acionados"""
        now = datetime.now()
        
        for reminder in self._reminders.values():
            if reminder.should_trigger(now):
                await self._trigger_reminder(reminder)
                reminder.last_triggered = now
    
    async def _trigger_reminder(self, reminder: Reminder):
        """Aciona um lembrete"""
        logger.info(f"Lembrete acionado: {reminder.message}")
        
        # Emite evento
        event_bus = get_event_bus()
        await event_bus.publish(Event(
            type=EventType.REMINDER_TRIGGERED,
            data={
                'reminder_id': reminder.id,
                'message': reminder.message
            }
        ))
    
    async def create_reminder(
        self,
        message: str,
        time: datetime,
        recurring: Optional[str] = None
    ) -> Reminder:
        """Cria novo lembrete"""
        reminder_id = f"reminder_{self._next_id}"
        self._next_id += 1
        
        reminder = Reminder(
            id=reminder_id,
            message=message,
            time=time,
            recurring=recurring
        )
        
        self._reminders[reminder_id] = reminder
        
        logger.info(f"Lembrete criado: {message} para {time}")
        return reminder
    
    async def delete_reminder(self, reminder_id: str) -> bool:
        """Deleta lembrete"""
        if reminder_id in self._reminders:
            del self._reminders[reminder_id]
            logger.info(f"Lembrete deletado: {reminder_id}")
            return True
        return False
    
    async def list_reminders(self) -> List[Reminder]:
        """Lista todos os lembretes"""
        return list(self._reminders.values())
    
    async def get_upcoming_reminders(self, hours: int = 24) -> List[Reminder]:
        """Obtém lembretes próximos"""
        now = datetime.now()
        end = now + timedelta(hours=hours)
        
        reminders = [
            r for r in self._reminders.values()
            if r.time <= end and r.enabled
        ]
        
        reminders.sort(key=lambda r: r.time)
        return reminders
