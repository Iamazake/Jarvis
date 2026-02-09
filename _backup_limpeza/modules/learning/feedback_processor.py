# -*- coding: utf-8 -*-
"""
Feedback Processor - Processador de Feedback
Coleta e processa feedback implícito e explícito

Autor: JARVIS Team
Versão: 3.1.0
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Feedback:
    """Representa um feedback"""
    id: str
    type: str  # 'implicit', 'explicit', 'correction'
    interaction_id: Optional[str] = None
    rating: Optional[float] = None  # 0-1
    message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class FeedbackProcessor:
    """
    Processador de feedback
    
    Coleta feedback de:
    - Tempo de resposta
    - Follow-up questions
    - Correções explícitas
    - Avaliações
    """
    
    def __init__(self):
        self._feedback: List[Feedback] = []
        self._next_id = 1
    
    def record_implicit_feedback(
        self,
        interaction_id: str,
        response_time: float,
        had_followup: bool = False,
        metadata: Dict[str, Any] = None
    ) -> Feedback:
        """
        Registra feedback implícito
        
        Args:
            interaction_id: ID da interação
            response_time: Tempo de resposta em segundos
            had_followup: Se houve follow-up
            metadata: Metadados adicionais
        """
        # Calcula rating baseado em tempo e follow-up
        # Tempo rápido + sem follow-up = bom (rating alto)
        rating = 1.0
        
        if response_time > 5.0:  # Muito lento
            rating -= 0.3
        elif response_time > 2.0:  # Lento
            rating -= 0.1
        
        if had_followup:  # Follow-up pode indicar resposta incompleta
            rating -= 0.2
        
        rating = max(0.0, min(1.0, rating))
        
        feedback = Feedback(
            id=f"feedback_{self._next_id}",
            type='implicit',
            interaction_id=interaction_id,
            rating=rating,
            metadata={
                'response_time': response_time,
                'had_followup': had_followup,
                **(metadata or {})
            }
        )
        
        self._next_id += 1
        self._feedback.append(feedback)
        
        logger.debug(f"Feedback implícito registrado: rating={rating:.2f}")
        return feedback
    
    def record_explicit_feedback(
        self,
        interaction_id: str,
        rating: float,
        message: Optional[str] = None
    ) -> Feedback:
        """
        Registra feedback explícito
        
        Args:
            interaction_id: ID da interação
            rating: Avaliação (0-1)
            message: Mensagem opcional
        """
        feedback = Feedback(
            id=f"feedback_{self._next_id}",
            type='explicit',
            interaction_id=interaction_id,
            rating=rating,
            message=message
        )
        
        self._next_id += 1
        self._feedback.append(feedback)
        
        logger.info(f"Feedback explícito registrado: rating={rating:.2f}")
        return feedback
    
    def record_correction(
        self,
        interaction_id: str,
        original_response: str,
        corrected_response: str,
        context: Dict[str, Any] = None
    ) -> Feedback:
        """
        Registra correção
        
        Args:
            interaction_id: ID da interação
            original_response: Resposta original
            corrected_response: Resposta corrigida
            context: Contexto adicional
        """
        feedback = Feedback(
            id=f"feedback_{self._next_id}",
            type='correction',
            interaction_id=interaction_id,
            rating=0.0,  # Correção = rating baixo
            message=f"Correção: {original_response} -> {corrected_response}",
            metadata={
                'original': original_response,
                'corrected': corrected_response,
                **(context or {})
            }
        )
        
        self._next_id += 1
        self._feedback.append(feedback)
        
        logger.info(f"Correção registrada para interação {interaction_id}")
        return feedback
    
    def get_average_rating(self, hours: int = 24) -> float:
        """Obtém rating médio das últimas horas"""
        cutoff = datetime.now().timestamp() - (hours * 3600)
        
        recent_feedback = [
            f for f in self._feedback
            if f.timestamp.timestamp() > cutoff and f.rating is not None
        ]
        
        if not recent_feedback:
            return 0.5  # Default neutro
        
        return sum(f.rating for f in recent_feedback) / len(recent_feedback)
    
    def get_feedback_history(self, limit: int = 100) -> List[Feedback]:
        """Obtém histórico de feedback"""
        return self._feedback[-limit:]
