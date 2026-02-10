# -*- coding: utf-8 -*-
"""
JARVIS AI Engine com MCP Integration
Usa OpenAI Function Calling com ferramentas MCP

Autor: JARVIS Team
Versão: 3.0.0
"""

import asyncio
import json
import logging
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

# OpenAI
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class AIResponse:
    """Resposta da IA"""
    text: str
    tool_calls: List[Dict] = None
    tokens_used: int = 0
    model: str = ""
    success: bool = True
    error: str = ""


class JarvisAI:
    """
    Motor de IA do JARVIS com suporte MCP
    
    Usa OpenAI GPT-4 com Function Calling para
    selecionar e executar ferramentas automaticamente.
    """
    
    def __init__(self, mcp_client=None):
        """
        Inicializa o motor de IA
        
        Args:
            mcp_client: Cliente MCP para ferramentas
        """
        self.mcp_client = mcp_client
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4-turbo')
        self.max_tokens = int(os.getenv('OPENAI_MAX_TOKENS', '2000'))
        self.temperature = float(os.getenv('OPENAI_TEMPERATURE', '0.7'))
        
        # Histórico de conversas
        self.conversation_history: List[Dict] = []
        self.max_history = 20
        
        # Inicializa cliente OpenAI
        self.client = None
        if OPENAI_AVAILABLE:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.client = AsyncOpenAI(api_key=api_key)
            else:
                logger.warning("⚠️ OPENAI_API_KEY não configurada")
    
    def set_mcp_client(self, mcp_client):
        """Define o cliente MCP"""
        self.mcp_client = mcp_client
    
    async def process(self, message: str, user_id: str = "default") -> AIResponse:
        """
        Processa uma mensagem e retorna resposta
        
        Args:
            message: Mensagem do usuário
            user_id: ID do usuário
            
        Returns:
            AIResponse com o resultado
        """
        if not self.client:
            return AIResponse(
                text="❌ OpenAI não configurada. Defina OPENAI_API_KEY no .env",
                success=False,
                error="API key missing"
            )
        
        try:
            # Monta mensagens
            messages = self._build_messages(message)
            
            # Pega ferramentas MCP
            tools = []
            if self.mcp_client:
                tools = self.mcp_client.get_tools_for_openai()
            
            # Primeira chamada à API
            logger.debug(f"🤖 Enviando para {self.model}...")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            # Processa resposta
            result = await self._process_response(response, messages)
            
            # Salva no histórico
            self._update_history(message, result.text)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro AI: {e}")
            return AIResponse(
                text=f"Desculpe, ocorreu um erro: {str(e)}",
                success=False,
                error=str(e)
            )
    
    def _build_messages(self, message: str) -> List[Dict]:
        """Constrói lista de mensagens para a API"""
        messages = []
        
        # System prompt
        system_prompt = self._get_system_prompt()
        messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        # Histórico recente
        for item in self.conversation_history[-self.max_history:]:
            messages.append({"role": "user", "content": item['user']})
            messages.append({"role": "assistant", "content": item['assistant']})
        
        # Mensagem atual
        messages.append({
            "role": "user",
            "content": message
        })
        
        return messages
    
    def _get_system_prompt(self) -> str:
        """Retorna o system prompt"""
        if self.mcp_client:
            return self.mcp_client.get_system_prompt()
        
        return """Você é JARVIS, um assistente virtual inteligente inspirado no J.A.R.V.I.S. do Homem de Ferro.

=== REGRAS ===
1. Sempre responda em português brasileiro
2. Seja direto, educado e com um leve humor britânico
3. Se não souber algo, admita honestamente
4. Mantenha contexto das conversas anteriores
5. Você PODE enviar mensagens pelo WhatsApp quando o serviço estiver ativo (start.bat opção 3 ou 4). NUNCA diga que não pode enviar mensagens ou interagir com contatos.
6. IMPORTANTE: Responda sempre ao conteúdo da mensagem. Se o usuário fizer pergunta, pedido (conta, informação, tarefa) ou pedir ajuda, responda de forma útil e concreta. NÃO responda apenas com um cumprimento genérico (ex: "Olá! Como posso ajudar?") a menos que a mensagem seja APENAS um cumprimento (oi, olá, bom dia). Para "me ajude com uma conta", "você só responde olá?", "oi Jarvis" etc., dê uma resposta útil ao que foi pedido.
"""
    
    async def _process_response(self, response, messages: List[Dict]) -> AIResponse:
        """
        Processa resposta da API, executando tools se necessário
        
        Executa múltiplos ciclos de tool calls se a IA continuar chamando tools.
        """
        message = response.choices[0].message
        total_tokens = response.usage.total_tokens if response.usage else 0
        
        # Máximo de ciclos para evitar loops infinitos
        max_cycles = 5
        cycle = 0
        
        while message.tool_calls and cycle < max_cycles:
            cycle += 1
            logger.info(f"🔧 Executando {len(message.tool_calls)} ferramenta(s) (ciclo {cycle})...")
            
            # Adiciona a resposta do assistente com tool_calls
            messages.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
            })
            
            # Executa cada tool
            for tc in message.tool_calls:
                tool_name = tc.function.name
                
                try:
                    arguments = json.loads(tc.function.arguments)
                except:
                    arguments = {}
                
                logger.info(f"  → {tool_name}({list(arguments.keys())})")
                
                if self.mcp_client:
                    result = await self.mcp_client.call_tool(tool_name, arguments)
                else:
                    result = "Ferramentas não disponíveis"
                
                # Adiciona resultado
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result)
                })
            
            # Chama API novamente para IA processar resultados
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.mcp_client.get_tools_for_openai() if self.mcp_client else None,
                tool_choice="auto" if self.mcp_client else None,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            message = response.choices[0].message
            if response.usage:
                total_tokens += response.usage.total_tokens
        
        if cycle >= max_cycles:
            logger.warning("⚠️ Máximo de ciclos de tools atingido")
        
        return AIResponse(
            text=message.content or "Entendido.",
            tool_calls=[
                {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
                for tc in (message.tool_calls or [])
            ],
            tokens_used=total_tokens,
            model=self.model,
            success=True
        )
    
    def _update_history(self, user_message: str, assistant_message: str):
        """Atualiza histórico de conversa"""
        self.conversation_history.append({
            'user': user_message,
            'assistant': assistant_message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Limita tamanho
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history:]
    
    def clear_history(self):
        """Limpa histórico de conversas"""
        self.conversation_history = []
    
    async def get_embedding(self, text: str) -> List[float]:
        """
        Gera embedding para texto (útil para busca semântica)
        
        Args:
            text: Texto para gerar embedding
            
        Returns:
            Lista de floats representando o embedding
        """
        if not self.client:
            return []
        
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Erro embedding: {e}")
            return []


# === SINGLETON GLOBAL ===
_ai_instance = None


def get_ai(mcp_client=None) -> JarvisAI:
    """Retorna instância global da IA"""
    global _ai_instance
    if _ai_instance is None:
        _ai_instance = JarvisAI(mcp_client)
    elif mcp_client:
        _ai_instance.set_mcp_client(mcp_client)
    return _ai_instance
