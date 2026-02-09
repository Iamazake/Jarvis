# -*- coding: utf-8 -*-
"""
Security Module - Módulo de Segurança
Autenticação e auditoria

Autor: JARVIS Team
Versão: 3.1.0
"""

from typing import Dict, Any, Optional

from core.logger import get_logger
from .auth_manager import AuthManager
from .audit_log import AuditLog

logger = get_logger(__name__)


class SecurityModule:
    """
    Módulo de segurança.
    
    Funcionalidades:
    - Autenticação por PIN
    - Log de auditoria
    - Controle de acesso a comandos sensíveis (estrutura)
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._running = False
        self.status = '🔴'
        self.auth = AuthManager(config)
        self.audit = AuditLog()
    
    async def start(self):
        """Inicializa o módulo."""
        logger.info("🔐 Iniciando módulo de segurança...")
        self._running = True
        self.status = '🟢'
        logger.info("✅ Módulo de segurança pronto")
    
    async def stop(self):
        """Para o módulo."""
        self._running = False
        self.status = '🔴'
    
    def require_pin(self, pin: str) -> bool:
        """Verifica PIN. Retorna True se válido."""
        return self.auth.verify_pin(pin)
    
    def audit_action(self, action: str, user: str = 'user', resource: str = '', details: Optional[Dict] = None):
        """Registra ação no log de auditoria."""
        self.audit.log(action=action, user=user, resource=resource, details=details)
    
    async def process(
        self,
        message: str,
        intent,
        context: Dict,
        metadata: Dict
    ) -> str:
        """Processa comandos do módulo."""
        msg_lower = message.lower().strip()
        
        if 'configurar pin' in msg_lower or 'definir pin' in msg_lower:
            return "Para configurar PIN, use: 'configurar pin [seu_pin]' (mínimo 4 dígitos)."
        
        if 'últimas ações' in msg_lower or 'ultimas acoes' in msg_lower or 'auditoria' in msg_lower:
            entries = self.audit.read_recent(15)
            if not entries:
                return "Nenhuma entrada de auditoria recente."
            lines = ["📋 **Últimas ações (auditoria)**\n"]
            for e in entries:
                lines.append(f"• {e['timestamp'][:19]} | {e['action']} | {e.get('resource', '')}")
            return "\n".join(lines)
        
        return "Comandos: 'configurar pin', 'últimas ações (auditoria)'"
    
    def is_available(self) -> bool:
        return self._running
