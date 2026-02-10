# -*- coding: utf-8 -*-
"""
Plugin de exemplo: saudações automáticas
Responde "Bom dia", "Boa tarde", etc. sem passar pelo fluxo principal.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from core.plugin_manager import Plugin


class AutoGreetingsPlugin(Plugin):
    """Responde a saudações com base no horário."""

    async def on_message_received(self, message: str, context: Dict[str, Any]) -> Optional[str]:
        msg_lower = (message or "").strip().lower()
        if not msg_lower:
            return None
        hour = datetime.now().hour
        if msg_lower in ("bom dia", "boa tarde", "boa noite", "oi", "olá", "e aí"):
            if 6 <= hour < 12:
                return "Bom dia! Como posso ajudar?"
            if 12 <= hour < 18:
                return "Boa tarde! Em que posso ajudar?"
            return "Boa noite! Em que posso ajudar?"
        return None
