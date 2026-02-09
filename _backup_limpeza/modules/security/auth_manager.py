# -*- coding: utf-8 -*-
"""
Auth Manager - Gerenciador de Autenticação
Autenticação simples por PIN/token (expansível)

Autor: JARVIS Team
Versão: 3.1.0
"""

import os
import hashlib
import secrets
from typing import Optional, Dict, Any
from pathlib import Path

from core.logger import get_logger

logger = get_logger(__name__)


class AuthManager:
    """
    Gerenciador de autenticação.
    
    Por padrão usa variável de ambiente JARVIS_PIN ou arquivo .pin.
    Expansível para múltiplos usuários e tokens.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        base = config.get('base_dir') if isinstance(config, dict) else getattr(config, 'base_dir', None)
        self.base_dir = Path(base) if base else Path(__file__).parent.parent.parent
        self._pin_file = self.base_dir / '.jarvis_pin_hash'
        self._sessions: Dict[str, float] = {}  # token -> timestamp
        self._session_ttl = int(config.get('SESSION_TTL_SECONDS', 3600))
    
    def _hash_pin(self, pin: str) -> str:
        return hashlib.sha256(pin.encode()).hexdigest()
    
    def set_pin(self, pin: str) -> bool:
        """Define PIN (salva hash)."""
        if len(pin) < 4:
            return False
        self._pin_file.parent.mkdir(parents=True, exist_ok=True)
        self._pin_file.write_text(self._hash_pin(pin), encoding='utf-8')
        logger.info("PIN configurado")
        return True
    
    def verify_pin(self, pin: str) -> bool:
        """Verifica PIN."""
        env_pin = os.getenv('JARVIS_PIN')
        if env_pin and env_pin == pin:
            return True
        if self._pin_file.exists():
            return self._hash_pin(pin) == self._pin_file.read_text(encoding='utf-8').strip()
        return False
    
    def create_session(self, pin: str) -> Optional[str]:
        """Cria sessão e retorna token se PIN válido."""
        if not self.verify_pin(pin):
            return None
        token = secrets.token_urlsafe(32)
        self._sessions[token] = __import__('time').time()
        return token
    
    def verify_session(self, token: str) -> bool:
        """Verifica se token de sessão é válido."""
        import time
        if token not in self._sessions:
            return False
        if time.time() - self._sessions[token] > self._session_ttl:
            del self._sessions[token]
            return False
        return True
    
    def revoke_session(self, token: str):
        """Invalida sessão."""
        self._sessions.pop(token, None)
