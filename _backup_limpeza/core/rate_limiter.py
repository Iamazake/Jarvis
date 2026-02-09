# -*- coding: utf-8 -*-
"""
Rate Limiter - Controle de Taxa de Requisições
Previne bloqueio de APIs por excesso de requisições

Autor: JARVIS Team
Versão: 3.1.0
"""

import time
import asyncio
from typing import Dict, Optional, Tuple
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .exceptions import RateLimitException
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitWindow:
    """Janela de rate limiting"""
    requests: deque = field(default_factory=deque)
    limit: int = 0
    window_seconds: int = 0


class RateLimiter:
    """
    Rate Limiter usando algoritmo Token Bucket
    
    Controla número de requisições por período de tempo
    
    Usage:
        limiter = RateLimiter(limit=10, window=60)  # 10 req/min
        
        @limiter.wrap_async
        async def call_api():
            ...
    """
    
    def __init__(
        self,
        name: str,
        limit: int,
        window: int,
        burst: Optional[int] = None
    ):
        """
        Inicializa rate limiter
        
        Args:
            name: Nome do limiter
            limit: Número máximo de requisições
            window: Janela de tempo em segundos
            burst: Permite burst inicial (opcional)
        """
        self.name = name
        self.limit = limit
        self.window = window
        self.burst = burst or limit
        
        # Histórico de requisições (timestamps)
        self._requests: deque = deque(maxlen=limit * 2)
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """
        Tenta adquirir permissão para fazer requisição
        
        Returns:
            True se permitido, False caso contrário
        
        Raises:
            RateLimitException: Se rate limit excedido
        """
        async with self._lock:
            now = time.time()
            
            # Remove requisições antigas (fora da janela)
            cutoff = now - self.window
            while self._requests and self._requests[0] < cutoff:
                self._requests.popleft()
            
            # Verifica se pode fazer requisição
            if len(self._requests) >= self.limit:
                # Rate limit excedido
                oldest_request = self._requests[0]
                retry_after = int(self.window - (now - oldest_request)) + 1
                
                logger.warning(
                    f"Rate limit excedido para {self.name}",
                    context={
                        'limit': self.limit,
                        'window': self.window,
                        'retry_after': retry_after
                    }
                )
                
                raise RateLimitException(
                    resource=self.name,
                    limit=self.limit,
                    window=self.window,
                    retry_after=retry_after
                )
            
            # Permite requisição
            self._requests.append(now)
            return True
    
    async def call(self, func, *args, **kwargs):
        """
        Executa função com rate limiting
        
        Args:
            func: Função a executar
            *args: Argumentos
            **kwargs: Keyword arguments
        
        Returns:
            Resultado da função
        """
        await self.acquire()
        
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    
    def wrap_async(self, func):
        """
        Decorator para funções assíncronas
        
        Usage:
            @limiter.wrap_async
            async def minha_funcao():
                ...
        """
        async def wrapper(*args, **kwargs):
            return await self.call(func, *args, **kwargs)
        return wrapper
    
    def wrap_sync(self, func):
        """
        Decorator para funções síncronas
        
        Usage:
            @limiter.wrap_sync
            def minha_funcao():
                ...
        """
        def wrapper(*args, **kwargs):
            # Versão síncrona
            now = time.time()
            cutoff = now - self.window
            
            # Remove requisições antigas
            while self._requests and self._requests[0] < cutoff:
                self._requests.popleft()
            
            # Verifica limite
            if len(self._requests) >= self.limit:
                oldest_request = self._requests[0]
                retry_after = int(self.window - (now - oldest_request)) + 1
                raise RateLimitException(
                    resource=self.name,
                    limit=self.limit,
                    window=self.window,
                    retry_after=retry_after
                )
            
            # Permite
            self._requests.append(now)
            return func(*args, **kwargs)
        
        return wrapper
    
    def get_status(self) -> Dict:
        """Retorna status do rate limiter"""
        now = time.time()
        cutoff = now - self.window
        
        # Conta requisições na janela
        recent = sum(1 for req_time in self._requests if req_time > cutoff)
        
        return {
            'name': self.name,
            'limit': self.limit,
            'window': self.window,
            'current': recent,
            'remaining': max(0, self.limit - recent),
            'reset_in': int(self.window - (now - (self._requests[0] if self._requests else now))) if self._requests else 0
        }
    
    def reset(self):
        """Reseta histórico de requisições"""
        self._requests.clear()
        logger.info(f"Rate limiter {self.name} resetado")


class RateLimiterManager:
    """
    Gerenciador de múltiplos rate limiters
    """
    
    def __init__(self):
        self._limiters: Dict[str, RateLimiter] = {}
    
    def get_limiter(
        self,
        name: str,
        limit: int,
        window: int,
        burst: Optional[int] = None
    ) -> RateLimiter:
        """
        Obtém ou cria rate limiter
        
        Args:
            name: Nome do limiter
            limit: Limite de requisições
            window: Janela em segundos
            burst: Burst permitido
        
        Returns:
            Rate limiter
        """
        if name not in self._limiters:
            self._limiters[name] = RateLimiter(
                name=name,
                limit=limit,
                window=window,
                burst=burst
            )
        return self._limiters[name]
    
    def get_all_status(self) -> Dict[str, Dict]:
        """Retorna status de todos os limiters"""
        return {
            name: limiter.get_status()
            for name, limiter in self._limiters.items()
        }
    
    def reset_all(self):
        """Reseta todos os limiters"""
        for limiter in self._limiters.values():
            limiter.reset()


# Instância global
_limiter_manager: Optional[RateLimiterManager] = None


def get_rate_limiter(
    name: str,
    limit: int,
    window: int
) -> RateLimiter:
    """
    Obtém rate limiter global
    
    Args:
        name: Nome do limiter
        limit: Limite de requisições
        window: Janela em segundos
    
    Returns:
        Rate limiter
    """
    global _limiter_manager
    if _limiter_manager is None:
        _limiter_manager = RateLimiterManager()
    return _limiter_manager.get_limiter(name, limit, window)


# Presets comuns
def get_openai_limiter() -> RateLimiter:
    """Rate limiter para OpenAI (60 req/min para tier 1)"""
    return get_rate_limiter('openai', limit=60, window=60)


def get_anthropic_limiter() -> RateLimiter:
    """Rate limiter para Anthropic (50 req/min)"""
    return get_rate_limiter('anthropic', limit=50, window=60)


def get_web_search_limiter() -> RateLimiter:
    """Rate limiter para pesquisa web (10 req/min)"""
    return get_rate_limiter('web_search', limit=10, window=60)
