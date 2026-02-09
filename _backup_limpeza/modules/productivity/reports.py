# -*- coding: utf-8 -*-
"""
Reports - Relatórios de Produtividade
Geração de relatórios e sugestões

Autor: JARVIS Team
Versão: 3.1.0
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta

from core.logger import get_logger

logger = get_logger(__name__)


class ProductivityReports:
    """Geração de relatórios e sugestões de produtividade."""
    
    def __init__(self, tracker):
        self.tracker = tracker
    
    def daily_report(self) -> str:
        """Relatório em texto do dia."""
        summary = self.tracker.get_today_summary()
        
        lines = [
            f"📊 **Relatório do dia** ({summary['date']})",
            "",
            f"• Total: {summary['total_hours']}h",
            f"• Sessões: {summary['session_count']}",
            ""
        ]
        
        if summary['by_category']:
            lines.append("Por categoria:")
            for cat, sec in summary['by_category'].items():
                lines.append(f"  - {cat}: {sec/3600:.1f}h")
        else:
            lines.append("Nenhuma sessão registrada hoje.")
        
        return "\n".join(lines)
    
    def weekly_report(self) -> str:
        """Relatório em texto da semana."""
        summary = self.tracker.get_week_summary()
        
        lines = [
            "📊 **Relatório da semana**",
            "",
            f"• Total: {summary['total_hours']}h",
            f"• Sessões: {summary['session_count']}",
            ""
        ]
        
        if summary['by_category']:
            lines.append("Por categoria:")
            for cat, sec in summary['by_category'].items():
                lines.append(f"  - {cat}: {sec/3600:.1f}h")
        
        if summary['by_day']:
            lines.append("")
            lines.append("Por dia:")
            for day, sec in sorted(summary['by_day'].items(), reverse=True)[:7]:
                lines.append(f"  - {day}: {sec/3600:.1f}h")
        
        return "\n".join(lines)
    
    def get_suggestions(self) -> List[str]:
        """Sugestões de otimização baseadas nos dados."""
        suggestions = []
        today = self.tracker.get_today_summary()
        week = self.tracker.get_week_summary()
        
        if today['total_hours'] > 10:
            suggestions.append("Considerar pausas: mais de 10h registradas hoje.")
        
        if week['session_count'] > 0 and week['total_hours'] / max(1, week['session_count']) < 0.25:
            suggestions.append("Sessões muito curtas. Tente blocos de foco de 25–50 min.")
        
        if not today['by_category'] and datetime.now().hour >= 9:
            suggestions.append("Nenhuma sessão hoje. Que tal registrar um bloco de foco?")
        
        return suggestions or ["Mantenha o ritmo. Use 'iniciar sessão' para registrar foco."]
