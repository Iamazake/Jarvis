# -*- coding: utf-8 -*-
"""
Error Handler - Gerenciador Centralizado de Erros
Tratamento e recuperação de erros

Autor: JARVIS Team
Versão: 3.1.0
"""

import logging
import traceback
from typing import Optional, Callable, Dict, Any
from functools import wraps

from .exceptions import JarvisException

logger = logging.getLogger(__name__)


class ErrorHandler:
    """
    Gerenciador centralizado de erros
    
    Funcionalidades:
    - Captura e loga erros
    - Formata mensagens de erro
    - Retry automático para erros recuperáveis
    - Fallback para erros críticos
    """
    
    def __init__(self):
        self.error_count: Dict[str, int] = {}
        self.retry_strategies: Dict[str, Callable] = {}
    
    def handle(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        retry: bool = False,
        max_retries: int = 3
    ) -> str:
        """
        Trata um erro e retorna mensagem formatada
        
        Args:
            error: Exceção capturada
            context: Contexto adicional
            retry: Se deve tentar retry
            max_retries: Máximo de tentativas
        
        Returns:
            Mensagem de erro formatada para o usuário
        """
        context = context or {}
        
        # Incrementa contador
        error_type = type(error).__name__
        self.error_count[error_type] = self.error_count.get(error_type, 0) + 1
        
        # Loga erro completo
        self._log_error(error, context)
        
        # Formata mensagem para usuário
        user_message = self._format_user_message(error, context)
        
        return user_message
    
    def _log_error(self, error: Exception, context: Dict[str, Any]):
        """Loga erro com contexto completo"""
        error_type = type(error).__name__
        
        log_data = {
            'error_type': error_type,
            'error_message': str(error),
            **context
        }
        
        # Adiciona detalhes se for JarvisException
        if isinstance(error, JarvisException):
            log_data.update({
                'error_code': error.error_code,
                'module': error.module,
                'details': error.details
            })
        
        logger.error(
            f"Erro capturado: {error_type}",
            extra=log_data,
            exc_info=True
        )
    
    def _format_user_message(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> str:
        """
        Formata mensagem amigável para o usuário
        
        Não expõe detalhes técnicos, apenas mensagem clara
        """
        # Se for JarvisException, usa mensagem customizada
        if isinstance(error, JarvisException):
            return error.message
        
        # Mensagens padrão por tipo de erro
        error_type = type(error).__name__
        
        user_messages = {
            'ConnectionError': 'Desculpe, não consegui conectar ao serviço. Verifique sua conexão.',
            'TimeoutError': 'A operação demorou muito. Tente novamente.',
            'ValueError': 'Dados inválidos fornecidos.',
            'KeyError': 'Informação não encontrada.',
            'PermissionError': 'Sem permissão para executar esta ação.',
            'FileNotFoundError': 'Arquivo não encontrado.',
            'ImportError': 'Módulo não disponível.',
        }
        
        return user_messages.get(
            error_type,
            'Desculpe, ocorreu um erro inesperado. Tente novamente.'
        )
    
    def wrap_async(self, func: Callable):
        """
        Decorator para capturar erros em funções assíncronas
        
        Usage:
            @error_handler.wrap_async
            async def minha_funcao():
                ...
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                context = {
                    'function': func.__name__,
                    'args': str(args)[:100],
                    'kwargs': str(kwargs)[:100]
                }
                error_msg = self.handle(e, context)
                raise JarvisException(error_msg) from e
        
        return wrapper
    
    def wrap_sync(self, func: Callable):
        """
        Decorator para capturar erros em funções síncronas
        
        Usage:
            @error_handler.wrap_sync
            def minha_funcao():
                ...
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = {
                    'function': func.__name__,
                    'args': str(args)[:100],
                    'kwargs': str(kwargs)[:100]
                }
                error_msg = self.handle(e, context)
                raise JarvisException(error_msg) from e
        
        return wrapper
    
    def get_error_stats(self) -> Dict[str, int]:
        """Retorna estatísticas de erros"""
        return self.error_count.copy()
    
    def reset_stats(self):
        """Reseta estatísticas de erros"""
        self.error_count.clear()


# Instância global
_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Retorna instância global do error handler"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler
