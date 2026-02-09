# -*- coding: utf-8 -*-
"""
Audit Log - Log de Auditoria
Registro de ações sensíveis

Autor: JARVIS Team
Versão: 3.1.0
"""

from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import json

from core.logger import get_logger

logger = get_logger(__name__)


class AuditLog:
    """Log de auditoria para ações sensíveis."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path(__file__).parent.parent.parent
        self.log_dir = self.base_dir / 'data' / 'audit'
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._file = self.log_dir / 'audit.jsonl'
    
    def log(
        self,
        action: str,
        user: str = 'system',
        resource: str = '',
        details: Optional[Dict[str, Any]] = None,
        success: bool = True
    ):
        """Registra entrada de auditoria."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'user': user,
            'resource': resource,
            'success': success,
            'details': details or {}
        }
        try:
            with open(self._file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"Erro ao escrever audit log: {e}")
    
    def read_recent(self, n: int = 50) -> list:
        """Lê as últimas n entradas."""
        if not self._file.exists():
            return []
        lines = []
        try:
            with open(self._file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            logger.error(f"Erro ao ler audit log: {e}")
            return []
        
        result = []
        for line in lines[-n:]:
            line = line.strip()
            if line:
                try:
                    result.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return result
