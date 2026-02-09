# -*- coding: utf-8 -*-
"""
Event Manager - Gerenciador de Eventos
Gerencia eventos do calendário

Autor: JARVIS Team
Versão: 3.1.0
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from core.logger import get_logger
from core.schemas import EventSchema

logger = get_logger(__name__)


@dataclass
class Event:
    """Representa um evento"""
    id: str
    title: str
    description: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    reminder_minutes: Optional[int] = None
    recurring: Optional[str] = None  # 'daily', 'weekly', 'monthly'
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'location': self.location,
            'reminder_minutes': self.reminder_minutes,
            'recurring': self.recurring
        }


class EventManager:
    """
    Gerenciador de eventos do calendário
    """
    
    def __init__(self):
        self._events: Dict[str, Event] = {}
        self._next_id = 1
    
    async def create_event(
        self,
        title: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        reminder_minutes: Optional[int] = None,
        recurring: Optional[str] = None
    ) -> Event:
        """Cria novo evento"""
        event_id = f"event_{self._next_id}"
        self._next_id += 1
        
        event = Event(
            id=event_id,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            location=location,
            reminder_minutes=reminder_minutes,
            recurring=recurring
        )
        
        self._events[event_id] = event
        
        logger.info(f"Evento criado: {title} em {start_time}")
        return event
    
    async def get_event(self, event_id: str) -> Optional[Event]:
        """Obtém evento por ID"""
        return self._events.get(event_id)
    
    async def update_event(self, event_id: str, **kwargs) -> Optional[Event]:
        """Atualiza evento"""
        event = self._events.get(event_id)
        if not event:
            return None
        
        for key, value in kwargs.items():
            if hasattr(event, key):
                setattr(event, key, value)
        
        logger.info(f"Evento atualizado: {event_id}")
        return event
    
    async def delete_event(self, event_id: str) -> bool:
        """Deleta evento"""
        if event_id in self._events:
            del self._events[event_id]
            logger.info(f"Evento deletado: {event_id}")
            return True
        return False
    
    async def list_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Event]:
        """Lista eventos no período"""
        events = list(self._events.values())
        
        if start_date:
            events = [e for e in events if e.start_time >= start_date]
        
        if end_date:
            events = [e for e in events if e.start_time <= end_date]
        
        # Ordena por data
        events.sort(key=lambda e: e.start_time)
        
        return events
    
    async def get_upcoming_events(self, hours: int = 24) -> List[Event]:
        """Obtém eventos próximos"""
        now = datetime.now()
        end = now + timedelta(hours=hours)
        
        events = await self.list_events(start_date=now, end_date=end)
        return events
    
    async def get_events_for_date(self, date: datetime) -> List[Event]:
        """Obtém eventos de uma data específica"""
        start = date.replace(hour=0, minute=0, second=0)
        end = date.replace(hour=23, minute=59, second=59)
        
        return await self.list_events(start_date=start, end_date=end)
