# -*- coding: utf-8 -*-
"""
WhatsApp Handlers - Gerenciamento de Mensagens e Perfis
Strategy Pattern: Diferentes estratégias de resposta por perfil

Autor: JARVIS Team
Versão: 4.0.0
"""

import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

# Import do sistema de monitors
try:
    from ..monitors import MonitorManager, load_monitors_from_config
    MONITORS_AVAILABLE = True
except ImportError:
    MONITORS_AVAILABLE = False
    MonitorManager = None

logger = logging.getLogger(__name__)


class ContactType(Enum):
    """Tipos de contato para definir tom da conversa"""
    NAMORADA = "namorada"
    FAMILIA = "familia"
    TRABALHO = "trabalho"
    AMIGO = "amigo"
    DESCONHECIDO = "desconhecido"


@dataclass
class ContactProfile:
    """
    Perfil de contato - Define como responder
    
    Strategy Pattern: Cada perfil tem sua estratégia de resposta
    """
    name: str
    phone: str = ""
    contact_type: ContactType = ContactType.AMIGO
    
    # Configurações de resposta
    tone: str = "casual"  # casual, formal, carinhoso, profissional
    emoji_frequency: str = "moderado"  # nenhum, pouco, moderado, muito
    formality: str = "media"  # baixa, media, alta
    
    # Contexto personalizado
    context: str = ""  # Ex: "Minha namorada, gosta de gatinhos"
    custom_instructions: str = ""  # Instruções extras para IA
    
    # Histórico
    conversation_history: List[Dict] = field(default_factory=list)
    
    def get_system_prompt(self) -> str:
        """Gera prompt do sistema baseado no perfil"""
        prompts = {
            ContactType.NAMORADA: """
                Você escreve mensagens carinhosas para a namorada do usuário.
                Use apelidos carinhosos, emojis de coração, seja romântico e atencioso.
                Demonstre interesse genuíno e carinho.
            """,
            ContactType.FAMILIA: """
                Você escreve mensagens para família do usuário.
                Seja respeitoso, amoroso e atencioso.
                Use um tom familiar e acolhedor.
            """,
            ContactType.TRABALHO: """
                Você escreve mensagens profissionais.
                Seja formal, objetivo e cortês.
                Evite emojis excessivos e gírias.
            """,
            ContactType.AMIGO: """
                Você escreve mensagens para amigos.
                Seja casual, divertido e natural.
                Use gírias e humor quando apropriado.
            """,
            ContactType.DESCONHECIDO: """
                Você escreve mensagens educadas e neutras.
                Seja cordial mas não íntimo.
            """
        }
        
        base = prompts.get(self.contact_type, prompts[ContactType.DESCONHECIDO])
        
        if self.context:
            base += f"\n\nContexto adicional: {self.context}"
        
        if self.custom_instructions:
            base += f"\n\nInstruções especiais: {self.custom_instructions}"
        
        return base.strip()
    
    def add_message(self, role: str, content: str):
        """Adiciona mensagem ao histórico"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        # Manter apenas últimas 20 mensagens
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
    
    def to_dict(self) -> Dict:
        """Converte para dicionário"""
        return {
            "name": self.name,
            "phone": self.phone,
            "contact_type": self.contact_type.value,
            "tone": self.tone,
            "emoji_frequency": self.emoji_frequency,
            "formality": self.formality,
            "context": self.context,
            "custom_instructions": self.custom_instructions,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ContactProfile':
        """Cria a partir de dicionário"""
        contact_type = ContactType(data.get("contact_type", "amigo"))
        return cls(
            name=data.get("name", ""),
            phone=data.get("phone", ""),
            contact_type=contact_type,
            tone=data.get("tone", "casual"),
            emoji_frequency=data.get("emoji_frequency", "moderado"),
            formality=data.get("formality", "media"),
            context=data.get("context", ""),
            custom_instructions=data.get("custom_instructions", ""),
        )


class MessageHandler:
    """
    Gerenciador de mensagens
    
    Observer Pattern: Notifica handlers quando mensagem chega
    Integra com MonitorManager para monitoramento avançado
    """
    
    def __init__(self, enable_monitors: bool = True):
        self.profiles: Dict[str, ContactProfile] = {}
        self.monitored_contacts: List[str] = []
        self.handlers: List[Callable] = []
        
        # Integração com sistema de monitors
        self.monitor_manager = None
        if enable_monitors and MONITORS_AVAILABLE:
            try:
                self.monitor_manager = load_monitors_from_config()
                logger.info(f"🔍 MonitorManager carregado: {len(self.monitor_manager)} monitors")
            except Exception as e:
                logger.warning(f"Não foi possível carregar monitors: {e}")
    
    def add_profile(self, profile: ContactProfile):
        """Adiciona perfil de contato"""
        key = profile.phone or profile.name.lower()
        self.profiles[key] = profile
        logger.info(f"📝 Perfil adicionado: {profile.name}")
    
    def get_profile(self, identifier: str) -> Optional[ContactProfile]:
        """Obtém perfil por nome ou telefone"""
        # Busca exata
        if identifier in self.profiles:
            return self.profiles[identifier]
        
        # Busca por nome (case insensitive)
        identifier_lower = identifier.lower()
        for key, profile in self.profiles.items():
            if profile.name.lower() == identifier_lower:
                return profile
            if identifier_lower in profile.name.lower():
                return profile
        
        return None
    
    def add_monitored(self, contact: str):
        """Adiciona contato à lista de monitoramento"""
        if contact not in self.monitored_contacts:
            self.monitored_contacts.append(contact)
            logger.info(f"👁️ Monitorando: {contact}")
    
    def remove_monitored(self, contact: str):
        """Remove contato do monitoramento"""
        if contact in self.monitored_contacts:
            self.monitored_contacts.remove(contact)
            logger.info(f"👁️ Parou de monitorar: {contact}")
    
    def is_monitored(self, contact: str) -> bool:
        """Verifica se contato está sendo monitorado"""
        contact_lower = contact.lower()
        for monitored in self.monitored_contacts:
            if monitored.lower() in contact_lower or contact_lower in monitored.lower():
                return True
        return False
    
    def register_handler(self, handler: Callable):
        """Registra handler para mensagens"""
        self.handlers.append(handler)
    
    def handle_message(self, message: Dict):
        """
        Processa mensagem recebida.
        Envia para handlers e para MonitorManager (Observer pattern)
        """
        # Dispatch para handlers registrados
        for handler in self.handlers:
            try:
                handler(message)
            except Exception as e:
                logger.error(f"Erro no handler: {e}")
        
        # Dispatch para MonitorManager (keyword, contact, media monitors)
        if self.monitor_manager:
            try:
                # Converte formato da mensagem para evento de monitor
                event = self._message_to_event(message)
                self.monitor_manager.dispatch(event)
            except Exception as e:
                logger.error(f"Erro ao despachar para monitors: {e}")
    
    def _message_to_event(self, message: Dict) -> Dict:
        """Converte mensagem do WhatsApp para formato de evento dos monitors"""
        # Extrai tipo de mídia se houver
        media_type = None
        if message.get('hasMedia'):
            media_type = message.get('type', 'unknown')  # image, video, audio, document
        
        event_type = 'media' if media_type else 'message'
        
        return {
            'type': event_type,
            'sender': message.get('from', message.get('sender', '')),
            'push_name': message.get('pushName', message.get('notifyName', '')),
            'timestamp': message.get('timestamp', 0),
            'data': {
                'text': message.get('body', message.get('text', '')),
                'mediaType': media_type,
                'mimetype': message.get('mimetype', ''),
                'caption': message.get('caption', ''),
                'base64': message.get('base64', ''),
                'isGroup': message.get('isGroup', False),
                'groupName': message.get('groupName', ''),
            }
        }
    
    def handle_presence(self, presence: Dict):
        """
        Processa evento de presença (online/offline).
        Envia para PresenceMonitor via MonitorManager.
        """
        if not self.monitor_manager:
            return
        
        event = {
            'type': 'presence',
            'sender': presence.get('id', presence.get('jid', '')),
            'push_name': presence.get('pushName', ''),
            'timestamp': presence.get('timestamp', 0),
            'data': {
                'status': presence.get('status', 'unknown'),  # available, unavailable, composing
                'lastSeen': presence.get('lastSeen', None)
            }
        }
        
        try:
            self.monitor_manager.dispatch(event)
        except Exception as e:
            logger.error(f"Erro ao processar presença: {e}")
    
    def create_default_profiles(self):
        """Cria perfis padrão"""
        defaults = [
            ContactProfile(
                name="Namorada",
                contact_type=ContactType.NAMORADA,
                tone="carinhoso",
                emoji_frequency="muito",
                context="Relacionamento amoroso"
            ),
            ContactProfile(
                name="Mãe",
                contact_type=ContactType.FAMILIA,
                tone="respeitoso",
                emoji_frequency="moderado"
            ),
            ContactProfile(
                name="Chefe",
                contact_type=ContactType.TRABALHO,
                tone="profissional",
                emoji_frequency="pouco",
                formality="alta"
            ),
        ]
        
        for profile in defaults:
            self.add_profile(profile)


# Perfis pré-configurados para acesso rápido
DEFAULT_PROFILES = {
    "namorada": ContactProfile(
        name="Namorada",
        contact_type=ContactType.NAMORADA,
        tone="carinhoso",
        emoji_frequency="muito"
    ),
    "familia": ContactProfile(
        name="Família",
        contact_type=ContactType.FAMILIA,
        tone="respeitoso",
        emoji_frequency="moderado"
    ),
    "trabalho": ContactProfile(
        name="Trabalho",
        contact_type=ContactType.TRABALHO,
        tone="profissional",
        emoji_frequency="pouco",
        formality="alta"
    ),
    "amigo": ContactProfile(
        name="Amigo",
        contact_type=ContactType.AMIGO,
        tone="casual",
        emoji_frequency="moderado"
    ),
}
