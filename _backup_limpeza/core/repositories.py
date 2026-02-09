# -*- coding: utf-8 -*-
"""
Repositories - Repository Pattern para Acesso a Dados
Abstração de acesso a dados

Autor: JARVIS Team
Versão: 3.1.0
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Generic, TypeVar
from datetime import datetime

from .logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """
    Repositório base abstrato
    
    Define interface comum para acesso a dados
    """
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """Cria nova entidade"""
        pass
    
    @abstractmethod
    async def get_by_id(self, id: Any) -> Optional[T]:
        """Obtém entidade por ID"""
        pass
    
    @abstractmethod
    async def update(self, id: Any, entity: T) -> Optional[T]:
        """Atualiza entidade"""
        pass
    
    @abstractmethod
    async def delete(self, id: Any) -> bool:
        """Deleta entidade"""
        pass
    
    @abstractmethod
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Lista todas as entidades"""
        pass


class MemoryRepository(BaseRepository[T]):
    """
    Repositório em memória (para testes/desenvolvimento)
    """
    
    def __init__(self):
        self._storage: Dict[Any, T] = {}
        self._next_id = 1
    
    async def create(self, entity: T) -> T:
        """Cria entidade"""
        entity_id = self._next_id
        self._next_id += 1
        
        # Assume que entidade tem atributo id
        if hasattr(entity, 'id'):
            entity.id = entity_id
        
        self._storage[entity_id] = entity
        logger.debug(f"Entidade criada: {entity_id}")
        return entity
    
    async def get_by_id(self, id: Any) -> Optional[T]:
        """Obtém por ID"""
        return self._storage.get(id)
    
    async def update(self, id: Any, entity: T) -> Optional[T]:
        """Atualiza entidade"""
        if id not in self._storage:
            return None
        
        self._storage[id] = entity
        logger.debug(f"Entidade atualizada: {id}")
        return entity
    
    async def delete(self, id: Any) -> bool:
        """Deleta entidade"""
        if id in self._storage:
            del self._storage[id]
            logger.debug(f"Entidade deletada: {id}")
            return True
        return False
    
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Lista todas"""
        items = list(self._storage.values())
        return items[offset:offset + limit]
    
    def clear(self):
        """Limpa repositório"""
        self._storage.clear()
        self._next_id = 1


class ConversationRepository(BaseRepository[Dict[str, Any]]):
    """
    Repositório para conversas
    """
    
    def __init__(self, db_connection=None):
        self.db = db_connection
        self._table = 'conversations'
    
    async def create(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Cria conversa"""
        # Implementação específica para banco de dados
        # Por enquanto, retorna entidade
        logger.debug("Conversa criada")
        return entity
    
    async def get_by_id(self, id: Any) -> Optional[Dict[str, Any]]:
        """Obtém conversa por ID"""
        # Implementação específica
        return None
    
    async def update(self, id: Any, entity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Atualiza conversa"""
        return None
    
    async def delete(self, id: Any) -> bool:
        """Deleta conversa"""
        return False
    
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Lista conversas"""
        return []
    
    async def get_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Obtém conversas de uma sessão"""
        return []
    
    async def get_recent(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Obtém conversas recentes"""
        return []


class MemoryRepository(BaseRepository[Dict[str, Any]]):
    """
    Repositório para memórias
    """
    
    def __init__(self, db_connection=None):
        self.db = db_connection
        self._table = 'memories'
    
    async def create(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Cria memória"""
        return entity
    
    async def get_by_id(self, id: Any) -> Optional[Dict[str, Any]]:
        """Obtém memória por ID"""
        return None
    
    async def update(self, id: Any, entity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Atualiza memória"""
        return None
    
    async def delete(self, id: Any) -> bool:
        """Deleta memória"""
        return False
    
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Lista memórias"""
        return []
    
    async def get_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Obtém memórias por categoria"""
        return []
    
    async def get_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        """Obtém memória por chave"""
        return None


class EventRepository(BaseRepository[Dict[str, Any]]):
    """
    Repositório para eventos do sistema
    """
    
    def __init__(self, db_connection=None):
        self.db = db_connection
        self._table = 'events'
    
    async def create(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Cria evento"""
        return entity
    
    async def get_by_id(self, id: Any) -> Optional[Dict[str, Any]]:
        """Obtém evento por ID"""
        return None
    
    async def update(self, id: Any, entity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Atualiza evento"""
        return None
    
    async def delete(self, id: Any) -> bool:
        """Deleta evento"""
        return False
    
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Lista eventos"""
        return []
    
    async def get_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Obtém eventos por tipo"""
        return []
    
    async def get_recent(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Obtém eventos recentes"""
        return []


class RepositoryManager:
    """
    Gerenciador de repositórios
    """
    
    def __init__(self):
        self._repositories: Dict[str, BaseRepository] = {}
    
    def register(self, name: str, repository: BaseRepository):
        """Registra repositório"""
        self._repositories[name] = repository
        logger.debug(f"Repositório registrado: {name}")
    
    def get(self, name: str) -> Optional[BaseRepository]:
        """Obtém repositório"""
        return self._repositories.get(name)
    
    def get_all(self) -> Dict[str, BaseRepository]:
        """Retorna todos os repositórios"""
        return self._repositories.copy()


# Instância global
_repo_manager: Optional[RepositoryManager] = None


def get_repository_manager() -> RepositoryManager:
    """Retorna gerenciador global de repositórios"""
    global _repo_manager
    if _repo_manager is None:
        _repo_manager = RepositoryManager()
    return _repo_manager
