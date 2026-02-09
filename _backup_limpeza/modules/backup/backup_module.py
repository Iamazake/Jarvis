# -*- coding: utf-8 -*-
"""
Backup Module - Módulo de Backup e Sincronização
Backup de memórias e configurações

Autor: JARVIS Team
Versão: 3.1.0
"""

from typing import Dict, Any, Optional, List

from core.logger import get_logger
from .sync_manager import SyncManager

logger = get_logger(__name__)


class BackupModule:
    """
    Módulo de backup.
    
    Funcionalidades:
    - Backup de configurações
    - Snapshot de memórias
    - Listagem e restauração de backups
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._running = False
        self.status = '🔴'
        self.sync = SyncManager()
    
    async def start(self):
        """Inicializa o módulo."""
        logger.info("💾 Iniciando módulo de backup...")
        self._running = True
        self.status = '🟢'
        logger.info("✅ Módulo de backup pronto")
    
    async def stop(self):
        """Para o módulo."""
        self._running = False
        self.status = '🔴'
    
    async def process(
        self,
        message: str,
        intent,
        context: Dict,
        metadata: Dict
    ) -> str:
        """Processa comandos do módulo."""
        msg_lower = message.lower().strip()
        
        if 'backup' in msg_lower or 'fazer backup' in msg_lower or 'criar backup' in msg_lower:
            try:
                path = self.sync.backup_config()
                return f"✅ Backup de configuração criado: `{path}`"
            except Exception as e:
                logger.error(f"Erro no backup: {e}")
                return f"❌ Erro ao criar backup: {e}"
        
        if 'listar backup' in msg_lower or 'listar backups' in msg_lower:
            configs = self.sync.list_backups('config_')
            if not configs:
                return "Nenhum backup de configuração encontrado."
            lines = ["📂 **Backups de configuração**\n"]
            for b in configs[:10]:
                lines.append(f"• {b['name']} ({b['modified'][:10]})")
            return "\n".join(lines)
        
        if 'restaurar' in msg_lower and 'config' in msg_lower:
            # Usuário pode especificar nome do arquivo em mensagem futura
            return "Para restaurar, use: 'restaurar config [nome_do_arquivo]' (ex: config_20260205_120000.json)"
        
        return "Comandos: 'fazer backup', 'listar backups'"
    
    def backup_config_now(self) -> str:
        """Cria backup de config (uso programático)."""
        return self.sync.backup_config()
    
    def backup_memories_now(self, memory_data: Dict[str, Any]) -> str:
        """Cria backup de memórias (uso programático)."""
        return self.sync.backup_memories(memory_data)
    
    def list_backups(self, prefix: str = '') -> List[Dict[str, Any]]:
        """Lista backups (uso programático)."""
        return self.sync.list_backups(prefix)
    
    def is_available(self) -> bool:
        return self._running
