# -*- coding: utf-8 -*-
"""
AI Providers - Strategy Pattern
Implementações de diferentes provedores de IA

Autor: JARVIS Team
Versão: 4.0.0
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

# Imports opcionais
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import anthropic
    HAS_CLAUDE = True
except ImportError:
    HAS_CLAUDE = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class AIProvider(ABC):
    """Interface base para provedores de IA (Strategy Pattern)"""
    
    @abstractmethod
    def generate(self, system_prompt: str, messages: List[Dict], max_tokens: int = 500) -> Tuple[str, Dict]:
        """Gera resposta"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Verifica disponibilidade"""
        pass


class OpenAIProvider(AIProvider):
    """Provider OpenAI (GPT-4, GPT-3.5)"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self.client = None
        
        if HAS_OPENAI and api_key:
            self.client = openai.OpenAI(api_key=api_key)
            logger.info(f"✅ OpenAI: {model}")
    
    def is_available(self) -> bool:
        return HAS_OPENAI and self.client is not None
    
    def generate(self, system_prompt: str, messages: List[Dict], max_tokens: int = 500) -> Tuple[str, Dict]:
        if not self.is_available():
            return "", {"error": "OpenAI não disponível"}
        
        try:
            api_messages = [{"role": "system", "content": system_prompt}]
            api_messages.extend(messages)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            text = response.choices[0].message.content.strip()
            metadata = {
                "model": self.model,
                "tokens": response.usage.total_tokens if response.usage else 0,
                "provider": "openai"
            }
            
            return text, metadata
            
        except Exception as e:
            logger.error(f"❌ OpenAI: {e}")
            return "", {"error": str(e)}


class ClaudeProvider(AIProvider):
    """Provider Anthropic Claude"""
    
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        self.api_key = api_key
        self.model = model
        self.client = None
        
        if HAS_CLAUDE and api_key:
            self.client = anthropic.Anthropic(api_key=api_key)
            logger.info(f"✅ Claude: {model}")
    
    def is_available(self) -> bool:
        return HAS_CLAUDE and self.client is not None
    
    def generate(self, system_prompt: str, messages: List[Dict], max_tokens: int = 500) -> Tuple[str, Dict]:
        if not self.is_available():
            return "", {"error": "Claude não disponível"}
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages
            )
            
            text = response.content[0].text.strip()
            metadata = {
                "model": self.model,
                "tokens": response.usage.input_tokens + response.usage.output_tokens,
                "provider": "claude"
            }
            
            return text, metadata
            
        except Exception as e:
            logger.error(f"❌ Claude: {e}")
            return "", {"error": str(e)}


class OllamaProvider(AIProvider):
    """Provider Ollama (Local)"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        logger.info(f"✅ Ollama: {model}")
    
    def is_available(self) -> bool:
        if not HAS_REQUESTS:
            return False
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def generate(self, system_prompt: str, messages: List[Dict], max_tokens: int = 500) -> Tuple[str, Dict]:
        if not HAS_REQUESTS:
            return "", {"error": "requests não instalado"}
        
        try:
            prompt = f"System: {system_prompt}\n\n"
            for msg in messages:
                role = "User" if msg["role"] == "user" else "Assistant"
                prompt += f"{role}: {msg['content']}\n"
            prompt += "Assistant:"
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "").strip(), {"model": self.model, "provider": "ollama"}
            
            return "", {"error": f"HTTP {response.status_code}"}
            
        except Exception as e:
            logger.error(f"❌ Ollama: {e}")
            return "", {"error": str(e)}


class ProviderFactory:
    """Factory Pattern: Cria providers dinamicamente"""
    
    @staticmethod
    def create(provider_type: str, config: Dict) -> Optional[AIProvider]:
        providers = {
            "openai": lambda: OpenAIProvider(
                api_key=config.get("api_key", ""),
                model=config.get("model", "gpt-4o-mini")
            ),
            "claude": lambda: ClaudeProvider(
                api_key=config.get("api_key", ""),
                model=config.get("model", "claude-3-haiku-20240307")
            ),
            "ollama": lambda: OllamaProvider(
                base_url=config.get("base_url", "http://localhost:11434"),
                model=config.get("model", "llama2")
            ),
        }
        
        factory = providers.get(provider_type.lower())
        return factory() if factory else None
