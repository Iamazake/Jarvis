# -*- coding: utf-8 -*-
"""
Circuit Breaker - Padrão Circuit Breaker
Proteção contra falhas em APIs externas

Autor: JARVIS Team
Versão: 3.1.0
"""

import time
import asyncio
from typing import Callable, Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .exceptions import CircuitBreakerOpenException
from .logger import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """Estados do circuit breaker"""
    CLOSED = "closed"      # Normal, permitindo requisições
    OPEN = "open"          # Bloqueando requisições após muitas falhas
    HALF_OPEN = "half_open"  # Testando se serviço recuperou


@dataclass
class CircuitBreakerStats:
    """Estatísticas do circuit breaker"""
    failures: int = 0
    successes: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changes: int = 0


class CircuitBreaker:
    """
    Circuit Breaker para proteger contra falhas em APIs externas
    
    Estados:
    - CLOSED: Normal, permitindo requisições
    - OPEN: Bloqueando após muitas falhas
    - HALF_OPEN: Testando recuperação
    
    Usage:
        breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60
        )
        
        @breaker.wrap_async
        async def call_api():
            ...
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
        expected_exception: type = Exception
    ):
        """
        Inicializa circuit breaker
        
        Args:
            name: Nome do circuit breaker
            failure_threshold: Número de falhas para abrir
            recovery_timeout: Tempo em segundos antes de tentar recuperar
            success_threshold: Sucessos necessários para fechar
            expected_exception: Tipo de exceção que conta como falha
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.expected_exception = expected_exception
        
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()
        self._opened_at: Optional[datetime] = None
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Executa função através do circuit breaker
        
        Args:
            func: Função a executar
            *args: Argumentos
            **kwargs: Keyword arguments
        
        Returns:
            Resultado da função
        
        Raises:
            CircuitBreakerOpenException: Se circuit breaker está aberto
        """
        async with self._lock:
            # Verifica se pode executar
            if self.state == CircuitState.OPEN:
                # Verifica se já passou tempo de recuperação
                if self._opened_at:
                    elapsed = (datetime.now() - self._opened_at).total_seconds()
                    if elapsed >= self.recovery_timeout:
                        # Tenta recuperar
                        self.state = CircuitState.HALF_OPEN
                        self.stats.state_changes += 1
                        logger.info(
                            f"Circuit breaker {self.name} entrando em HALF_OPEN",
                            context={'state': 'half_open'}
                        )
                    else:
                        # Ainda bloqueado
                        retry_after = int(self.recovery_timeout - elapsed)
                        raise CircuitBreakerOpenException(
                            self.name,
                            retry_after=retry_after
                        )
            
            # Executa função
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Sucesso
                await self._on_success()
                return result
                
            except self.expected_exception as e:
                # Falha esperada
                await self._on_failure()
                raise
            except Exception as e:
                # Outras exceções não contam como falha do serviço
                logger.warning(
                    f"Exceção inesperada em {self.name}: {type(e).__name__}",
                    context={'exception': str(e)}
                )
                raise
    
    async def _on_success(self):
        """Chamado quando há sucesso"""
        self.stats.successes += 1
        self.stats.last_success_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            # Se já teve sucessos suficientes, fecha
            if self.stats.successes >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.stats.state_changes += 1
                self.stats.failures = 0
                self._opened_at = None
                logger.info(
                    f"Circuit breaker {self.name} fechado (recuperado)",
                    context={'state': 'closed'}
                )
    
    async def _on_failure(self):
        """Chamado quando há falha"""
        self.stats.failures += 1
        self.stats.last_failure_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            # Volta para aberto imediatamente
            self.state = CircuitState.OPEN
            self.stats.state_changes += 1
            self._opened_at = datetime.now()
            logger.warning(
                f"Circuit breaker {self.name} reaberto após falha",
                context={'state': 'open'}
            )
        
        elif self.state == CircuitState.CLOSED:
            # Verifica se atingiu threshold
            if self.stats.failures >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.stats.state_changes += 1
                self._opened_at = datetime.now()
                logger.error(
                    f"Circuit breaker {self.name} aberto após {self.stats.failures} falhas",
                    context={
                        'state': 'open',
                        'failures': self.stats.failures
                    }
                )
    
    def wrap_async(self, func: Callable):
        """
        Decorator para funções assíncronas
        
        Usage:
            @breaker.wrap_async
            async def minha_funcao():
                ...
        """
        async def wrapper(*args, **kwargs):
            return await self.call(func, *args, **kwargs)
        return wrapper
    
    def wrap_sync(self, func: Callable):
        """
        Decorator para funções síncronas
        
        Usage:
            @breaker.wrap_sync
            def minha_funcao():
                ...
        """
        def wrapper(*args, **kwargs):
            # Para funções síncronas, executa diretamente
            # (sem async/await)
            if self.state == CircuitState.OPEN:
                if self._opened_at:
                    elapsed = (datetime.now() - self._opened_at).total_seconds()
                    if elapsed >= self.recovery_timeout:
                        self.state = CircuitState.HALF_OPEN
                    else:
                        retry_after = int(self.recovery_timeout - elapsed)
                        raise CircuitBreakerOpenException(
                            self.name,
                            retry_after=retry_after
                        )
            
            try:
                result = func(*args, **kwargs)
                self._on_success_sync()
                return result
            except self.expected_exception as e:
                self._on_failure_sync()
                raise
        
        return wrapper
    
    def _on_success_sync(self):
        """Versão síncrona de _on_success"""
        self.stats.successes += 1
        self.stats.last_success_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            if self.stats.successes >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.stats.state_changes += 1
                self.stats.failures = 0
                self._opened_at = None
    
    def _on_failure_sync(self):
        """Versão síncrona de _on_failure"""
        self.stats.failures += 1
        self.stats.last_failure_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.stats.state_changes += 1
            self._opened_at = datetime.now()
        elif self.state == CircuitState.CLOSED:
            if self.stats.failures >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.stats.state_changes += 1
                self._opened_at = datetime.now()
    
    def reset(self):
        """Reseta circuit breaker para estado inicial"""
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self._opened_at = None
        logger.info(f"Circuit breaker {self.name} resetado")
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do circuit breaker"""
        return {
            'name': self.name,
            'state': self.state.value,
            'failures': self.stats.failures,
            'successes': self.stats.successes,
            'opened_at': self._opened_at.isoformat() if self._opened_at else None,
            'state_changes': self.stats.state_changes
        }


