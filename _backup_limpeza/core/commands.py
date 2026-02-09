# -*- coding: utf-8 -*-
"""
Commands - Command Pattern para Ações
Encapsula ações como comandos para undo/redo

Autor: JARVIS Team
Versão: 3.1.0
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .logger import get_logger

logger = get_logger(__name__)


class CommandStatus(Enum):
    """Status de um comando"""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CommandResult:
    """Resultado da execução de um comando"""
    success: bool
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class Command(ABC):
    """
    Interface base para comandos
    
    Todos os comandos devem implementar execute() e opcionalmente undo()
    """
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.status = CommandStatus.PENDING
        self.created_at = datetime.now()
        self.executed_at: Optional[datetime] = None
        self.result: Optional[CommandResult] = None
    
    @abstractmethod
    async def execute(self) -> CommandResult:
        """
        Executa o comando
        
        Returns:
            Resultado da execução
        """
        pass
    
    async def undo(self) -> CommandResult:
        """
        Desfaz o comando (opcional)
        
        Returns:
            Resultado do undo
        """
        return CommandResult(
            success=False,
            message="Undo não implementado para este comando"
        )
    
    def can_undo(self) -> bool:
        """Verifica se comando pode ser desfeito"""
        return False
    
    def get_info(self) -> Dict[str, Any]:
        """Retorna informações do comando"""
        return {
            'name': self.name,
            'description': self.description,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'can_undo': self.can_undo()
        }


class CommandInvoker:
    """
    Invocador de comandos
    
    Gerencia execução, histórico e undo/redo
    """
    
    def __init__(self, max_history: int = 100):
        self.history: List[Command] = []
        self.undo_stack: List[Command] = []
        self.max_history = max_history
    
    async def execute(self, command: Command) -> CommandResult:
        """
        Executa um comando
        
        Args:
            command: Comando a executar
        
        Returns:
            Resultado da execução
        """
        command.status = CommandStatus.EXECUTING
        
        try:
            result = await command.execute()
            command.status = CommandStatus.COMPLETED if result.success else CommandStatus.FAILED
            command.executed_at = datetime.now()
            command.result = result
            
            # Adiciona ao histórico
            self.history.append(command)
            if len(self.history) > self.max_history:
                self.history.pop(0)
            
            # Limpa undo stack quando novo comando é executado
            self.undo_stack.clear()
            
            logger.info(
                f"Comando executado: {command.name}",
                context={'success': result.success}
            )
            
            return result
            
        except Exception as e:
            command.status = CommandStatus.FAILED
            command.result = CommandResult(
                success=False,
                error=str(e)
            )
            logger.error(
                f"Erro executando comando {command.name}: {e}",
                exc_info=True
            )
            return command.result
    
    async def undo(self) -> Optional[CommandResult]:
        """
        Desfaz último comando
        
        Returns:
            Resultado do undo ou None se não houver comando
        """
        if not self.history:
            return None
        
        command = self.history.pop()
        
        if not command.can_undo():
            logger.warning(f"Comando {command.name} não pode ser desfeito")
            return None
        
        try:
            result = await command.undo()
            self.undo_stack.append(command)
            
            logger.info(f"Comando desfeito: {command.name}")
            return result
            
        except Exception as e:
            logger.error(f"Erro desfazendo comando {command.name}: {e}")
            return CommandResult(success=False, error=str(e))
    
    async def redo(self) -> Optional[CommandResult]:
        """
        Refaz último comando desfeito
        
        Returns:
            Resultado do redo ou None se não houver comando
        """
        if not self.undo_stack:
            return None
        
        command = self.undo_stack.pop()
        return await self.execute(command)
    
    def get_history(self, limit: int = 10) -> List[Command]:
        """Retorna histórico de comandos"""
        return self.history[-limit:]
    
    def clear_history(self):
        """Limpa histórico"""
        self.history.clear()
        self.undo_stack.clear()


# Comandos específicos do JARVIS

class SendMessageCommand(Command):
    """Comando para enviar mensagem"""
    
    def __init__(self, recipient: str, message: str, source: str = 'cli'):
        super().__init__(
            name='send_message',
            description=f"Enviar mensagem para {recipient}"
        )
        self.recipient = recipient
        self.message = message
        self.source = source
        self._sent = False
    
    async def execute(self) -> CommandResult:
        """Executa envio de mensagem"""
        # Aqui integraria com módulo de WhatsApp ou outro
        # Por enquanto, simula
        self._sent = True
        
        return CommandResult(
            success=True,
            message=f"Mensagem enviada para {self.recipient}",
            data={'recipient': self.recipient, 'message': self.message}
        )
    
    async def undo(self) -> CommandResult:
        """Desfaz envio (não é possível realmente desfazer)"""
        return CommandResult(
            success=False,
            message="Não é possível desfazer envio de mensagem"
        )
    
    def can_undo(self) -> bool:
        return False


class RememberCommand(Command):
    """Comando para lembrar informação"""
    
    def __init__(self, key: str, value: Any, category: str = 'facts'):
        super().__init__(
            name='remember',
            description=f"Lembrar {key}"
        )
        self.key = key
        self.value = value
        self.category = category
        self._old_value = None
    
    async def execute(self) -> CommandResult:
        """Executa lembrança"""
        # Aqui integraria com módulo de memória
        # Por enquanto, simula
        
        return CommandResult(
            success=True,
            message=f"Informação '{self.key}' lembrada",
            data={'key': self.key, 'value': self.value}
        )
    
    async def undo(self) -> CommandResult:
        """Desfaz lembrança"""
        # Aqui deletaria a memória
        return CommandResult(
            success=True,
            message=f"Informação '{self.key}' esquecida"
        )
    
    def can_undo(self) -> bool:
        return True


class SearchCommand(Command):
    """Comando para pesquisar"""
    
    def __init__(self, query: str):
        super().__init__(
            name='search',
            description=f"Pesquisar: {query}"
        )
        self.query = query
        self.results = None
    
    async def execute(self) -> CommandResult:
        """Executa pesquisa"""
        # Aqui integraria com módulo de pesquisa
        self.results = []  # Simulado
        
        return CommandResult(
            success=True,
            message=f"Pesquisa realizada: {self.query}",
            data={'query': self.query, 'results': self.results}
        )
    
    def can_undo(self) -> bool:
        return False


class CommandFactory:
    """
    Factory para criar comandos
    """
    
    @staticmethod
    def create_send_message(recipient: str, message: str, source: str = 'cli') -> SendMessageCommand:
        """Cria comando de envio de mensagem"""
        return SendMessageCommand(recipient, message, source)
    
    @staticmethod
    def create_remember(key: str, value: Any, category: str = 'facts') -> RememberCommand:
        """Cria comando de lembrança"""
        return RememberCommand(key, value, category)
    
    @staticmethod
    def create_search(query: str) -> SearchCommand:
        """Cria comando de pesquisa"""
        return SearchCommand(query)


# Instância global
_invoker: Optional[CommandInvoker] = None


def get_command_invoker() -> CommandInvoker:
    """Retorna invocador global de comandos"""
    global _invoker
    if _invoker is None:
        _invoker = CommandInvoker()
    return _invoker
