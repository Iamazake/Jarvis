# -*- coding: utf-8 -*-
"""
Execution Plan - Plano de execução (objetivo → confirmação → execução)
Evita loop de confirmação e fixa o contato alvo.

Autor: JARVIS Team
"""

import uuid
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExecutionPlan:
    """
    Plano de execução com contato travado.
    status: draft | awaiting_confirmation | executed | cancelled
    """
    plan_id: str = field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:8]}")
    target_contact: str = ""  # Nome/JID travado (ex.: "Douglas Moretti")
    steps: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "draft"  # draft | awaiting_confirmation | executed | cancelled
    summary: str = ""  # Texto mostrado ao usuário
    composed_message: Optional[str] = None  # Preenchido ao executar step compose
    # Tom/conteúdo (não usados para extrair contato)
    tone: str = ""  # romantic | professional | informal | formal
    relationship: str = ""  # girlfriend | boyfriend | friend | colleague | etc.
    formality: str = ""  # informal | formal

    def to_dict(self) -> Dict[str, Any]:
        """Serialização para incluir no contexto (dict)."""
        return {
            "plan_id": self.plan_id,
            "target_contact": self.target_contact,
            "steps": list(self.steps),
            "status": self.status,
            "summary": self.summary,
            "composed_message": self.composed_message,
            "tone": self.tone,
            "relationship": self.relationship,
            "formality": self.formality,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionPlan":
        """Restaura a partir do contexto."""
        return cls(
            plan_id=data.get("plan_id", ""),
            target_contact=data.get("target_contact", ""),
            steps=list(data.get("steps", [])),
            status=data.get("status", "draft"),
            summary=data.get("summary", ""),
            composed_message=data.get("composed_message"),
            tone=data.get("tone", ""),
            relationship=data.get("relationship", ""),
            formality=data.get("formality", ""),
        )
