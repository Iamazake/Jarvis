# -*- coding: utf-8 -*-
"""
Sentiment Module - Módulo de Análise de Sentimento
Análise de sentimento em tempo real e ajuste de tom

Autor: JARVIS Team
Versão: 3.1.0
"""

from typing import Dict, Any, Optional, List
from collections import deque
from datetime import datetime, timedelta

from core.logger import get_logger
from .analyzer import SentimentAnalyzer, SentimentResult, SentimentLabel

logger = get_logger(__name__)


class SentimentModule:
    """
    Módulo de análise de sentimento.
    
    Funcionalidades:
    - Análise de sentimento em tempo real
    - Alertas para mensagens negativas
    - Estatísticas de humor
    - Sugestão de tom de resposta
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._running = False
        self.status = '🔴'
        self.analyzer = SentimentAnalyzer(
            language=config.get('JARVIS_LANGUAGE', 'pt')[:2]
        )
        self._history: deque = deque(maxlen=500)
        self._alert_threshold = float(config.get('SENTIMENT_ALERT_THRESHOLD', -0.3))
    
    async def start(self):
        """Inicializa o módulo"""
        logger.info("😊 Iniciando módulo de sentimento...")
        self._running = True
        self.status = '🟢'
        logger.info("✅ Módulo de sentimento pronto")
    
    async def stop(self):
        """Para o módulo"""
        self._running = False
        self.status = '🔴'
    
    def analyze(self, text: str) -> SentimentResult:
        """Analisa sentimento de um texto."""
        result = self.analyzer.analyze(text)
        self._history.append({
            'text': text[:200],
            'result': result,
            'timestamp': datetime.now()
        })
        return result
    
    def get_tone_suggestion(self, result: SentimentResult) -> str:
        """
        Sugere tom de resposta com base no sentimento.
        
        Returns:
            Descrição do tom sugerido (ex: "empático e suporte")
        """
        if result.label == SentimentLabel.NEGATIVE:
            return "empático, prestativo e focado em resolver o problema"
        if result.label == SentimentLabel.POSITIVE:
            return "amigável e positivo, mantendo o clima"
        return "neutro e informativo"
    
    def get_mood_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Retorna estatísticas de humor nas últimas horas."""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [h for h in self._history if h['timestamp'] >= cutoff]
        if not recent:
            return {
                'count': 0,
                'positive_pct': 0,
                'negative_pct': 0,
                'neutral_pct': 0,
                'average_score': 0.0
            }
        
        labels = [h['result'].label for h in recent]
        total = len(labels)
        scores = [h['result'].score for h in recent]
        
        return {
            'count': total,
            'positive_pct': 100 * sum(1 for l in labels if l == SentimentLabel.POSITIVE) / total,
            'negative_pct': 100 * sum(1 for l in labels if l == SentimentLabel.NEGATIVE) / total,
            'neutral_pct': 100 * sum(1 for l in labels if l == SentimentLabel.NEUTRAL) / total,
            'average_score': sum(scores) / total
        }
    
    def should_alert_negative(self, text: str) -> bool:
        """Indica se a mensagem é negativa o suficiente para alerta."""
        result = self.analyzer.analyze(text)
        return self.analyzer.is_negative_alert(result, self._alert_threshold)
    
    async def process(
        self,
        message: str,
        intent,
        context: Dict,
        metadata: Dict
    ) -> str:
        """Processa comandos do módulo (estatísticas, analisar texto)."""
        msg_lower = message.lower().strip()
        
        if 'estatísticas' in msg_lower or 'estatisticas' in msg_lower or 'humor' in msg_lower:
            stats = self.get_mood_stats(24)
            return (
                f"😊 **Estatísticas de humor (24h)**\n\n"
                f"• Análises: {stats['count']}\n"
                f"• Positivo: {stats['positive_pct']:.0f}%\n"
                f"• Negativo: {stats['negative_pct']:.0f}%\n"
                f"• Neutro: {stats['neutral_pct']:.0f}%\n"
                f"• Score médio: {stats['average_score']:.2f}"
            )
        
        if 'analisar' in msg_lower or 'sentimento' in msg_lower:
            # Analisa a própria mensagem ou texto após o comando
            to_analyze = message.replace('analisar', '').replace('sentimento', '').strip()
            if not to_analyze:
                to_analyze = context.get('history', [{}])[-1].get('content', '') if context.get('history') else ''
            if not to_analyze:
                return "Envie o texto para analisar, por exemplo: 'analisar sentimento: <texto>'"
            
            result = self.analyze(to_analyze)
            tone = self.get_tone_suggestion(result)
            return (
                f"😊 **Análise de sentimento**\n\n"
                f"• Sentimento: {result.label.value}\n"
                f"• Score: {result.score:.2f}\n"
                f"• Confiança: {result.confidence:.0%}\n"
                f"• Sugestão de tom: {tone}"
            )
        
        return "Comandos: 'estatísticas de humor', 'analisar sentimento: <texto>'"
    
    def is_available(self) -> bool:
        return self._running
