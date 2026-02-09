# -*- coding: utf-8 -*-
"""
Sync Manager - Gerenciador de Backup e Sincronização
Backup de memórias e configurações

Autor: JARVIS Team
Versão: 3.1.0
"""

import os
import json
import shutil
import hashlib
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from core.logger import get_logger

logger = get_logger(__name__)


class SyncManager:
    """
    Gerencia backup e versionamento de dados do JARVIS.
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path(__file__).parent.parent.parent
        self.backup_dir = self.base_dir / 'data' / 'backups'
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._max_backups = int(os.getenv('BACKUP_MAX_COUNT', '10'))
    
    def backup_config(self) -> str:
        """Cria backup do config.json. Retorna caminho do arquivo."""
        config_path = self.base_dir / 'config.json'
        if not config_path.exists():
            raise FileNotFoundError("config.json não encontrado")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dest = self.backup_dir / f'config_{timestamp}.json'
        shutil.copy2(config_path, dest)
        logger.info(f"Backup de config: {dest}")
        self._prune_old_backups('config_')
        return str(dest)
    
    def backup_memories(self, memory_data: Dict[str, Any]) -> str:
        """Salva snapshot das memórias. Retorna caminho do arquivo."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dest = self.backup_dir / f'memories_{timestamp}.json'
        with open(dest, 'w', encoding='utf-8') as f:
            json.dump(memory_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Backup de memórias: {dest}")
        self._prune_old_backups('memories_')
        return str(dest)
    
    def list_backups(self, prefix: str = '') -> List[Dict[str, Any]]:
        """Lista backups disponíveis."""
        result = []
        for f in sorted(self.backup_dir.glob(f'{prefix}*'), reverse=True):
            if f.suffix in ('.json', '.zip'):
                stat = f.stat()
                result.append({
                    'path': str(f),
                    'name': f.name,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        return result[: self._max_backups * 2]
    
    def restore_config(self, backup_name: str) -> bool:
        """Restaura config a partir de um backup."""
        path = self.backup_dir / backup_name
        if not path.exists() or not backup_name.startswith('config_'):
            return False
        
        config_path = self.base_dir / 'config.json'
        shutil.copy2(path, config_path)
        logger.info(f"Config restaurado de {backup_name}")
        return True
    
    def _prune_old_backups(self, prefix: str):
        """Remove backups antigos além do limite."""
        files = sorted(
            self.backup_dir.glob(f'{prefix}*'),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        for f in files[self._max_backups:]:
            try:
                f.unlink()
                logger.debug(f"Backup antigo removido: {f.name}")
            except OSError as e:
                logger.warning(f"Erro ao remover {f}: {e}")
