# -*- coding: utf-8 -*-
"""
File Manager - Gerenciamento de Arquivos
"""

import asyncio
import os
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class FileManager:
    """
    Gerencia arquivos e pastas
    
    Funcionalidades:
    - Criar/deletar arquivos e pastas
    - Listar diretórios
    - Mover/copiar arquivos
    - Organizar downloads por tipo
    """
    
    def __init__(self, config):
        self.config = config
        
        # Diretórios padrão
        home = Path.home()
        self.downloads = Path(config.get('DOWNLOADS_PATH', '~/Downloads')).expanduser()
        self.documents = Path(config.get('DOCUMENTS_PATH', '~/Documents')).expanduser()
        
        # Mapeamento de extensões para categorias
        self.file_categories = {
            'Imagens': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'],
            'Videos': ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv'],
            'Audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'],
            'Documentos': ['.pdf', '.doc', '.docx', '.txt', '.xlsx', '.pptx', '.odt'],
            'Compactados': ['.zip', '.rar', '.7z', '.tar', '.gz'],
            'Código': ['.py', '.js', '.html', '.css', '.java', '.cpp', '.json'],
            'Executáveis': ['.exe', '.msi', '.dmg', '.deb', '.rpm'],
        }
    
    async def list_directory(self, path: str = '.') -> List[Dict]:
        """
        Lista conteúdo de um diretório
        
        Returns:
            Lista de dicts com name, is_dir, size, modified
        """
        try:
            p = Path(path).expanduser()
            
            if not p.exists():
                return []
            
            loop = asyncio.get_event_loop()
            
            def _list():
                items = []
                for item in p.iterdir():
                    try:
                        stat = item.stat()
                        items.append({
                            'name': item.name,
                            'path': str(item),
                            'is_dir': item.is_dir(),
                            'size': stat.st_size if not item.is_dir() else 0,
                            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
                    except PermissionError:
                        continue
                return sorted(items, key=lambda x: (not x['is_dir'], x['name'].lower()))
            
            return await loop.run_in_executor(None, _list)
            
        except Exception as e:
            logger.error(f"Erro listando diretório: {e}")
            return []
    
    async def create_directory(self, path: str) -> Optional[str]:
        """Cria diretório"""
        try:
            p = Path(path).expanduser()
            p.mkdir(parents=True, exist_ok=True)
            return str(p)
        except Exception as e:
            logger.error(f"Erro criando diretório: {e}")
            return None
    
    async def create_file(self, path: str, content: str = '') -> Optional[str]:
        """Cria arquivo com conteúdo opcional"""
        try:
            p = Path(path).expanduser()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding='utf-8')
            return str(p)
        except Exception as e:
            logger.error(f"Erro criando arquivo: {e}")
            return None
    
    async def delete(self, path: str, force: bool = False) -> bool:
        """
        Deleta arquivo ou pasta
        
        Args:
            path: Caminho para deletar
            force: Se True, deleta pastas não vazias
        """
        try:
            p = Path(path).expanduser()
            
            if not p.exists():
                return True
            
            if p.is_dir():
                if force:
                    shutil.rmtree(p)
                else:
                    p.rmdir()  # Só funciona se vazia
            else:
                p.unlink()
            
            return True
            
        except Exception as e:
            logger.error(f"Erro deletando: {e}")
            return False
    
    async def move(self, source: str, destination: str) -> bool:
        """Move arquivo/pasta"""
        try:
            src = Path(source).expanduser()
            dst = Path(destination).expanduser()
            
            # Se destino é diretório, move para dentro
            if dst.is_dir():
                dst = dst / src.name
            
            shutil.move(str(src), str(dst))
            return True
            
        except Exception as e:
            logger.error(f"Erro movendo: {e}")
            return False
    
    async def copy(self, source: str, destination: str) -> bool:
        """Copia arquivo/pasta"""
        try:
            src = Path(source).expanduser()
            dst = Path(destination).expanduser()
            
            if src.is_dir():
                shutil.copytree(str(src), str(dst))
            else:
                shutil.copy2(str(src), str(dst))
            
            return True
            
        except Exception as e:
            logger.error(f"Erro copiando: {e}")
            return False
    
    async def organize_downloads(self) -> int:
        """
        Organiza arquivos em Downloads por categoria
        
        Returns:
            Número de arquivos movidos
        """
        if not self.downloads.exists():
            return 0
        
        moved = 0
        
        for file in self.downloads.iterdir():
            if file.is_dir():
                continue
            
            ext = file.suffix.lower()
            
            # Encontra categoria
            category = 'Outros'
            for cat, extensions in self.file_categories.items():
                if ext in extensions:
                    category = cat
                    break
            
            # Cria pasta da categoria e move
            dest_folder = self.downloads / category
            dest_folder.mkdir(exist_ok=True)
            
            try:
                shutil.move(str(file), str(dest_folder / file.name))
                moved += 1
                logger.debug(f"Movido: {file.name} -> {category}")
            except Exception as e:
                logger.debug(f"Erro movendo {file.name}: {e}")
        
        return moved
    
    async def search(self, pattern: str, path: str = '.', 
                     recursive: bool = True) -> List[str]:
        """
        Busca arquivos por padrão
        
        Args:
            pattern: Padrão glob (ex: "*.txt")
            path: Diretório inicial
            recursive: Buscar em subpastas
        """
        try:
            p = Path(path).expanduser()
            
            if recursive:
                matches = list(p.rglob(pattern))
            else:
                matches = list(p.glob(pattern))
            
            return [str(m) for m in matches[:100]]  # Limita resultados
            
        except Exception as e:
            logger.error(f"Erro buscando: {e}")
            return []
    
    def format_size(self, size: int) -> str:
        """Formata tamanho em bytes para humano"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
