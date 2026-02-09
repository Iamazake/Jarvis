# -*- coding: utf-8 -*-
"""
Analyzer - Analisador de Sentimento (pt-BR)
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SentimentLabel(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass
class SentimentResult:
    label: SentimentLabel
    score: float
    confidence: float
    raw_scores: Dict[str, float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'label': self.label.value,
            'score': self.score,
            'confidence': self.confidence,
            'raw_scores': self.raw_scores or {}
        }


class SentimentAnalyzer:
    """Analisador de sentimento com fallback por léxico pt-BR."""

    def __init__(self, language: str = 'pt'):
        self.language = language
        self._vader = None
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            self._vader = SentimentIntensityAnalyzer()
        except ImportError:
            pass

    def analyze(self, text: str) -> SentimentResult:
        if not text or not text.strip():
            return SentimentResult(label=SentimentLabel.NEUTRAL, score=0.0, confidence=0.0)
        text = text.strip()
        if self._vader:
            try:
                scores = self._vader.polarity_scores(text)
                compound = scores['compound']
                label = SentimentLabel.POSITIVE if compound >= 0.05 else (SentimentLabel.NEGATIVE if compound <= -0.05 else SentimentLabel.NEUTRAL)
                return SentimentResult(label=label, score=compound, confidence=min(1.0, abs(compound) * 2), raw_scores=scores)
            except Exception:
                pass
        return self._simple_analyzer(text)

    def _simple_analyzer(self, text: str) -> SentimentResult:
        text_lower = text.lower()
        positive_words = ['bom', 'ótimo', 'excelente', 'feliz', 'obrigado', 'legal', 'perfeito', 'bem', 'sim']
        negative_words = ['ruim', 'péssimo', 'triste', 'problema', 'erro', 'não', 'mal', 'detesto']
        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)
        total = pos_count + neg_count
        if total == 0:
            return SentimentResult(label=SentimentLabel.NEUTRAL, score=0.0, confidence=0.3)
        score = max(-1.0, min(1.0, (pos_count - neg_count) / max(total, 1)))
        label = SentimentLabel.POSITIVE if score > 0.1 else (SentimentLabel.NEGATIVE if score < -0.1 else SentimentLabel.NEUTRAL)
        return SentimentResult(label=label, score=score, confidence=min(0.8, 0.3 + abs(score) * 0.5), raw_scores={})

    def is_negative_alert(self, result: SentimentResult, threshold: float = -0.3) -> bool:
        return result.label == SentimentLabel.NEGATIVE and result.score <= threshold