class CircuitBreakerManager:
    """
    Gerenciador de múltiplos circuit breakers
    """
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
    
    def get_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2
    ) -> CircuitBreaker:
        """
        Obtém ou cria circuit breaker
        
        Args:
            name: Nome do breaker
            failure_threshold: Threshold de falhas
            recovery_timeout: Timeout de recuperação
            success_threshold: Threshold de sucessos
        
        Returns:
            Circuit breaker
        """
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                success_threshold=success_threshold
            )
        return self._breakers[name]
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Retorna status de todos os breakers"""
        return {
            name: breaker.get_status()
            for name, breaker in self._breakers.items()
        }
    
    def reset_all(self):
        """Reseta todos os breakers"""
        for breaker in self._breakers.values():
            breaker.reset()


# Instância global
_breaker_manager: Optional[CircuitBreakerManager] = None


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60
) -> CircuitBreaker:
    """
    Obtém circuit breaker global
    
    Args:
        name: Nome do breaker
        failure_threshold: Threshold de falhas
        recovery_timeout: Timeout de recuperação
    
    Returns:
        Circuit breaker
    """
    global _breaker_manager
    if _breaker_manager is None:
        _breaker_manager = CircuitBreakerManager()
    return _breaker_manager.get_breaker(name, failure_threshold, recovery_timeout)
