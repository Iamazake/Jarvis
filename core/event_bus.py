# -*- coding: utf-8 -*-
"""
Event Bus - Sistema de Eventos Aprimorado
Observer Pattern com tipos de eventos e filtros

Autor: JARVIS Team
Versão: 3.1.0
"""

import asyncio
from typing import Dict, List, Callable, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .logger import get_logger

logger = get_logger(__name__)


class EventType(Enum):
    """Tipos de eventos do sistema"""
    # Mensagens
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_SENT = "message_sent"
    RESPONSE_GENERATED = "response_generated"
    
    # Módulos
    MODULE_STARTED = "module_started"
    MODULE_STOPPED = "module_stopped"
    MODULE_ERROR = "module_error"
    
    # IA
    AI_REQUEST = "ai_request"
    AI_RESPONSE = "ai_response"
    AI_ERROR = "ai_error"
    
    # Ferramentas
    TOOL_CALLED = "tool_called"
    TOOL_RESULT = "tool_result"
    TOOL_ERROR = "tool_error"
    
    # Memória
    MEMORY_SAVED = "memory_saved"
    MEMORY_RECALLED = "memory_recalled"
    
    # Sistema
    SYSTEM_STARTED = "system_started"
    SYSTEM_STOPPED = "system_stopped"
    SYSTEM_ERROR = "system_error"
    
    # Proativo
    PROACTIVE_SUGGESTION = "proactive_suggestion"
    REMINDER_TRIGGERED = "reminder_triggered"


@dataclass
class Event:
    """Representa um evento"""
    type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte evento para dicionário"""
        return {
            'type': self.type.value,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source
        }


class EventBus:
    """
    Sistema de eventos centralizado
    
    Funcionalidades:
    - Publicação de eventos
    - Assinatura com filtros
    - Handlers assíncronos e síncronos
    - Prioridades de handlers
    - Middleware
    """
    
    def __init__(self):
        self._subscribers: Dict[EventType, List[Dict[str, Any]]] = {}
        self._middleware: List[Callable] = []
        self._event_history: List[Event] = []
        self._max_history: int = 1000
        self._running = True
    
    def subscribe(
        self,
        event_type: EventType,
        handler: Callable,
        priority: int = 0,
        filter_func: Optional[Callable] = None
    ):
        """
        Assina um tipo de evento
        
        Args:
            event_type: Tipo de evento
            handler: Função handler (async ou sync)
            priority: Prioridade (maior = executa primeiro)
            filter_func: Função de filtro (opcional)
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append({
            'handler': handler,
            'priority': priority,
            'filter': filter_func
        })
        
        # Ordena por prioridade (maior primeiro)
        self._subscribers[event_type].sort(key=lambda x: x['priority'], reverse=True)
        
        logger.debug(
            f"Handler registrado para {event_type.value}",
            context={'priority': priority}
        )
    
    def unsubscribe(self, event_type: EventType, handler: Callable):
        """Remove assinatura"""
        if event_type not in self._subscribers:
            return
        
        self._subscribers[event_type] = [
            sub for sub in self._subscribers[event_type]
            if sub['handler'] != handler
        ]
        
        logger.debug(f"Handler removido de {event_type.value}")
    
    def add_middleware(self, middleware: Callable):
        """
        Adiciona middleware
        
        Middleware recebe (event, next_handler) e pode modificar evento
        """
        self._middleware.append(middleware)
        logger.debug("Middleware adicionado")
    
    async def publish(self, event: Event) -> int:
        """
        Publica um evento
        
        Args:
            event: Evento a publicar
        
        Returns:
            Número de handlers executados
        """
        if not self._running:
            return 0
        
        # Adiciona ao histórico
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # Busca subscribers
        handlers = self._subscribers.get(event.type, [])
        
        if not handlers:
            logger.debug(f"Nenhum handler para {event.type.value}")
            return 0
        
        # Aplica middleware
        processed_event = event
        for middleware in self._middleware:
            processed_event = await self._apply_middleware(middleware, processed_event)
            if processed_event is None:
                # Middleware bloqueou evento
                return 0
        
        # Executa handlers
        executed = 0
        for subscriber in handlers:
            # Aplica filtro se existir
            if subscriber['filter']:
                try:
                    if asyncio.iscoroutinefunction(subscriber['filter']):
                        if not await subscriber['filter'](processed_event):
                            continue
                    else:
                        if not subscriber['filter'](processed_event):
                            continue
                except Exception as e:
                    logger.error(
                        f"Erro em filtro para {event.type.value}: {e}",
                        exc_info=True
                    )
                    continue
            
            # Executa handler
            try:
                handler = subscriber['handler']
                if asyncio.iscoroutinefunction(handler):
                    await handler(processed_event)
                else:
                    handler(processed_event)
                executed += 1
            except Exception as e:
                logger.error(
                    f"Erro em handler para {event.type.value}: {e}",
                    exc_info=True
                )
        
        logger.debug(
            f"Evento {event.type.value} publicado",
            context={'handlers_executed': executed}
        )
        
        return executed
    
    async def _apply_middleware(self, middleware: Callable, event: Event) -> Optional[Event]:
        """Aplica middleware"""
        try:
            if asyncio.iscoroutinefunction(middleware):
                return await middleware(event, self._next_handler)
            else:
                return middleware(event, self._next_handler)
        except Exception as e:
            logger.error(f"Erro em middleware: {e}", exc_info=True)
            return event
    
    def _next_handler(self, event: Event):
        """Placeholder para next handler em middleware"""
        pass
    
    def get_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100
    ) -> List[Event]:
        """
        Retorna histórico de eventos
        
        Args:
            event_type: Filtrar por tipo (opcional)
            limit: Limite de eventos
        
        Returns:
            Lista de eventos
        """
        events = self._event_history
        
        if event_type:
            events = [e for e in events if e.type == event_type]
        
        return events[-limit:]
    
    def get_subscriber_count(self, event_type: EventType) -> int:
        """Retorna número de subscribers para um tipo"""
        return len(self._subscribers.get(event_type, []))
    
    def stop(self):
        """Para o event bus"""
        self._running = False
        logger.info("Event bus parado")
    
    def start(self):
        """Inicia o event bus"""
        self._running = True
        logger.info("Event bus iniciado")


# Instância global
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Retorna instância global do event bus"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
        _event_bus.start()
    return _event_bus


# Funções de conveniência
async def emit(event_type: EventType, data: Dict[str, Any] = None, source: str = None):
    """Emite um evento"""
    event = Event(
        type=event_type,
        data=data or {},
        source=source
    )
    bus = get_event_bus()
    await bus.publish(event)


def on(event_type: EventType, priority: int = 0):
    """
    Decorator para assinar eventos
    
    Usage:
        @on(EventType.MESSAGE_RECEIVED)
        async def handle_message(event: Event):
            ...
    """
    def decorator(handler: Callable):
        bus = get_event_bus()
        bus.subscribe(event_type, handler, priority)
        return handler
    return decorator
