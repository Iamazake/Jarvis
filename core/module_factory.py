# -*- coding: utf-8 -*-
"""
Module Factory - Factory Pattern para Módulos
Criação e validação de módulos

Autor: JARVIS Team
Versão: 3.1.0
"""

import importlib
import inspect
from typing import Dict, Any, Optional, Type, Callable
from abc import ABC, abstractmethod

from .exceptions import ModuleException, ConfigurationException
from .logger import get_logger
from .schemas import ModuleConfigSchema

logger = get_logger(__name__)


class BaseModule(ABC):
    """
    Classe base para todos os módulos do JARVIS
    
    Todos os módulos devem herdar desta classe
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa módulo
        
        Args:
            config: Configuração do módulo
        """
        self.config = config
        self._running = False
        self.status = '🔴'
        self.name = self.__class__.__name__
    
    @abstractmethod
    async def start(self):
        """Inicializa o módulo"""
        pass
    
    @abstractmethod
    async def stop(self):
        """Para o módulo"""
        pass
    
    async def process(
        self,
        message: str,
        intent,
        context: Dict,
        metadata: Dict
    ) -> str:
        """
        Processa mensagem (opcional)
        
        Módulos podem implementar este método se processarem mensagens
        """
        raise NotImplementedError("Módulo não implementa process()")
    
    def is_available(self) -> bool:
        """Verifica se módulo está disponível"""
        return self._running
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do módulo"""
        return {
            'name': self.name,
            'status': self.status,
            'running': self._running,
            'available': self.is_available()
        }


class ModuleFactory:
    """
    Factory para criar instâncias de módulos
    
    Funcionalidades:
    - Validação de configuração
    - Carregamento dinâmico de módulos
    - Verificação de dependências
    - Tratamento de erros
    """
    
    def __init__(self):
        self._registered_modules: Dict[str, Dict[str, Any]] = {}
        self._module_cache: Dict[str, BaseModule] = {}
    
    def register_module(
        self,
        name: str,
        module_path: str,
        class_name: str,
        required_config: Optional[Dict[str, Any]] = None,
        dependencies: Optional[list] = None
    ):
        """
        Registra um módulo disponível
        
        Args:
            name: Nome do módulo
            module_path: Caminho do módulo (ex: 'modules.ai')
            class_name: Nome da classe
            required_config: Configurações obrigatórias
            dependencies: Dependências de outros módulos
        """
        self._registered_modules[name] = {
            'module_path': module_path,
            'class_name': class_name,
            'required_config': required_config or {},
            'dependencies': dependencies or []
        }
        logger.debug(f"Módulo registrado: {name}")
    
    async def create_module(
        self,
        name: str,
        config: Dict[str, Any],
        validate: bool = True
    ) -> Optional[BaseModule]:
        """
        Cria instância de módulo
        
        Args:
            name: Nome do módulo
            config: Configuração
            validate: Se deve validar configuração
        
        Returns:
            Instância do módulo ou None se falhar
        
        Raises:
            ModuleException: Se houver erro ao criar módulo
        """
        # Verifica se já está em cache
        cache_key = f"{name}_{id(config)}"
        if cache_key in self._module_cache:
            return self._module_cache[cache_key]
        
        # Verifica se módulo está registrado
        if name not in self._registered_modules:
            raise ModuleException(
                f"Módulo '{name}' não está registrado",
                module=name
            )
        
        module_info = self._registered_modules[name]
        
        try:
            # Valida configuração
            if validate:
                self._validate_config(name, config, module_info['required_config'])
            
            # Importa módulo
            module = importlib.import_module(module_info['module_path'])
            
            # Obtém classe
            module_class = getattr(module, module_info['class_name'])
            
            # Verifica se é subclasse de BaseModule
            if not issubclass(module_class, BaseModule):
                raise ModuleException(
                    f"Classe {module_info['class_name']} não herda de BaseModule",
                    module=name
                )
            
            # Cria instância
            instance = module_class(config)
            
            # Cacheia
            self._module_cache[cache_key] = instance
            
            logger.info(f"Módulo criado: {name}")
            return instance
            
        except ImportError as e:
            raise ModuleException(
                f"Erro ao importar módulo {name}: {str(e)}",
                module=name,
                details={'error': str(e)}
            )
        except AttributeError as e:
            raise ModuleException(
                f"Classe {module_info['class_name']} não encontrada em {module_info['module_path']}",
                module=name,
                details={'error': str(e)}
            )
        except Exception as e:
            raise ModuleException(
                f"Erro ao criar módulo {name}: {str(e)}",
                module=name,
                details={'error': str(e)}
            )
    
    def _validate_config(
        self,
        name: str,
        config: Dict[str, Any],
        required: Dict[str, Any]
    ):
        """
        Valida configuração do módulo
        
        Args:
            name: Nome do módulo
            config: Configuração fornecida
            required: Configurações obrigatórias
        
        Raises:
            ConfigurationException: Se configuração inválida
        """
        missing = []
        
        for key, default in required.items():
            if key not in config and default is None:
                missing.append(key)
        
        if missing:
            raise ConfigurationException(
                f"Configurações obrigatórias faltando para módulo {name}: {', '.join(missing)}",
                details={'missing': missing, 'module': name}
            )
    
    def get_registered_modules(self) -> list:
        """Retorna lista de módulos registrados"""
        return list(self._registered_modules.keys())
    
    def clear_cache(self):
        """Limpa cache de módulos"""
        self._module_cache.clear()
        logger.debug("Cache de módulos limpo")


# Factory global pré-configurado
_factory: Optional[ModuleFactory] = None


def get_module_factory() -> ModuleFactory:
    """Retorna factory global"""
    global _factory
    if _factory is None:
        _factory = ModuleFactory()
        # Registra módulos padrão
        _register_default_modules(_factory)
    return _factory


def _register_default_modules(factory: ModuleFactory):
    """Registra módulos padrão do JARVIS"""
    factory.register_module(
        'ai',
        'modules.ai',
        'AIModule',
        required_config={'OPENAI_API_KEY': None}
    )
    
    factory.register_module(
        'memory',
        'modules.memory',
        'MemoryModule'
    )
    
    factory.register_module(
        'search',
        'modules.search',
        'SearchModule'
    )
    
    factory.register_module(
        'tools',
        'modules.tools',
        'ToolsModule'
    )
    
    factory.register_module(
        'voice',
        'modules.voice',
        'VoiceModule'
    )
    
    logger.info("Módulos padrão registrados")
