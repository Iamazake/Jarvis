# -*- coding: utf-8 -*-
"""
Plugin Manager - Sistema de plugins para interceptar mensagens
Plugins podem tratar mensagens antes do fluxo principal (ex.: saudações automáticas).

Autor: JARVIS Team
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class Plugin(ABC):
    """Interface base para um plugin."""

    @abstractmethod
    async def on_message_received(self, message: str, context: Dict[str, Any]) -> Optional[str]:
        """
        Chamado quando uma mensagem é recebida.
        Retorna uma string (resposta) se o plugin quiser interceptar; None para deixar o fluxo normal.
        """
        pass


class PluginManager:
    """Gerencia plugins e processa mensagens na ordem de registro."""

    def __init__(self) -> None:
        self.plugins: List[Plugin] = []

    def register(self, plugin: Plugin) -> None:
        """Registra um plugin."""
        if plugin not in self.plugins:
            self.plugins.append(plugin)
            logger.debug("Plugin registrado: %s", type(plugin).__name__)

    def unregister(self, plugin: Plugin) -> None:
        """Remove um plugin."""
        if plugin in self.plugins:
            self.plugins.remove(plugin)

    async def process(self, message: str, context: Dict[str, Any]) -> Optional[str]:
        """
        Passa a mensagem por todos os plugins em ordem.
        Retorna a primeira resposta não vazia; None se nenhum plugin interceptar.
        """
        for plugin in self.plugins:
            try:
                response = await plugin.on_message_received(message, context)
                if response and response.strip():
                    return response.strip()
            except Exception as e:
                logger.warning("Plugin %s falhou: %s", type(plugin).__name__, e)
        return None
