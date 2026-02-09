# -*- coding: utf-8 -*-
"""Módulo de Backup e Sincronização."""
import logging
from typing import Dict, Any, List
from .sync_manager import SyncManager

logger = logging.getLogger(__name__)


class BackupModule:
    def __init__(self, config):
        self.config = config
        self._running = False
        self.status = '🔴'
        self.sync = SyncManager()

    async def start(self):
        logger.info("💾 Iniciando módulo de backup...")
        self._running = True
        self.status = '🟢'

    async def stop(self):
        self._running = False
        self.status = '🔴'

    async def process(self, message: str, intent, context: Dict, metadata: Dict) -> str:
        msg_lower = message.lower().strip()
        if 'backup' in msg_lower or 'fazer backup' in msg_lower or 'criar backup' in msg_lower:
            try:
                path = self.sync.backup_config()
                return f"✅ Backup de configuração criado: `{path}`"
            except Exception as e:
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
            return "Para restaurar: 'restaurar config [nome_do_arquivo]' (ex: config_20260205_120000.json)"
        return "Comandos: 'fazer backup', 'listar backups'"
