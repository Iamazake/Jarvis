# -*- coding: utf-8 -*-
"""
Learning Module - Módulo Principal de Aprendizado
Sistema que aprende com interações e melhora respostas

Autor: JARVIS Team
Versão: 3.1.0
"""

from typing import Dict, Any, Optional, List

from core.logger import get_logger
from core.module_factory import BaseModule
from .feedback_processor import FeedbackProcessor, Feedback
from .pattern_extractor import PatternExtractor

logger = get_logger(__name__)


class LearningModule(BaseModule):
    """
    Módulo de Aprendizado
    
    Funcionalidades:
    - Coleta feedback implícito e explícito
    - Extrai padrões de uso
    - Melhora classificação de intenções
    - Sugestões proativas
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.feedback_processor = FeedbackProcessor()
        self.pattern_extractor = PatternExtractor()
        self._learning_enabled = config.get('learning_enabled', True)
    
    async def start(self):
        """Inicializa o módulo"""
        logger.info("🧠 Iniciando módulo de aprendizado...")
        
        self._running = True
        self.status = '🟢'
        logger.info("✅ Módulo de aprendizado pronto")
    
    async def stop(self):
        """Para o módulo"""
        self._running = False
        self.status = '🔴'
        logger.info("Módulo de aprendizado parado")
    
    async def process(
        self,
        message: str,
        intent,
        context: Dict,
        metadata: Dict
    ) -> str:
        """Processa comandos de aprendizado"""
        message_lower = message.lower()
        
        # Estatísticas
        if 'estatísticas' in message_lower or 'padrões' in message_lower:
            return await self._handle_statistics()
        
        # Sugestões
        elif 'sugestões' in message_lower or 'sugestão' in message_lower:
            return await self._handle_suggestions()
        
        else:
            return "Comandos disponíveis: 'estatísticas', 'sugestões'"
    
    async def _handle_statistics(self) -> str:
        """Retorna estatísticas de aprendizado"""
        patterns = self.pattern_extractor.extract_patterns()
        avg_rating = self.feedback_processor.get_average_rating()
        
        response = f"📊 **Estatísticas de Aprendizado**\n\n"
        response += f"⭐ Rating médio: {avg_rating:.2f}\n\n"
        
        common_intents = patterns.get('common_intents', [])
        if common_intents:
            response += "**Intenções mais comuns:**\n"
            for intent_info in common_intents[:3]:
                response += f"• {intent_info['intent']}: {intent_info['percentage']:.1f}%\n"
        
        return response
    
    async def _handle_suggestions(self) -> str:
        """Retorna sugestões"""
        suggestions = self.pattern_extractor.get_suggestions()
        
        if not suggestions:
            return "Ainda não há sugestões disponíveis. Continue usando o JARVIS para gerar padrões."
        
        response = "💡 **Sugestões Baseadas em Padrões**\n\n"
        for i, suggestion in enumerate(suggestions, 1):
            response += f"{i}. {suggestion}\n"
        
        return response
    
    # Métodos públicos
    
    def record_interaction(
        self,
        message: str,
        intent: str,
        response_time: float,
        rating: Optional[float] = None
    ):
        """Registra interação para aprendizado"""
        if not self._learning_enabled:
            return
        
        self.pattern_extractor.add_interaction(message, intent, response_time, rating)
        
        # Registra feedback implícito
        self.feedback_processor.record_implicit_feedback(
            interaction_id=f"interaction_{len(self.pattern_extractor._interactions)}",
            response_time=response_time,
            had_followup=False  # Seria detectado depois
        )
    
    def record_feedback(
        self,
        interaction_id: str,
        rating: float,
        message: Optional[str] = None
    ):
        """Registra feedback explícito"""
        self.feedback_processor.record_explicit_feedback(
            interaction_id=interaction_id,
            rating=rating,
            message=message
        )
    
    def get_patterns(self) -> Dict[str, Any]:
        """Obtém padrões extraídos"""
        return self.pattern_extractor.extract_patterns()
    
    def get_average_rating(self, hours: int = 24) -> float:
        """Obtém rating médio"""
        return self.feedback_processor.get_average_rating(hours)
