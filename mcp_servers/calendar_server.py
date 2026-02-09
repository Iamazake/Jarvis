# -*- coding: utf-8 -*-
"""
Calendar MCP Server - Servidor MCP para Calendário
Expõe ferramentas de calendário via MCP

Autor: JARVIS Team
Versão: 3.1.0
"""

from typing import Dict, Any
from datetime import datetime

from .base import MCPServer, Tool
from core.logger import get_logger

logger = get_logger(__name__)


class CalendarServer(MCPServer):
    """
    Servidor MCP para funcionalidades de calendário
    """
    
    def __init__(self):
        super().__init__("calendar", "1.0.0")
        self.calendar_module = None
    
    async def setup_tools(self):
        """Configura ferramentas do servidor"""
        
        # Criar evento
        self.register_tool(
            Tool(
                name="create_event",
                description="Cria um novo evento no calendário",
                parameters={
                    "title": {"type": "string", "description": "Título do evento"},
                    "start_time": {"type": "string", "description": "Data/hora de início (ISO format)"},
                    "end_time": {"type": "string", "description": "Data/hora de fim (ISO format, opcional)"},
                    "description": {"type": "string", "description": "Descrição do evento (opcional)"},
                    "location": {"type": "string", "description": "Local do evento (opcional)"}
                },
                required=["title", "start_time"]
            ),
            self._handle_create_event
        )
        
        # Listar eventos
        self.register_tool(
            Tool(
                name="list_events",
                description="Lista eventos do calendário",
                parameters={
                    "start_date": {"type": "string", "description": "Data inicial (ISO format, opcional)"},
                    "end_date": {"type": "string", "description": "Data final (ISO format, opcional)"}
                },
                required=[]
            ),
            self._handle_list_events
        )
        
        # Criar lembrete
        self.register_tool(
            Tool(
                name="create_reminder",
                description="Cria um lembrete",
                parameters={
                    "message": {"type": "string", "description": "Mensagem do lembrete"},
                    "time": {"type": "string", "description": "Data/hora do lembrete (ISO format)"},
                    "recurring": {"type": "string", "description": "Recorrência: daily, weekly, monthly (opcional)"}
                },
                required=["message", "time"]
            ),
            self._handle_create_reminder
        )
        
        # Próximos eventos
        self.register_tool(
            Tool(
                name="get_upcoming_events",
                description="Obtém eventos próximos",
                parameters={
                    "hours": {"type": "integer", "description": "Horas à frente (padrão: 24)"}
                },
                required=[]
            ),
            self._handle_upcoming_events
        )
    
    def set_calendar_module(self, module):
        """Define módulo de calendário"""
        self.calendar_module = module
    
    async def _handle_create_event(self, **kwargs) -> str:
        """Handler para criar evento"""
        if not self.calendar_module:
            return "Módulo de calendário não disponível"
        
        try:
            title = kwargs['title']
            start_time = datetime.fromisoformat(kwargs['start_time'])
            end_time = None
            if 'end_time' in kwargs and kwargs['end_time']:
                end_time = datetime.fromisoformat(kwargs['end_time'])
            
            event = await self.calendar_module.create_event(
                title=title,
                start_time=start_time,
                end_time=end_time,
                description=kwargs.get('description'),
                location=kwargs.get('location')
            )
            
            return f"✅ Evento criado: {event.title} em {start_time.strftime('%d/%m/%Y %H:%M')}"
            
        except Exception as e:
            logger.error(f"Erro criando evento: {e}", exc_info=True)
            return f"❌ Erro ao criar evento: {str(e)}"
    
    async def _handle_list_events(self, **kwargs) -> str:
        """Handler para listar eventos"""
        if not self.calendar_module:
            return "Módulo de calendário não disponível"
        
        try:
            start_date = None
            end_date = None
            
            if 'start_date' in kwargs and kwargs['start_date']:
                start_date = datetime.fromisoformat(kwargs['start_date'])
            if 'end_date' in kwargs and kwargs['end_date']:
                end_date = datetime.fromisoformat(kwargs['end_date'])
            
            events = await self.calendar_module.event_manager.list_events(
                start_date=start_date,
                end_date=end_date
            )
            
            if not events:
                return "Não há eventos no período especificado."
            
            response = f"📅 **Eventos** ({len(events)})\n\n"
            for event in events[:10]:
                response += f"• {event.title} - {event.start_time.strftime('%d/%m/%Y %H:%M')}\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Erro listando eventos: {e}", exc_info=True)
            return f"❌ Erro ao listar eventos: {str(e)}"
    
    async def _handle_create_reminder(self, **kwargs) -> str:
        """Handler para criar lembrete"""
        if not self.calendar_module:
            return "Módulo de calendário não disponível"
        
        try:
            message = kwargs['message']
            time = datetime.fromisoformat(kwargs['time'])
            recurring = kwargs.get('recurring')
            
            reminder = await self.calendar_module.create_reminder(
                message=message,
                time=time,
                recurring=recurring
            )
            
            return f"✅ Lembrete criado: {message} para {time.strftime('%d/%m/%Y %H:%M')}"
            
        except Exception as e:
            logger.error(f"Erro criando lembrete: {e}", exc_info=True)
            return f"❌ Erro ao criar lembrete: {str(e)}"
    
    async def _handle_upcoming_events(self, **kwargs) -> str:
        """Handler para próximos eventos"""
        if not self.calendar_module:
            return "Módulo de calendário não disponível"
        
        try:
            hours = kwargs.get('hours', 24)
            events = await self.calendar_module.get_upcoming_reminders(hours)
            
            if not events:
                return f"Não há eventos nas próximas {hours} horas."
            
            response = f"📅 **Próximos Eventos** ({len(events)})\n\n"
            for event in events[:10]:
                response += f"• {event.title} - {event.start_time.strftime('%d/%m/%Y %H:%M')}\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Erro obtendo próximos eventos: {e}", exc_info=True)
            return f"❌ Erro: {str(e)}"
