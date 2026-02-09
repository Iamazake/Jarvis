# -*- coding: utf-8 -*-
"""
Logger - Sistema de Logging Estruturado
Logging com contexto e formatação consistente

Autor: JARVIS Team
Versão: 3.1.0
"""

import logging
import sys
import json
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path


class StructuredFormatter(logging.Formatter):
    """
    Formatter que produz logs estruturados em JSON
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Formata log como JSON estruturado"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Adiciona contexto extra se existir
        if hasattr(record, 'context'):
            log_data['context'] = record.context
        
        # Adiciona campos extras
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename',
                          'funcName', 'levelname', 'levelno', 'lineno',
                          'module', 'msecs', 'message', 'pathname', 'process',
                          'processName', 'relativeCreated', 'thread', 'threadName',
                          'exc_info', 'exc_text', 'stack_info', 'context']:
                log_data[key] = value
        
        # Adiciona exception se houver
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


class ColoredFormatter(logging.Formatter):
    """
    Formatter colorido para terminal
    """
    
    # Cores ANSI
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Formata log com cores"""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Formata timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # Formata mensagem
        message = record.getMessage()
        
        # Adiciona contexto se existir
        context_str = ""
        if hasattr(record, 'context') and record.context:
            context_str = f" | {json.dumps(record.context, ensure_ascii=False)}"
        
        # Formata
        formatted = (
            f"{color}[{timestamp}] {record.levelname:8s}{reset} | "
            f"{record.name} | {message}{context_str}"
        )
        
        # Adiciona exception se houver
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        return formatted


class JarvisLogger:
    """
    Logger customizado para JARVIS com contexto
    """
    
    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        log_file: Optional[Path] = None,
        structured: bool = False,
        colored: bool = True
    ):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Remove handlers existentes
        self.logger.handlers.clear()
        
        # Handler para console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        if colored and sys.stdout.isatty():
            console_handler.setFormatter(ColoredFormatter())
        else:
            console_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                    datefmt='%H:%M:%S'
                )
            )
        
        self.logger.addHandler(console_handler)
        
        # Handler para arquivo se especificado
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(level)
            
            if structured:
                file_handler.setFormatter(StructuredFormatter())
            else:
                file_handler.setFormatter(
                    logging.Formatter(
                        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S'
                    )
                )
            
            self.logger.addHandler(file_handler)
    
    def _log_with_context(
        self,
        level: int,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Loga com contexto adicional"""
        extra = {'context': context or {}}
        extra.update(kwargs)
        self.logger.log(level, message, extra=extra)
    
    def debug(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Log de debug"""
        self._log_with_context(logging.DEBUG, message, context, **kwargs)
    
    def info(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Log de informação"""
        self._log_with_context(logging.INFO, message, context, **kwargs)
    
    def warning(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Log de aviso"""
        self._log_with_context(logging.WARNING, message, context, **kwargs)
    
    def error(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        exc_info: bool = False,
        **kwargs
    ):
        """Log de erro"""
        if exc_info:
            kwargs['exc_info'] = True
        self._log_with_context(logging.ERROR, message, context, **kwargs)
    
    def critical(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        exc_info: bool = False,
        **kwargs
    ):
        """Log crítico"""
        if exc_info:
            kwargs['exc_info'] = True
        self._log_with_context(logging.CRITICAL, message, context, **kwargs)


def get_logger(
    name: str,
    level: Optional[int] = None,
    log_file: Optional[Path] = None,
    structured: bool = False
) -> JarvisLogger:
    """
    Cria ou retorna logger configurado
    
    Args:
        name: Nome do logger (geralmente __name__)
        level: Nível de log (default: INFO)
        log_file: Arquivo para logs (opcional)
        structured: Se deve usar formato JSON estruturado
    
    Returns:
        Logger configurado
    """
    if level is None:
        import os
        level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
        level = getattr(logging, level_str, logging.INFO)
    
    return JarvisLogger(name, level, log_file, structured)


# Função de conveniência para substituir logging.getLogger()
def setup_logging(
    level: Optional[int] = None,
    log_file: Optional[Path] = None,
    structured: bool = False
):
    """
    Configura logging global do JARVIS
    
    Args:
        level: Nível de log
        log_file: Arquivo para logs
        structured: Formato estruturado
    """
    if level is None:
        import os
        level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
        level = getattr(logging, level_str, logging.INFO)
    
    # Configura root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove handlers existentes
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    if sys.stdout.isatty():
        console_handler.setFormatter(ColoredFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%H:%M:%S'
            )
        )
    
    root_logger.addHandler(console_handler)
    
    # File handler se especificado
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        
        if structured:
            file_handler.setFormatter(StructuredFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            )
        
        root_logger.addHandler(file_handler)
