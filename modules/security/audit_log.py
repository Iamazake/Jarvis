# -*- coding: utf-8 -*-
"""Log de auditoria (JSONL)."""
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class AuditLog:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent
        self.log_dir = self.base_dir / 'data' / 'audit'
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._file = self.log_dir / 'audit.jsonl'

    def log(self, action: str, user: str = 'system', resource: str = '', details: Optional[Dict[str, Any]] = None, success: bool = True):
        entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action, 'user': user, 'resource': resource, 'success': success, 'details': details or {}
        }
        try:
            with open(self._file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error("Audit log: %s", e)

    def read_recent(self, n: int = 50) -> list:
        if not self._file.exists():
            return []
        result = []
        try:
            with open(self._file, 'r', encoding='utf-8') as f:
                for line in f.readlines()[-n:]:
                    line = line.strip()
                    if line:
                        try:
                            result.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            logger.error("Audit read: %s", e)
        return result
