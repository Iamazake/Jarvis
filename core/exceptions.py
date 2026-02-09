# -*- coding: utf-8 -*-
"""
JARVIS Exceptions - Hierarquia de Exceções Customizadas
Sistema unificado de tratamento de erros

Autor: JARVIS Team
Versão: 3.1.0
"""

from typing import Optional, Dict, Any


class JarvisException(Exception):
    """
    Exceção base para todos os erros do JARVIS
    
    Attributes:
        message: Mensagem de erro
        error_code: Código de erro opcional
        details: Detalhes adicionais do erro
        module: Módulo onde o erro ocorreu
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        module: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.module = module
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.error_code:
            parts.append(f"[{self.error_code}]")
        if self.module:
            parts.append(f"(módulo: {self.module})")
        return " ".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte exceção para dicionário"""
        return {
            'error': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'module': self.module,
            'details': self.details
        }


class ModuleException(JarvisException):
    """Erro em módulo específico"""
    pass


class AIModuleException(ModuleException):
    """Erro no módulo de IA"""
    pass


class VoiceModuleException(ModuleException):
    """Erro no módulo de voz"""
    pass


class SearchModuleException(ModuleException):
    """Erro no módulo de pesquisa"""
    pass


class ToolsModuleException(ModuleException):
    """Erro no módulo de ferramentas"""
    pass


class MemoryModuleException(ModuleException):
    """Erro no módulo de memória"""
    pass


class AIException(JarvisException):
    """Erro na IA (provider, API, etc)"""
    pass


class AIProviderException(AIException):
    """Erro específico de provider de IA"""
    
    def __init__(
        self,
        provider: str,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            module='ai'
        )
        self.provider = provider


class AIAPIException(AIException):
    """Erro na chamada à API de IA"""
    
    def __init__(
        self,
        provider: str,
        status_code: Optional[int] = None,
        response: Optional[str] = None,
        message: Optional[str] = None
    ):
        msg = message or f"Erro na API {provider}"
        if status_code:
            msg += f" (status: {status_code})"
        super().__init__(
            message=msg,
            error_code=f"AI_API_{status_code or 'UNKNOWN'}",
            details={
                'provider': provider,
                'status_code': status_code,
                'response': response
            },
            module='ai'
        )
        self.status_code = status_code
        self.response = response


class ToolException(JarvisException):
    """Erro em ferramenta/MCP tool"""
    
    def __init__(
        self,
        tool_name: str,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            module='tools'
        )
        self.tool_name = tool_name


class ConfigurationException(JarvisException):
    """Erro de configuração"""
    pass


class ValidationException(JarvisException):
    """Erro de validação de dados"""
    
    def __init__(
        self,
        field: str,
        value: Any,
        message: str,
        error_code: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code or 'VALIDATION_ERROR',
            details={'field': field, 'value': str(value)}
        )
        self.field = field
        self.value = value


class DatabaseException(JarvisException):
    """Erro de banco de dados"""
    pass


class CacheException(JarvisException):
    """Erro no cache"""
    pass


class RateLimitException(JarvisException):
    """Erro de rate limiting"""
    
    def __init__(
        self,
        resource: str,
        limit: int,
        window: int,
        retry_after: Optional[int] = None
    ):
        message = f"Rate limit excedido para {resource} ({limit} requisições por {window}s)"
        super().__init__(
            message=message,
            error_code='RATE_LIMIT_EXCEEDED',
            details={
                'resource': resource,
                'limit': limit,
                'window': window,
                'retry_after': retry_after
            }
        )
        self.resource = resource
        self.limit = limit
        self.window = window
        self.retry_after = retry_after


class CircuitBreakerOpenException(JarvisException):
    """Erro quando circuit breaker está aberto"""
    
    def __init__(self, resource: str, retry_after: Optional[int] = None):
        message = f"Circuit breaker aberto para {resource}"
        if retry_after:
            message += f". Tente novamente em {retry_after}s"
        super().__init__(
            message=message,
            error_code='CIRCUIT_BREAKER_OPEN',
            details={'resource': resource, 'retry_after': retry_after}
        )
        self.resource = resource
        self.retry_after = retry_after
