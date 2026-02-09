# -*- coding: utf-8 -*-
"""Relatórios e sugestões de produtividade."""
from typing import Dict, Any, List


class ProductivityReports:
    def __init__(self, tracker):
        self.tracker = tracker

    def daily_report(self) -> str:
        summary = self.tracker.get_today_summary()
        lines = [f"📊 **Relatório do dia** ({summary['date']})", "", f"• Total: {summary['total_hours']}h", f"• Sessões: {summary['session_count']}", ""]
        if summary['by_category']:
            for cat, sec in summary['by_category'].items():
                lines.append(f"  - {cat}: {sec/3600:.1f}h")
        else:
            lines.append("Nenhuma sessão registrada hoje.")
        return "\n".join(lines)

    def weekly_report(self) -> str:
        summary = self.tracker.get_week_summary()
        lines = ["📊 **Relatório da semana**", "", f"• Total: {summary['total_hours']}h", f"• Sessões: {summary['session_count']}", ""]
        if summary['by_category']:
            for cat, sec in summary['by_category'].items():
                lines.append(f"  - {cat}: {sec/3600:.1f}h")
        if summary.get('by_day'):
            lines.append("")
            for day, sec in sorted(summary['by_day'].items(), reverse=True)[:7]:
                lines.append(f"  - {day}: {sec/3600:.1f}h")
        return "\n".join(lines)

    def get_suggestions(self) -> List[str]:
        suggestions = [
            "Faça pausas curtas a cada 50 min de foco.",
            "Use 'iniciar sessão' ao começar uma tarefa e 'encerrar sessão' ao terminar.",
            "Revise o relatório do dia ao final do expediente."
        ]
        return suggestions
