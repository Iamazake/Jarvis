# -*- coding: utf-8 -*-
"""
Health Monitor - Verificação centralizada de serviços
WhatsApp, API, opcionalmente MCP e banco de dados.

Autor: JARVIS Team
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

try:
    import aiohttp
except ImportError:
    aiohttp = None


class HealthMonitor:
    """Verifica saúde dos serviços do JARVIS (WhatsApp, API, etc.)."""

    def __init__(
        self,
        whatsapp_url: str = None,
        api_url: str = None,
        timeout_seconds: float = 2.0,
    ):
        self.whatsapp_url = (whatsapp_url or os.getenv("WHATSAPP_API_URL") or "http://localhost:3001").rstrip("/")
        self.api_url = (api_url or os.getenv("JARVIS_API_URL") or "http://localhost:5000").rstrip("/")
        self.timeout = timeout_seconds

    async def _check_http(self, url: str, path: str = "/health") -> Dict[str, Any]:
        """Faz GET em url+path e retorna status e latency_ms."""
        full_url = f"{url}{path}" if path else url
        if not aiohttp:
            return {"status": "unknown", "error": "aiohttp não instalado"}
        start = asyncio.get_event_loop().time()
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession() as session:
                async with session.get(full_url, timeout=timeout) as resp:
                    latency_ms = round((asyncio.get_event_loop().time() - start) * 1000)
                    if resp.status == 200:
                        return {"status": "ok", "latency_ms": latency_ms}
                    return {"status": "error", "code": resp.status, "latency_ms": latency_ms}
        except asyncio.TimeoutError:
            return {"status": "timeout", "latency_ms": round((asyncio.get_event_loop().time() - start) * 1000)}
        except Exception as e:
            return {"status": "down", "error": str(e)}

    async def _check_whatsapp(self) -> Dict[str, Any]:
        """Verifica serviço WhatsApp (Baileys)."""
        # Tenta /status primeiro (usado pelo serviço Node)
        result = await self._check_http(self.whatsapp_url, "/status")
        if result.get("status") == "ok":
            return result
        result = await self._check_http(self.whatsapp_url, "/health")
        return result

    async def _check_api(self) -> Dict[str, Any]:
        """Verifica API (Fastify/Node que chama Python)."""
        return await self._check_http(self.api_url, "/health")

    async def _check_mcp_servers(self) -> Dict[str, Any]:
        """MCP servers são processos/stdio; não há endpoint HTTP. Retorna info de configuração."""
        return {"status": "ok", "note": "MCP servers are process-based; no HTTP health endpoint"}

    async def _check_database(self) -> Dict[str, Any]:
        """Se houver conexão de BD configurada, pode fazer query trivial. Por ora apenas skip."""
        return {"status": "skip", "note": "No database health check configured"}

    async def check_all_services(self) -> Dict[str, Dict[str, Any]]:
        """Executa todas as verificações e retorna um dicionário por serviço."""
        whatsapp, api, mcp, db = await asyncio.gather(
            self._check_whatsapp(),
            self._check_api(),
            self._check_mcp_servers(),
            self._check_database(),
        )
        return {
            "whatsapp": whatsapp,
            "api": api,
            "mcp_servers": mcp,
            "database": db,
        }
