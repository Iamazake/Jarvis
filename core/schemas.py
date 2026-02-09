# -*- coding: utf-8 -*-
"""
Schemas - Validação de Dados com Pydantic
Schemas para validação de entrada e saída

Autor: JARVIS Team
Versão: 3.1.0
"""

from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field, validator, ConfigDict


# ==========================================
# Schemas Base
# ==========================================

class BaseSchema(BaseModel):
    """Schema base com configurações comuns"""
    model_config = ConfigDict(
        extra='forbid',
        validate_assignment=True,
        use_enum_values=True
    )


# ==========================================
# Schemas de Mensagens
# ==========================================

class MessageSchema(BaseSchema):
    """Schema para mensagens do usuário"""
    content: str = Field(..., min_length=1, max_length=10000, description="Conteúdo da mensagem")
    source: Literal['cli', 'voice', 'whatsapp', 'web'] = Field(default='cli', description="Origem da mensagem")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadados adicionais")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="Timestamp da mensagem")
    
    @validator('content')
    def validate_content(cls, v):
        """Valida conteúdo não vazio"""
        if not v or not v.strip():
            raise ValueError('Conteúdo da mensagem não pode ser vazio')
        return v.strip()


class ResponseSchema(BaseSchema):
    """Schema para respostas do JARVIS"""
    text: str = Field(..., min_length=1, description="Texto da resposta")
    source: str = Field(default='jarvis', description="Origem da resposta")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadados")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="Timestamp")


# ==========================================
# Schemas de Intenção
# ==========================================

class IntentSchema(BaseSchema):
    """Schema para intenção classificada"""
    type: str = Field(..., description="Tipo da intenção")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confiança (0-1)")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Entidades extraídas")
    raw_match: Optional[str] = Field(None, description="Match original")


# ==========================================
# Schemas de Contexto
# ==========================================

class ContextSchema(BaseSchema):
    """Schema para contexto de conversa"""
    history: List[Dict[str, str]] = Field(default_factory=list, description="Histórico de mensagens")
    last_intent: Optional[str] = Field(None, description="Última intenção")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Entidades do contexto")
    session: Dict[str, Any] = Field(default_factory=dict, description="Dados da sessão")
    active_flows: List[str] = Field(default_factory=list, description="Fluxos ativos")


# ==========================================
# Schemas de Módulos
# ==========================================

class ModuleConfigSchema(BaseSchema):
    """Schema para configuração de módulo"""
    enabled: bool = Field(default=True, description="Se o módulo está habilitado")
    config: Dict[str, Any] = Field(default_factory=dict, description="Configurações específicas")


class ModuleStatusSchema(BaseSchema):
    """Schema para status de módulo"""
    name: str = Field(..., description="Nome do módulo")
    status: Literal['🟢', '🟡', '🔴'] = Field(..., description="Status do módulo")
    running: bool = Field(..., description="Se está rodando")
    last_error: Optional[str] = Field(None, description="Último erro")


# ==========================================
# Schemas de IA
# ==========================================

class AIRequestSchema(BaseSchema):
    """Schema para requisição de IA"""
    message: str = Field(..., min_length=1, max_length=10000, description="Mensagem do usuário")
    context: Optional[ContextSchema] = Field(None, description="Contexto da conversa")
    provider: Optional[str] = Field(None, description="Provider de IA específico")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Temperatura")
    max_tokens: Optional[int] = Field(None, ge=1, le=4000, description="Máximo de tokens")


class AIResponseSchema(BaseSchema):
    """Schema para resposta de IA"""
    text: str = Field(..., description="Texto da resposta")
    model: str = Field(..., description="Modelo usado")
    tokens_used: int = Field(default=0, ge=0, description="Tokens utilizados")
    provider: str = Field(..., description="Provider usado")
    cached: bool = Field(default=False, description="Se veio do cache")


# ==========================================
# Schemas de Ferramentas
# ==========================================

class ToolCallSchema(BaseSchema):
    """Schema para chamada de ferramenta"""
    tool_name: str = Field(..., description="Nome da ferramenta")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Argumentos")
    tool_call_id: Optional[str] = Field(None, description="ID da chamada")


class ToolResultSchema(BaseSchema):
    """Schema para resultado de ferramenta"""
    tool_name: str = Field(..., description="Nome da ferramenta")
    result: Any = Field(..., description="Resultado")
    success: bool = Field(..., description="Se foi bem-sucedido")
    error: Optional[str] = Field(None, description="Erro se houver")


