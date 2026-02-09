# -*- coding: utf-8 -*-
"""Módulo de Segurança (PIN e auditoria)."""
import logging
from typing import Dict, Any, Optional
from .auth_manager import AuthManager
from .audit_log import AuditLog

logger = logging.getLogger(__name__)


class SecurityModule:
    def __init__(self, config):
        self.config = config
        self._running = False
        self.status = '🔴'
        self.auth = AuthManager(config)
        self.audit = AuditLog()

    async def start(self):
        logger.info("🔐 Iniciando módulo de segurança...")
        self._running = True
        self.status = '🟢'

    async def stop(self):
        self._running = False
        self.status = '🔴'

    def require_pin(self, pin: str) -> bool:
        return self.auth.verify_pin(pin)

    def audit_action(self, action: str, user: str = 'user', resource: str = '', details: Optional[Dict] = None):
        self.audit.log(action=action, user=user, resource=resource, details=details)

    async def process(self, message: str, intent, context: Dict, metadata: Dict) -> str:
        msg_lower = message.lower().strip()
        if 'configurar pin' in msg_lower or 'definir pin' in msg_lower:
            return "Para configurar PIN: 'configurar pin [seu_pin]' (mínimo 4 dígitos)."
        if 'últimas ações' in msg_lower or 'ultimas acoes' in msg_lower or 'auditoria' in msg_lower:
            entries = self.audit.read_recent(15)
            if not entries:
                return "Nenhuma entrada de auditoria recente."
            lines = ["📋 **Últimas ações (auditoria)**\n"]
            for e in entries:
                lines.append(f"• {e.get('timestamp', '')[:19]} | {e.get('action', '')} | {e.get('resource', '')}")
            return "\n".join(lines)
        return "Comandos: 'configurar pin', 'últimas ações (auditoria)'"
