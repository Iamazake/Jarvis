# -*- coding: utf-8 -*-
"""
Context Manager - Gerenciador de Contexto
Mantém histórico e contexto da conversa

Autor: JARVIS Team
Versão: 3.0.0
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import deque
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Representa uma mensagem no histórico"""
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = 'cli'  # 'cli', 'voice', 'whatsapp'
    metadata: Dict = field(default_factory=dict)


class ContextManager:
    """
    Gerencia o contexto da conversa
    
    Funcionalidades:
    - Histórico de mensagens (últimas N)
    - Contexto de curto prazo (sessão)
    - Referências a entidades mencionadas
    - Estado de fluxos em andamento
    """
    
    def __init__(self, max_history: int = 20, context_ttl_minutes: int = 30):
        self.max_history = max_history
        self.context_ttl = timedelta(minutes=context_ttl_minutes)
        
        # Histórico de mensagens (FIFO)
        self.messages: deque = deque(maxlen=max_history)
        
        # Contexto da sessão atual
        self._session_context: Dict[str, Any] = {}
        
        # Entidades mencionadas (nomes, lugares, etc)
        self._entities: Dict[str, Any] = {}
        
        # Última intenção detectada
        self._last_intent: Optional[str] = None
        
        # Último contato mencionado (para "monitore a conversa dele", "responde pra ele")
        self._last_contact: Optional[str] = None
        self._last_contact_at: Optional[datetime] = None

        # Contatos que o usuário pediu para monitorar nesta sessão ("resuma do contato que pedi pra monitorar")
        self._monitored_contacts: List[str] = []

        # Cache de últimas mensagens recebidas por contato
        # {"nome_ou_jid": {"text": "...", "timestamp": datetime, "from_me": False}}
        self._last_message_by_contact: Dict[str, Dict[str, Any]] = {}

        # Flag: narrar ações enquanto executa (estilo Stark)
        self._explain_actions: bool = True
        
        # Plano de execução pendente (confirmação única: "Posso prosseguir?" → sim executa)
        self._pending_plan: Optional[Any] = None

        # Fluxos em andamento
        self._active_flows: Dict[str, Dict] = {}
        
        # Timestamp da última interação
        self._last_interaction: datetime = datetime.now()
    
    def add_message(self, role: str, content: str, source: str = 'cli', 
                    metadata: Dict = None):
        """Adiciona mensagem ao histórico"""
        msg = Message(
            role=role,
            content=content,
            source=source,
            metadata=metadata or {}
        )
        self.messages.append(msg)
        self._last_interaction = datetime.now()
        
        # Limpa contexto se passou muito tempo
        self._check_context_expiry()
    
    def get_context(self) -> Dict:
        """Retorna contexto completo para processamento"""
        return {
            'history': self.get_history_for_ai(),
            'last_intent': self._last_intent,
            'last_contact': self._last_contact,
            'monitored_contacts': list(self._monitored_contacts),
            'last_monitored_contact': self.get_last_monitored_contact(),
            'entities': self._entities.copy(),
            'session': self._session_context.copy(),
            'active_flows': list(self._active_flows.keys()),
            'message_count': len(self.messages),
            'last_messages': self.get_all_last_messages(),
            'explain_actions': self._explain_actions,
            'pending_plan': self._pending_plan,
        }
    
    def get_history_for_ai(self, max_messages: int = 10) -> List[Dict]:
        """
        Retorna histórico formatado para a IA
        
        Returns:
            Lista de mensagens no formato OpenAI
        """
        history = []
        messages = list(self.messages)[-max_messages:]
        
        for msg in messages:
            history.append({
                'role': msg.role,
                'content': msg.content
            })
        
        return history
    
    def set_last_intent(self, intent: str):
        """Define última intenção detectada"""
        self._last_intent = intent

    def set_last_contact(self, contact: str):
        """Define último contato mencionado (nome ou jid) para referências como 'dele', 'ele'."""
        if contact:
            self._last_contact = contact
            self._last_contact_at = datetime.now()
            logger.debug("last_contact definido: %s", contact)

    def get_last_contact(self) -> Optional[str]:
        """Retorna o último contato mencionado na conversa."""
        return self._last_contact

    def add_monitored_contact(self, name_or_jid: str):
        """Registra contato que o usuário pediu para monitorar (para resolver 'do contato que pedi pra monitorar')."""
        if name_or_jid and name_or_jid not in self._monitored_contacts:
            self._monitored_contacts.append(name_or_jid)
            logger.debug("monitored_contact adicionado: %s", name_or_jid)

    def get_monitored_contacts(self) -> List[str]:
        """Retorna lista de contatos que o usuário pediu para monitorar nesta sessão."""
        return list(self._monitored_contacts)

    def get_last_monitored_contact(self) -> Optional[str]:
        """Retorna o último contato adicionado ao monitoramento (ou o único, se houver só um)."""
        if not self._monitored_contacts:
            return None
        return self._monitored_contacts[-1]

    # ── Plano de execução (confirmação única, contato travado) ──

    def set_pending_plan(self, plan: Any):
        """Define plano pendente de confirmação. NUNCA reclassificar intenção enquanto houver plano."""
        self._pending_plan = plan
        logger.debug("pending_plan definido: %s", getattr(plan, "plan_id", plan))

    def get_pending_plan(self) -> Optional[Any]:
        """Retorna o plano pendente (ExecutionPlan ou None)."""
        return self._pending_plan

    def clear_pending_plan(self):
        """Limpa plano pendente após execução ou cancelamento."""
        self._pending_plan = None
        logger.debug("pending_plan limpo")
    
    # ── Cache de últimas mensagens por contato ──

    def update_last_message(self, contact: str, text: str, from_me: bool = False):
        """Atualiza cache da última mensagem de/para um contato."""
        self._last_message_by_contact[contact.lower()] = {
            'text': text,
            'timestamp': datetime.now(),
            'from_me': from_me,
        }
        logger.debug("last_message atualizado para %s: %s...", contact, text[:40])

    def get_last_message(self, contact: str) -> Optional[Dict[str, Any]]:
        """Retorna última mensagem de um contato (ou None)."""
        return self._last_message_by_contact.get(contact.lower())

    def get_all_last_messages(self) -> Dict[str, Dict[str, Any]]:
        """Retorna dict completo de últimas mensagens."""
        return dict(self._last_message_by_contact)

    # ── Explain Actions (narração Stark) ──

    @property
    def explain_actions(self) -> bool:
        return self._explain_actions

    @explain_actions.setter
    def explain_actions(self, value: bool):
        self._explain_actions = value

    def add_entity(self, entity_type: str, value: Any, confidence: float = 1.0):
        """
        Adiciona entidade ao contexto
        
        Args:
            entity_type: Tipo (contact, location, date, etc)
            value: Valor da entidade
            confidence: Confiança (0-1)
        """
        self._entities[entity_type] = {
            'value': value,
            'confidence': confidence,
            'timestamp': datetime.now()
        }
    
    def get_entity(self, entity_type: str) -> Optional[Any]:
        """Obtém valor de uma entidade"""
        entity = self._entities.get(entity_type)
        if entity:
            return entity['value']
        return None
    
    def start_flow(self, flow_name: str, data: Dict = None):
        """
        Inicia um fluxo de conversa
        
        Flows são usados para diálogos multi-turno
        Ex: "Enviar mensagem" -> "Para quem?" -> "Qual mensagem?"
        """
        self._active_flows[flow_name] = {
            'started': datetime.now(),
            'step': 0,
            'data': data or {}
        }
        logger.debug(f"Flow iniciado: {flow_name}")
    
    def update_flow(self, flow_name: str, step: int = None, data: Dict = None):
        """Atualiza um fluxo ativo"""
        if flow_name in self._active_flows:
            if step is not None:
                self._active_flows[flow_name]['step'] = step
            if data:
                self._active_flows[flow_name]['data'].update(data)
    
    def end_flow(self, flow_name: str) -> Optional[Dict]:
        """Finaliza um fluxo e retorna seus dados"""
        return self._active_flows.pop(flow_name, None)
    
    def get_flow(self, flow_name: str) -> Optional[Dict]:
        """Obtém dados de um fluxo ativo"""
        return self._active_flows.get(flow_name)
    
    def set_session(self, key: str, value: Any):
        """Define valor no contexto da sessão"""
        self._session_context[key] = value
    
    def get_session(self, key: str, default: Any = None) -> Any:
        """Obtém valor do contexto da sessão"""
        return self._session_context.get(key, default)
    
    def _check_context_expiry(self):
        """Verifica se o contexto expirou e limpa se necessário"""
        now = datetime.now()
        
        # Se passou muito tempo, limpa contexto temporário
        if now - self._last_interaction > self.context_ttl:
            self._entities.clear()
            self._active_flows.clear()
            self._last_intent = None
            self._last_contact = None
            self._last_contact_at = None
            self._monitored_contacts.clear()
            self._pending_plan = None
            # NÃO limpa _last_message_by_contact — ele sobrevive a sessão
            logger.debug("Contexto expirado, limpo")
    
    def clear(self):
        """Limpa todo o contexto"""
        self.messages.clear()
        self._session_context.clear()
        self._entities.clear()
        self._active_flows.clear()
        self._last_intent = None
        self._last_contact = None
        self._last_contact_at = None
        self._monitored_contacts.clear()
        self._pending_plan = None
        self._last_message_by_contact.clear()
    
    def get_summary(self) -> str:
        """Retorna resumo do contexto atual"""
        return (
            f"Mensagens: {len(self.messages)} | "
            f"Entidades: {len(self._entities)} | "
            f"Flows ativos: {len(self._active_flows)}"
        )
