# -*- coding: utf-8 -*-
"""
Config - Gerenciador de Configurações Aprimorado
Carrega e valida configurações de .env e config.json

Autor: JARVIS Team
Versão: 3.1.0
"""

import os
import json
from pathlib import Path
from typing import Any, Optional, Dict
from dotenv import load_dotenv

try:
    from pydantic import BaseModel, Field, validator
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

from .logger import get_logger
from .exceptions import ConfigurationException

logger = get_logger(__name__)


if PYDANTIC_AVAILABLE:
    class ConfigSchema(BaseModel):
        """Schema de validação para configurações"""
        JARVIS_NAME: str = Field(default="Jarvis")
        JARVIS_WAKE_WORD: str = Field(default="jarvis")
        JARVIS_LANGUAGE: str = Field(default="pt-BR")
        JARVIS_VOICE_SPEED: int = Field(default=180, ge=50, le=300)
        JARVIS_LOG_LEVEL: str = Field(default="INFO")
        
        OPENAI_API_KEY: Optional[str] = None
        OPENAI_MODEL: str = Field(default="gpt-4o-mini")
        ANTHROPIC_API_KEY: Optional[str] = None
        ANTHROPIC_MODEL: str = Field(default="claude-3-haiku-20240307")
        AI_PROVIDER: str = Field(default="openai")
        
        DATABASE_TYPE: str = Field(default="sqlite")
        MYSQL_HOST: str = Field(default="127.0.0.1")
        MYSQL_PORT: int = Field(default=3306, ge=1, le=65535)
        MYSQL_DATABASE: str = Field(default="jarvis_db")
        MYSQL_USER: str = Field(default="root")
        MYSQL_PASSWORD: Optional[str] = None
        
        @validator('JARVIS_LOG_LEVEL')
        def validate_log_level(cls, v):
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if v.upper() not in valid_levels:
                raise ValueError(f'Log level deve ser um de: {", ".join(valid_levels)}')
            return v.upper()
        
        @validator('AI_PROVIDER')
        def validate_ai_provider(cls, v):
            valid_providers = ['openai', 'anthropic', 'ollama']
            if v.lower() not in valid_providers:
                raise ValueError(f'AI provider deve ser um de: {", ".join(valid_providers)}')
            return v.lower()


class Config:
    """
    Gerenciador de configurações centralizado e validado
    
    Carrega de:
    1. Variáveis de ambiente
    2. Arquivo .env
    3. config.json
    
    Valida configurações usando Pydantic (se disponível)
    """
    
    def __init__(self, config_path: Optional[str] = None, validate: bool = True):
        self._config: dict = {}
        self._env_loaded = False
        self._validate = validate and PYDANTIC_AVAILABLE
        
        # Diretório base do projeto
        self.base_dir = Path(__file__).parent.parent
        
        # Carrega configurações
        self._load_env()
        self._load_json_config(config_path)
        
        # Valida se solicitado e Pydantic disponível
        if self._validate:
            self._validate_config()
    
    def _load_env(self):
        """Carrega variáveis do .env"""
        env_path = self.base_dir / '.env'
        
        if env_path.exists():
            load_dotenv(env_path)
            self._env_loaded = True
            logger.debug(f"✅ .env carregado de {env_path}")
        else:
            logger.warning(f"⚠️ Arquivo .env não encontrado em {env_path}")
    
    def _load_json_config(self, config_path: Optional[str] = None):
        """Carrega config.json"""
        if config_path:
            json_path = Path(config_path)
        else:
            json_path = self.base_dir / 'config.json'
        
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self._config.update(loaded_config)
                logger.debug(f"✅ config.json carregado")
            except Exception as e:
                logger.error(f"❌ Erro ao carregar config.json: {e}")
    
    def _validate_config(self):
        """Valida configurações usando schema"""
        if not PYDANTIC_AVAILABLE:
            return
        
        try:
            # Cria schema com valores atuais (apenas campos presentes)
            schema_data = {k: v for k, v in self._config.items() if k in ConfigSchema.__fields__}
            schema = ConfigSchema(**schema_data)
            # Atualiza config com valores validados
            self._config.update(schema.dict(exclude_none=True))
            logger.debug("Configurações validadas")
        except Exception as e:
            raise ConfigurationException(
                f"Erro de validação de configuração: {str(e)}",
                details={'error': str(e)}
            )
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtém valor de configuração
        
        Prioridade:
        1. Variável de ambiente
        2. config.json
        3. Valor default
        """
        # Tenta variável de ambiente primeiro
        env_value = os.getenv(key)
        if env_value is not None:
            return self._parse_value(env_value)
        
        # Tenta config.json
        if key in self._config:
            return self._config[key]
        
        # Retorna default
        return default
    
    def _parse_value(self, value: str) -> Any:
        """Converte string para tipo apropriado"""
        # Boolean
        if value.lower() in ('true', 'yes', '1'):
            return True
        if value.lower() in ('false', 'no', '0'):
            return False
        
        # Número
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        return value
    
    def set(self, key: str, value: Any, persist: bool = False):
        """
        Define valor de configuração
        
        Args:
            key: Chave
            value: Valor
            persist: Se True, salva no config.json
        """
        self._config[key] = value
        
        if persist:
            self._save_json_config()
    
    def _save_json_config(self):
        """Salva config.json"""
        json_path = self.base_dir / 'config.json'
        
        try:
            # Valida antes de salvar se Pydantic disponível
            if self._validate and PYDANTIC_AVAILABLE:
                schema_data = {k: v for k, v in self._config.items() if k in ConfigSchema.__fields__}
                ConfigSchema(**schema_data)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.debug("✅ config.json salvo")
        except Exception as e:
            logger.error(f"❌ Erro ao salvar config.json: {e}")
    
    def validate(self) -> bool:
        """
        Valida configurações manualmente
        
        Returns:
            True se válido, False caso contrário
        """
        if not PYDANTIC_AVAILABLE:
            logger.warning("Pydantic não disponível, validação não pode ser realizada")
            return True
        
        try:
            schema_data = {k: v for k, v in self._config.items() if k in ConfigSchema.__fields__}
            ConfigSchema(**schema_data)
            return True
        except Exception as e:
            logger.error(f"Validação falhou: {e}")
            return False
    
    def get_schema(self) -> Optional[Dict[str, Any]]:
        """Retorna schema de configurações (se Pydantic disponível)"""
        if PYDANTIC_AVAILABLE:
            return ConfigSchema.schema()
        return None
    
    def get_all(self) -> dict:
        """Retorna todas as configurações"""
        return self._config.copy()
    
    def __getitem__(self, key: str) -> Any:
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any):
        self.set(key, value)
    
    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None


# Instância global
_config: Optional[Config] = None

def get_config() -> Config:
    """Retorna instância global de configuração"""
    global _config
    if _config is None:
        _config = Config()
    return _config
