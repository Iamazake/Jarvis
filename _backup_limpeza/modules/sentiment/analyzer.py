# -*- coding: utf-8 -*-
"""
Analyzer - Analisador de Sentimento
Análise de sentimento em texto (pt-BR)

Autor: JARVIS Team
Versão: 3.1.0
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from core.logger import get_logger

logger = get_logger(__name__)


class SentimentLabel(Enum):
    """Rótulos de sentimento"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass
class SentimentResult:
    """Resultado da análise de sentimento"""
    label: SentimentLabel
    score: float  # -1 a 1 (negativo a positivo)
    confidence: float  # 0 a 1
    raw_scores: Dict[str, float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'label': self.label.value,
            'score': self.score,
            'confidence': self.confidence,
            'raw_scores': self.raw_scores or {}
        }


class SentimentAnalyzer:
    """
    Analisador de sentimento
    
    Usa abordagem baseada em léxico/dicionário quando não há
    biblioteca de ML disponível; suporta fallback para textblob/vader.
    """
    
    def __init__(self, language: str = 'pt'):
        self.language = language
        self._vader = None
        self._textblob_available = False
        self._init_analyzers()
    
    def _init_analyzers(self):
        """Inicializa analisadores disponíveis"""
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            self._vader = SentimentIntensityAnalyzer()
            logger.debug("VADER Sentiment disponível")
        except ImportError:
            logger.debug("vaderSentiment não instalado")
        
        try:
            from textblob import TextBlob
            from textblob_fr import PatternTagger, PatternAnalyzer
            self._textblob_available = True
            logger.debug("TextBlob disponível")
        except ImportError:
            try:
                from textblob import TextBlob
                self._textblob_available = True
            except ImportError:
                pass
    
    def analyze(self, text: str) -> SentimentResult:
        """
        Analisa sentimento do texto.
        
        Args:
            text: Texto a analisar
            
        Returns:
            SentimentResult com label, score e confidence
        """
        if not text or not text.strip():
            return SentimentResult(
                label=SentimentLabel.NEUTRAL,
                score=0.0,
                confidence=0.0
            )
        
        text = text.strip()
        
        # Tenta VADER primeiro (funciona bem com inglês, razoável em pt)
        if self._vader:
            try:
                scores = self._vader.polarity_scores(text)
                compound = scores['compound']
                
                if compound >= 0.05:
                    label = SentimentLabel.POSITIVE
                elif compound <= -0.05:
                    label = SentimentLabel.NEGATIVE
                else:
                    label = SentimentLabel.NEUTRAL
                
                confidence = abs(compound)
                return SentimentResult(
                    label=label,
                    score=compound,
                    confidence=min(1.0, confidence * 2),
                    raw_scores=scores
                )
            except Exception as e:
                logger.debug(f"VADER falhou: {e}")
        
        # Fallback: análise simples por palavras em português
        return self._simple_analyzer(text)
    
    def _simple_analyzer(self, text: str) -> SentimentResult:
        """Analisador simples baseado em palavras-chave (pt-BR)"""
        text_lower = text.lower()
        
        positive_words = [
            'bom', 'ótimo', 'excelente', 'maravilhoso', 'feliz', 'alegre',
            'obrigado', 'obrigada', 'valeu', 'legal', 'show', 'perfeito',
            'adoro', 'amo', 'gosto', 'sucesso', 'ótima', 'bem', 'sim'
        ]
        
        negative_words = [
            'ruim', 'péssimo', 'horrível', 'triste', 'raiva', 'ódio',
            'problema', 'erro', 'falha', 'não', 'nunca', 'mal', 'pior',
            'detesto', 'odeio', 'insucesso', 'decepcionado', 'bravo'
        ]
        
        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)
        
        total = pos_count + neg_count
        if total == 0:
            return SentimentResult(
                label=SentimentLabel.NEUTRAL,
                score=0.0,
                confidence=0.3
            )
        
        score = (pos_count - neg_count) / max(total, 1)
        score = max(-1.0, min(1.0, score))
        
        if score > 0.1:
            label = SentimentLabel.POSITIVE
        elif score < -0.1:
            label = SentimentLabel.NEGATIVE
        else:
            label = SentimentLabel.NEUTRAL
        
        confidence = min(0.8, 0.3 + abs(score) * 0.5)
        
        return SentimentResult(
            label=label,
            score=score,
            confidence=confidence,
            raw_scores={'positive_count': pos_count, 'negative_count': neg_count}
        )
    
    def is_negative_alert(self, result: SentimentResult, threshold: float = -0.3) -> bool:
        """Indica se o sentimento é negativo o suficiente para alerta"""
        return result.label == SentimentLabel.NEGATIVE and result.score <= threshold
