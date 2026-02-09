# -*- coding: utf-8 -*-
"""Módulo de Produtividade (sessões de foco e relatórios)."""
import logging
from typing import Dict, Any
from .tracker import ProductivityTracker
from .reports import ProductivityReports

logger = logging.getLogger(__name__)


class ProductivityModule:
    def __init__(self, config):
        self.config = config
        self._running = False
        self.status = '🔴'
        self.tracker = ProductivityTracker()
        self.reports = ProductivityReports(self.tracker)

    async def start(self):
        logger.info("📈 Iniciando módulo de produtividade...")
        self._running = True
        self.status = '🟢'

    async def stop(self):
        if self.tracker.get_current_session():
            self.tracker.end_session()
        self._running = False
        self.status = '🔴'

    async def process(self, message: str, intent, context: Dict, metadata: Dict) -> str:
        msg_lower = message.lower().strip()
        if 'relatório' in msg_lower or 'relatorio' in msg_lower:
            if 'semana' in msg_lower:
                return self.reports.weekly_report()
            return self.reports.daily_report()
        if 'iniciar sessão' in msg_lower or 'iniciar sessao' in msg_lower or 'começar foco' in msg_lower:
            category = 'break' if ('pausa' in msg_lower or 'break' in msg_lower) else 'work'
            self.tracker.start_session(category=category)
            return f"✅ Sessão de **{category}** iniciada."
        if 'encerrar sessão' in msg_lower or 'encerrar sessao' in msg_lower or 'parar foco' in msg_lower:
            record = self.tracker.end_session()
            if record:
                return f"✅ Sessão encerrada. Duração: {record.duration_seconds/60:.0f} min."
            return "Nenhuma sessão ativa no momento."
        if 'sugestões' in msg_lower or 'sugestoes' in msg_lower or 'dicas' in msg_lower:
            return "💡 **Sugestões**\n\n" + "\n".join(f"• {s}" for s in self.reports.get_suggestions())
        if 'status' in msg_lower and 'produtividade' in msg_lower:
            current = self.tracker.get_current_session()
            if current:
                return f"⏱️ Sessão ativa: **{current.category}** desde {current.start.strftime('%H:%M')}."
            return "Nenhuma sessão ativa. Use 'iniciar sessão' para começar."
        return "Comandos: 'relatório do dia', 'relatório da semana', 'iniciar sessão', 'encerrar sessão', 'sugestões'"
