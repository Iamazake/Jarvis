# -*- coding: utf-8 -*-
"""
Pattern Extractor - Extrator de Padrões
Extrai padrões de interações para melhorar respostas

Autor: JARVIS Team
Versão: 3.1.0
"""

from typing import Dict, Any, List, Optional
from collections import defaultdict, Counter
from datetime import datetime, timedelta

from core.logger import get_logger

logger = get_logger(__name__)


class PatternExtractor:
    """
    Extrai padrões de interações
    
    Padrões identificados:
    - Horários preferidos
    - Tipos de comandos mais comuns
    - Preferências de resposta
    - Padrões de uso
    """
    
    def __init__(self):
        self._interactions: List[Dict[str, Any]] = []
        self._patterns: Dict[str, Any] = {}
    
    def add_interaction(
        self,
        message: str,
        intent: str,
        response_time: float,
        rating: Optional[float] = None
    ):
        """Adiciona interação para análise"""
        interaction = {
            'message': message,
            'intent': intent,
            'response_time': response_time,
            'rating': rating,
            'timestamp': datetime.now(),
            'hour': datetime.now().hour,
            'day_of_week': datetime.now().weekday()
        }
        
        self._interactions.append(interaction)
        
        # Mantém apenas últimas 1000 interações
        if len(self._interactions) > 1000:
            self._interactions.pop(0)
    
    def extract_patterns(self) -> Dict[str, Any]:
        """
        Extrai padrões das interações
        
        Returns:
            Dicionário com padrões identificados
        """
        if not self._interactions:
            return {}
        
        patterns = {
            'preferred_hours': self._extract_preferred_hours(),
            'common_intents': self._extract_common_intents(),
            'response_preferences': self._extract_response_preferences(),
            'usage_patterns': self._extract_usage_patterns()
        }
        
        self._patterns = patterns
        logger.info("Padrões extraídos das interações")
        return patterns
    
    def _extract_preferred_hours(self) -> List[int]:
        """Extrai horários preferidos de uso"""
        hour_counts = Counter(i['hour'] for i in self._interactions)
        
        # Retorna top 3 horários
        top_hours = [hour for hour, _ in hour_counts.most_common(3)]
        return sorted(top_hours)
    
    def _extract_common_intents(self) -> List[Dict[str, Any]]:
        """Extrai intenções mais comuns"""
        intent_counts = Counter(i['intent'] for i in self._interactions)
        
        total = len(self._interactions)
        common = []
        
        for intent, count in intent_counts.most_common(5):
            common.append({
                'intent': intent,
                'count': count,
                'percentage': (count / total) * 100
            })
        
        return common
    
    def _extract_response_preferences(self) -> Dict[str, Any]:
        """Extrai preferências de resposta"""
        # Analisa ratings
        ratings = [i['rating'] for i in self._interactions if i['rating'] is not None]
        
        if not ratings:
            return {}
        
        avg_rating = sum(ratings) / len(ratings)
        
        # Analisa tempo de resposta
        response_times = [i['response_time'] for i in self._interactions]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            'average_rating': avg_rating,
            'average_response_time': avg_response_time,
            'prefers_fast_responses': avg_response_time < 2.0
        }
    
    def _extract_usage_patterns(self) -> Dict[str, Any]:
        """Extrai padrões de uso"""
        # Análise por dia da semana
        day_counts = Counter(i['day_of_week'] for i in self._interactions)
        
        # Análise de frequência
        recent_interactions = [
            i for i in self._interactions
            if (datetime.now() - i['timestamp']).days <= 7
        ]
        
        return {
            'most_active_day': day_counts.most_common(1)[0][0] if day_counts else None,
            'interactions_last_week': len(recent_interactions),
            'daily_average': len(recent_interactions) / 7 if recent_interactions else 0
        }
    
    def get_suggestions(self) -> List[str]:
        """
        Gera sugestões baseadas em padrões
        
        Returns:
            Lista de sugestões
        """
        suggestions = []
        
        if not self._patterns:
            self.extract_patterns()
        
        patterns = self._patterns
        
        # Sugestão baseada em horários
        preferred_hours = patterns.get('preferred_hours', [])
        if preferred_hours:
            suggestions.append(
                f"Você costuma usar o JARVIS mais entre {preferred_hours[0]}h e {preferred_hours[-1]}h"
            )
        
        # Sugestão baseada em intenções
        common_intents = patterns.get('common_intents', [])
        if common_intents:
            top_intent = common_intents[0]['intent']
            suggestions.append(
                f"Seu tipo de comando mais comum é: {top_intent}"
            )
        
        return suggestions
