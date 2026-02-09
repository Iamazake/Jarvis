# -*- coding: utf-8 -*-
"""Autenticação por PIN/sessão."""
import os
import hashlib
import secrets
import time
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


def _config_get(c, key, default=None):
    return c.get(key, default) if hasattr(c, 'get') and callable(getattr(c, 'get')) else getattr(c, key, default)


class AuthManager:
    def __init__(self, config):
        self.config = config
        base = _config_get(config, 'base_dir')
        self.base_dir = Path(base) if base else Path(__file__).resolve().parent.parent.parent
        self._pin_file = self.base_dir / '.jarvis_pin_hash'
        self._sessions: Dict[str, float] = {}
        self._session_ttl = int(_config_get(config, 'SESSION_TTL_SECONDS', 3600))

    def _hash_pin(self, pin: str) -> str:
        return hashlib.sha256(pin.encode()).hexdigest()

    def set_pin(self, pin: str) -> bool:
        if len(pin) < 4:
            return False
        self._pin_file.parent.mkdir(parents=True, exist_ok=True)
        self._pin_file.write_text(self._hash_pin(pin), encoding='utf-8')
        return True

    def verify_pin(self, pin: str) -> bool:
        if os.getenv('JARVIS_PIN') == pin:
            return True
        if self._pin_file.exists():
            return self._hash_pin(pin) == self._pin_file.read_text(encoding='utf-8').strip()
        return False

    def create_session(self, pin: str) -> Optional[str]:
        if not self.verify_pin(pin):
            return None
        token = secrets.token_urlsafe(32)
        self._sessions[token] = time.time()
        return token

    def verify_session(self, token: str) -> bool:
        if token not in self._sessions:
            return False
        if time.time() - self._sessions[token] > self._session_ttl:
            del self._sessions[token]
            return False
        return True
