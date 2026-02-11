# -*- coding: utf-8 -*-
"""
Jarvis Actions MCP Server - Orchestrator como skills
Expõe ferramentas que delegam ao Orchestrator + ContextManager (monitor, autopilot, envio).

Autor: JARVIS Team
Versão: 3.0.0
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_servers.base import MCPServer, Tool

logger = logging.getLogger(__name__)


class JarvisActionsServer(MCPServer):
    """
    MCP Server que expõe ações do Orchestrator como ferramentas.
    Recebe instância de Jarvis no construtor para chamar execute_action + apply_out_meta.
    """

    def __init__(self, jarvis=None):
        super().__init__("jarvis-actions", "3.0.0")
        self.jarvis = jarvis

    async def setup_tools(self):
        if not self.jarvis:
            logger.warning("JarvisActionsServer: jarvis não fornecido, nenhuma ferramenta registrada")
            return

        # whatsapp_monitor(contact)
        self.register_tool(
            Tool(
                name="whatsapp_monitor",
                description="Monitora a conversa de um contato no WhatsApp. Use quando o usuário pedir para monitorar alguém.",
                parameters={
                    "contact": {
                        "type": "string",
                        "description": "Nome do contato a monitorar",
                    }
                },
                required=["contact"],
            ),
            self._whatsapp_monitor,
        )

        # whatsapp_autoreply_enable(contact, tone?)
        self.register_tool(
            Tool(
                name="whatsapp_autoreply_enable",
                description="Ativa o autopilot (auto-resposta) para um contato. Use quando o usuário pedir para ativar autopilot, responder automaticamente, etc.",
                parameters={
                    "contact": {
                        "type": "string",
                        "description": "Nome do contato",
                    },
                    "tone": {
                        "type": "string",
                        "description": "Tom da resposta (ex.: fofinho, profissional). Opcional, padrão fofinho.",
                    },
                },
                required=["contact"],
            ),
            self._whatsapp_autoreply_enable,
        )

        # whatsapp_autoreply_disable(contact?)
        self.register_tool(
            Tool(
                name="whatsapp_autoreply_disable",
                description="Desativa o autopilot para um contato. Use quando o usuário disser 'pare de responder', 'desative autopilot', etc. Se não informar contact, usa o contato ativo/monitorado.",
                parameters={
                    "contact": {
                        "type": "string",
                        "description": "Nome do contato (opcional; se vazio, usa o contato ativo ou último monitorado)",
                    }
                },
                required=[],
            ),
            self._whatsapp_autoreply_disable,
        )

        # whatsapp_autopilot_set_tone(contact, tone)
        self.register_tool(
            Tool(
                name="whatsapp_autopilot_set_tone",
                description="Altera o tom do autopilot para um contato (ex.: profissional, fofinho).",
                parameters={
                    "contact": {
                        "type": "string",
                        "description": "Nome do contato",
                    },
                    "tone": {
                        "type": "string",
                        "description": "Novo tom (ex.: profissional, fofinho)",
                    },
                },
                required=["contact", "tone"],
            ),
            self._whatsapp_autopilot_set_tone,
        )

        # whatsapp_autopilot_status()
        self.register_tool(
            Tool(
                name="whatsapp_autopilot_status",
                description="Retorna o status do autopilot (quais contatos estão com auto-resposta ativa).",
                parameters={},
                required=[],
            ),
            self._whatsapp_autopilot_status,
        )

        # whatsapp_monitor_status()
        self.register_tool(
            Tool(
                name="whatsapp_monitor_status",
                description="Retorna o status do monitoramento (qual conversa está sendo monitorada).",
                parameters={},
                required=[],
            ),
            self._whatsapp_monitor_status,
        )

        # whatsapp_monitor_disable(contact?)
        self.register_tool(
            Tool(
                name="whatsapp_monitor_disable",
                description="Cancela o monitoramento de um contato. Use quando o usuário pedir para cancelar/parar de monitorar alguém (não confundir com desativar autopilot).",
                parameters={
                    "contact": {
                        "type": "string",
                        "description": "Nome do contato (opcional; se vazio, usa o último monitorado)",
                    }
                },
                required=[],
            ),
            self._whatsapp_monitor_disable,
        )

        # whatsapp_send(contact, message)
        self.register_tool(
            Tool(
                name="whatsapp_send",
                description="Envia uma mensagem de WhatsApp para um contato. Use para enviar mensagens (sempre por esta ferramenta, com guardrails do Orchestrator).",
                parameters={
                    "contact": {
                        "type": "string",
                        "description": "Nome do contato ou número",
                    },
                    "message": {
                        "type": "string",
                        "description": "Texto da mensagem",
                    },
                },
                required=["contact", "message"],
            ),
            self._whatsapp_send,
        )

        logger.info("Jarvis Actions: %d ferramentas registradas", len(self.tools))

    async def _run_action(
        self,
        intent_type: str,
        entities: Dict[str, Any],
        message: str,
        source: str = "cli",
    ) -> str:
        context = self.jarvis.context.get_context()
        metadata = {}
        response, out_meta = await self.jarvis.orchestrator.execute_action(
            intent_type=intent_type,
            entities=entities,
            message=message,
            context=context,
            source=source,
            metadata=metadata,
        )
        await self.jarvis.apply_out_meta(out_meta or {})
        return response if isinstance(response, str) else str(response)

    async def _whatsapp_monitor(self, contact: str) -> str:
        contact = (contact or "").strip()
        if not contact:
            return "Informe o nome do contato a monitorar."
        return await self._run_action(
            "whatsapp_monitor",
            {"contact": contact},
            f"monitore {contact}",
        )

    async def _whatsapp_autoreply_enable(
        self, contact: str, tone: Optional[str] = None
    ) -> str:
        contact = (contact or "").strip()
        if not contact:
            return "Informe o nome do contato para ativar o autopilot."
        entities = {"contact": contact}
        if tone:
            entities["tone"] = tone.strip()
        return await self._run_action(
            "whatsapp_autoreply_enable",
            entities,
            f"ative autopilot para {contact}" + (f" tom {tone}" if tone else ""),
        )

    async def _whatsapp_autoreply_disable(self, contact: Optional[str] = None) -> str:
        contact = (contact or "").strip()
        if not contact:
            ctx = self.jarvis.context.get_context()
            contact = (
                (ctx.get("active_target_name") or "").strip()
                or (ctx.get("last_monitored_contact") or "").strip()
            )
        if not contact:
            return "Para quem devo desativar o autopilot? (Diga o nome ou ative primeiro o monitoramento para um contato.)"
        return await self._run_action(
            "whatsapp_autoreply_disable",
            {"contact": contact},
            f"desative autopilot para {contact}",
        )

    async def _whatsapp_autopilot_set_tone(self, contact: str, tone: str) -> str:
        contact = (contact or "").strip()
        tone = (tone or "profissional").strip()
        if not contact:
            return "Informe o nome do contato."
        return await self._run_action(
            "whatsapp_autopilot_set_tone",
            {"contact": contact, "tone": tone},
            f"mude o tom do autopilot para {contact} para {tone}",
        )

    async def _whatsapp_autopilot_status(self) -> str:
        return await self._run_action(
            "whatsapp_autopilot_status",
            {},
            "status do autopilot",
        )

    async def _whatsapp_monitor_status(self) -> str:
        return await self._run_action(
            "whatsapp_monitor_status",
            {},
            "status de monitoramento",
        )

    async def _whatsapp_monitor_disable(self, contact: Optional[str] = None) -> str:
        contact = (contact or "").strip()
        if not contact:
            ctx = self.jarvis.context.get_context()
            contact = (
                (ctx.get("last_monitored_contact") or "").strip()
                or (ctx.get("active_target_name") or "").strip()
            )
        if not contact:
            return "Para qual contato cancelar o monitoramento? (Diga o nome ou use após ter monitorado alguém.)"
        return await self._run_action(
            "whatsapp_monitor_disable",
            {"contact": contact},
            f"cancele o monitoramento de {contact}",
        )

    async def _whatsapp_send(self, contact: str, message: str) -> str:
        contact = (contact or "").strip()
        message = (message or "").strip()
        if not contact:
            return "Informe o nome ou número do contato para enviar a mensagem."
        if not message:
            return "Informe o texto da mensagem a enviar."
        return await self._run_action(
            "whatsapp_send",
            {"contact": contact, "message": message},
            f"envie para {contact}: {message}",
        )
