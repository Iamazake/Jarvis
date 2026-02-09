# -*- coding: utf-8 -*-
"""
Calendar Module - Módulo Principal de Calendário
Sistema completo de gerenciamento de eventos e lembretes

Autor: JARVIS Team
Versão: 3.1.0
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from core.logger import get_logger
from core.module_factory import BaseModule
from core.schemas import EventSchema, ReminderSchema
from .event_manager import EventManager, Event
from .reminder_scheduler import ReminderScheduler, Reminder

logger = get_logger(__name__)


class CalendarModule(BaseModule):
    """
    Módulo de Calendário completo
    
    Funcionalidades:
    - Gerenciamento de eventos
    - Lembretes e notificações
    - Eventos recorrentes
    - Integração com Google Calendar (futuro)
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.event_manager = EventManager()
        self.reminder_scheduler = ReminderScheduler()
    
    async def start(self):
        """Inicializa o módulo"""
        logger.info("📅 Iniciando módulo de calendário...")
        
        # Inicia scheduler de lembretes
        await self.reminder_scheduler.start()
        
        self._running = True
        self.status = '🟢'
        logger.info("✅ Módulo de calendário pronto")
    
    async def stop(self):
        """Para o módulo"""
        await self.reminder_scheduler.stop()
        self._running = False
        self.status = '🔴'
        logger.info("Módulo de calendário parado")
    
    async def process(
        self,
        message: str,
        intent,
        context: Dict,
        metadata: Dict
    ) -> str:
        """Processa comandos de calendário"""
        intent_type = intent.type if hasattr(intent, 'type') else str(intent)
        entities = intent.entities if hasattr(intent, 'entities') else {}
        
        message_lower = message.lower()
        
        # Criar evento
        if 'criar' in message_lower or 'adicionar' in message_lower or 'agendar' in message_lower:
            return await self._handle_create_event(message, entities)
        
        # Listar eventos
        elif 'listar' in message_lower or 'mostrar' in message_lower or 'eventos' in message_lower:
            return await self._handle_list_events(message, entities)
        
        # Criar lembrete
        elif 'lembrete' in message_lower or 'lembrar' in message_lower:
            return await self._handle_create_reminder(message, entities)
        
        # Próximos eventos
        elif 'próximos' in message_lower or 'hoje' in message_lower:
            return await self._handle_upcoming_events(message)
        
        else:
            return "Não entendi o comando de calendário. Tente 'criar evento', 'listar eventos' ou 'criar lembrete'."
    
    async def _handle_create_event(
        self,
        message: str,
        entities: Dict[str, Any]
    ) -> str:
        """Cria evento"""
        # Por enquanto, retorna mensagem simples
        # Em implementação completa, extrairia título, data, hora das entidades
        return "Para criar um evento, use: 'Criar evento [título] em [data] às [hora]'"
    
    async def _handle_list_events(
        self,
        message: str,
        entities: Dict[str, Any]
    ) -> str:
        """Lista eventos"""
        events = await self.event_manager.list_events()
        
        if not events:
            return "Não há eventos agendados."
        
        response = f"📅 **Eventos Agendados** ({len(events)})\n\n"
        
        for event in events[:10]:  # Limita a 10
            response += f"• **{event.title}**\n"
            response += f"  📅 {event.start_time.strftime('%d/%m/%Y %H:%M')}\n"
            if event.location:
                response += f"  📍 {event.location}\n"
            response += "\n"
        
        return response
    
    async def _handle_create_reminder(
        self,
        message: str,
        entities: Dict[str, Any]
    ) -> str:
        """Cria lembrete"""
        # Por enquanto, retorna mensagem simples
        return "Para criar um lembrete, use: 'Lembrar-me de [mensagem] em [data/hora]'"
    
    async def _handle_upcoming_events(self, message: str) -> str:
        """Lista próximos eventos"""
        events = await self.event_manager.get_upcoming_events(hours=24)
        
        if not events:
            return "Não há eventos nas próximas 24 horas."
        
        response = f"📅 **Próximos Eventos** ({len(events)})\n\n"
        
        for event in events:
            response += f"• **{event.title}**\n"
            response += f"  ⏰ {event.start_time.strftime('%d/%m/%Y %H:%M')}\n"
            if event.location:
                response += f"  📍 {event.location}\n"
            response += "\n"
        
        return response
    
    # Métodos públicos para uso direto
    
    async def create_event(
        self,
        title: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        reminder_minutes: Optional[int] = None
    ) -> Event:
        """Cria evento programaticamente"""
        return await self.event_manager.create_event(
            title=title,
            start_time=start_time,
            end_time=end_time,
            description=description,
            location=location,
            reminder_minutes=reminder_minutes
        )
    
    async def create_reminder(
        self,
        message: str,
        time: datetime,
        recurring: Optional[str] = None
    ) -> Reminder:
        """Cria lembrete programaticamente"""
        return await self.reminder_scheduler.create_reminder(
            message=message,
            time=time,
            recurring=recurring
        )
    
    async def get_events_today(self) -> List[Event]:
        """Obtém eventos de hoje"""
        today = datetime.now().replace(hour=0, minute=0, second=0)
        return await self.event_manager.get_events_for_date(today)
    
    async def get_upcoming_reminders(self, hours: int = 24) -> List[Reminder]:
        """Obtém lembretes próximos"""
        return await self.reminder_scheduler.get_upcoming_reminders(hours)
