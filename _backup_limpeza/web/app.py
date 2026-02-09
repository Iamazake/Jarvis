# -*- coding: utf-8 -*-
"""
Web Dashboard - Aplicação FastAPI
Status, histórico e configurações do JARVIS

Autor: JARVIS Team
Versão: 3.1.0
"""

import sys
from pathlib import Path

# Garante que o pacote jarvis está no path
JARVIS_ROOT = Path(__file__).parent.parent
if str(JARVIS_ROOT) not in sys.path:
    sys.path.insert(0, str(JARVIS_ROOT))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
try:
    from fastapi.templating import Jinja2Templates
except ImportError:
    from starlette.templating import Jinja2Templates

app = FastAPI(title="JARVIS Dashboard", version="3.1.0")

WEB_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))

# Referência opcional à instância do JARVIS (injetada ao iniciar com jarvis)
_jarvis_ref = None


def set_jarvis(jarvis):
    """Define a instância do JARVIS para o dashboard."""
    global _jarvis_ref
    _jarvis_ref = jarvis


def get_status():
    """Obtém status do JARVIS ou dados padrão."""
    if _jarvis_ref is not None:
        return _jarvis_ref.status
    return {
        "name": "JARVIS",
        "running": False,
        "uptime": "Não iniciado",
        "modules": {},
        "context_size": 0,
        "version": "3.1.0",
    }


def get_context_messages():
    """Obtém últimas mensagens do contexto."""
    if _jarvis_ref is not None and hasattr(_jarvis_ref, "context"):
        messages = list(_jarvis_ref.context.messages)[-20:]
        return [
            {"role": m.role, "content": m.content[:200], "source": getattr(m, "source", "")}
            for m in messages
        ]
    return []


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Página principal do dashboard."""
    status = get_status()
    messages = get_context_messages()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "status": status, "messages": messages},
    )


@app.get("/api/status")
async def api_status():
    """API: status do JARVIS."""
    return get_status()


@app.get("/api/history")
async def api_history():
    """API: histórico de mensagens."""
    return {"messages": get_context_messages()}


def run_dashboard(host: str = "127.0.0.1", port: int = 5050, jarvis=None):
    """Sobe o servidor do dashboard."""
    import uvicorn
    if jarvis is not None:
        set_jarvis(jarvis)
    uvicorn.run(app, host=host, port=port)