# ==========================================
# Schemas de Memória
# ==========================================

class MemorySchema(BaseSchema):
    """Schema para memória"""
    key: str = Field(..., min_length=1, description="Chave da memória")
    value: Any = Field(..., description="Valor")
    category: Literal['user_info', 'facts', 'preferences', 'identity'] = Field(
        ...,
        description="Categoria da memória"
    )
    timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="Timestamp")


class MemoryQuerySchema(BaseSchema):
    """Schema para consulta de memória"""
    key: Optional[str] = Field(None, description="Chave específica")
    category: Optional[str] = Field(None, description="Categoria")
    query: Optional[str] = Field(None, description="Busca textual")


# ==========================================
# Schemas de Pesquisa
# ==========================================

class SearchRequestSchema(BaseSchema):
    """Schema para requisição de pesquisa"""
    query: str = Field(..., min_length=1, max_length=500, description="Termo de pesquisa")
    num_results: int = Field(default=5, ge=1, le=20, description="Número de resultados")
    source: Optional[Literal['web', 'wikipedia', 'news', 'all']] = Field(
        default='all',
        description="Fonte de pesquisa"
    )


class SearchResultSchema(BaseSchema):
    """Schema para resultado de pesquisa"""
    title: str = Field(..., description="Título")
    url: Optional[str] = Field(None, description="URL")
    snippet: str = Field(..., description="Resumo")
    source: str = Field(..., description="Fonte")


# ==========================================
# Schemas de Calendário
# ==========================================

class EventSchema(BaseSchema):
    """Schema para evento"""
    title: str = Field(..., min_length=1, max_length=200, description="Título do evento")
    description: Optional[str] = Field(None, max_length=1000, description="Descrição")
    start_time: datetime = Field(..., description="Início")
    end_time: Optional[datetime] = Field(None, description="Fim")
    location: Optional[str] = Field(None, max_length=200, description="Local")
    reminder_minutes: Optional[int] = Field(None, ge=0, description="Lembrete em minutos")
    
    @validator('end_time')
    def validate_end_time(cls, v, values):
        """Valida que fim é depois do início"""
        if v and 'start_time' in values and v < values['start_time']:
            raise ValueError('Fim deve ser depois do início')
        return v


class ReminderSchema(BaseSchema):
    """Schema para lembrete"""
    message: str = Field(..., min_length=1, max_length=500, description="Mensagem")
    time: datetime = Field(..., description="Horário")
    recurring: Optional[Literal['daily', 'weekly', 'monthly']] = Field(
        None,
        description="Recorrência"
    )


# ==========================================
# Schemas de Automação
# ==========================================

class TriggerSchema(BaseSchema):
    """Schema para trigger de automação"""
    type: Literal['time', 'event', 'command'] = Field(..., description="Tipo de trigger")
    config: Dict[str, Any] = Field(..., description="Configuração do trigger")


class ActionSchema(BaseSchema):
    """Schema para ação de automação"""
    type: Literal['command', 'message', 'search', 'tool'] = Field(..., description="Tipo de ação")
    config: Dict[str, Any] = Field(..., description="Configuração da ação")


class WorkflowSchema(BaseSchema):
    """Schema para workflow"""
    name: str = Field(..., min_length=1, max_length=100, description="Nome do workflow")
    description: Optional[str] = Field(None, max_length=500, description="Descrição")
    trigger: TriggerSchema = Field(..., description="Trigger")
    actions: List[ActionSchema] = Field(..., min_length=1, description="Ações")
    enabled: bool = Field(default=True, description="Se está habilitado")


# ==========================================
# Schemas de Validação
# ==========================================

def validate_message(data: Dict[str, Any]) -> MessageSchema:
    """Valida dados de mensagem"""
    return MessageSchema(**data)


def validate_ai_request(data: Dict[str, Any]) -> AIRequestSchema:
    """Valida requisição de IA"""
    return AIRequestSchema(**data)


def validate_event(data: Dict[str, Any]) -> EventSchema:
    """Valida evento"""
    return EventSchema(**data)


def validate_workflow(data: Dict[str, Any]) -> WorkflowSchema:
    """Valida workflow"""
    return WorkflowSchema(**data)
