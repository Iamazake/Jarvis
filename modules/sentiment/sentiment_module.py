# -*- coding: utf-8 -*-
"""Módulo de Análise de Sentimento."""
from typing import Dict, Any, Optional, List
from collections import deque
from datetime import datetime, timedelta
import logging
from .analyzer import SentimentAnalyzer, SentimentResult, SentimentLabel

logger = logging.getLogger(__name__)


def _config_get(config, key: str, default=None):
    return config.get(key, default) if hasattr(config, 'get') and callable(getattr(config, 'get')) else getattr(config, key, default)


class SentimentModule:
    """Análise de sentimento em tempo real e sugestão de tom."""

    def __init__(self, config):
        self.config = config
        self._running = False
        self.status = '🔴'
        lang = (_config_get(config, 'JARVIS_LANGUAGE') or 'pt')[:2]
        self.analyzer = SentimentAnalyzer(language=lang)
        self._history: deque = deque(maxlen=500)
        self._alert_threshold = float(_config_get(config, 'SENTIMENT_ALERT_THRESHOLD', -0.3))

    async def start(self):
        logger.info("😊 Iniciando módulo de sentimento...")
        self._running = True
        self.status = '🟢'

    async def stop(self):
        self._running = False
        self.status = '🔴'

    def analyze(self, text: str) -> SentimentResult:
        result = self.analyzer.analyze(text)
        self._history.append({'text': text[:200], 'result': result, 'timestamp': datetime.now()})
        return result

    def get_tone_suggestion(self, result: SentimentResult) -> str:
        if result.label == SentimentLabel.NEGATIVE:
            return "empático e focado em resolver o problema"
        if result.label == SentimentLabel.POSITIVE:
            return "amigável e positivo"
        return "neutro e informativo"

    def get_mood_stats(self, hours: int = 24) -> Dict[str, Any]:
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [h for h in self._history if h['timestamp'] >= cutoff]
        if not recent:
            return {'count': 0, 'positive_pct': 0, 'negative_pct': 0, 'neutral_pct': 0, 'average_score': 0.0}
        total = len(recent)
        labels = [h['result'].label for h in recent]
        scores = [h['result'].score for h in recent]
        return {
            'count': total,
            'positive_pct': 100 * sum(1 for l in labels if l == SentimentLabel.POSITIVE) / total,
            'negative_pct': 100 * sum(1 for l in labels if l == SentimentLabel.NEGATIVE) / total,
            'neutral_pct': 100 * sum(1 for l in labels if l == SentimentLabel.NEUTRAL) / total,
            'average_score': sum(scores) / total
        }

    async def process(self, message: str, intent, context: Dict, metadata: Dict) -> str:
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
        if 'analisar' in msg_lower or 'sentimento' in msg_lower or 'sentindo' in msg_lower:
            to_analyze = message.replace('analisar', '').replace('sentimento', '').replace('como estou me sentindo', '').strip()
            if not to_analyze and context.get('history'):
                to_analyze = (context['history'][-1].get('content', '') if isinstance(context['history'][-1], dict) else '') or message
            if not to_analyze:
                to_analyze = message
            result = self.analyze(to_analyze)
            tone = self.get_tone_suggestion(result)
            return (
                f"😊 **Análise de sentimento**\n\n"
                f"• Sentimento: {result.label.value}\n"
                f"• Score: {result.score:.2f}\n"
                f"• Confiança: {result.confidence:.0%}\n"
                f"• Sugestão de tom: {tone}"
            )
        return "Comandos: 'estatísticas de humor', 'analisar sentimento', 'como estou me sentindo'"
