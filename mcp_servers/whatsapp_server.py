# -*- coding: utf-8 -*-
"""
WhatsApp MCP Server - Integração com WhatsApp
Conecta ao serviço Node.js/Baileys para enviar e receber mensagens

Autor: JARVIS Team
Versão: 3.0.0
"""

import os
import sys
import asyncio
import aiohttp
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_servers.base import MCPServer, Tool

logger = logging.getLogger(__name__)


class WhatsAppServer(MCPServer):
    """
    MCP Server para WhatsApp
    
    Ferramentas:
    - send_whatsapp: Envia mensagem
    - get_unread_messages: Lista mensagens não lidas
    - get_contacts: Lista contatos
    - get_chat_history: Histórico de um chat
    - get_whatsapp_status: Status da conexão
    """
    
    def __init__(self):
        super().__init__("jarvis-whatsapp", "3.0.0")
        self._load_env()
        
        # Cache de contatos
        self._contacts_cache = {}
        self._last_messages = []
    
    def _load_env(self):
        """Carrega configurações"""
        try:
            from dotenv import load_dotenv
            load_dotenv(Path(__file__).parent.parent / '.env')
        except:
            pass
        
        self.api_url = os.getenv('WHATSAPP_API_URL', 'http://localhost:3001')
        self.require_confirmation = True
    
    async def setup_tools(self):
        """Configura ferramentas do WhatsApp"""
        
        # 1. Enviar mensagem
        self.register_tool(
            Tool(
                name="send_whatsapp",
                description="Envia uma mensagem de WhatsApp. Pode enviar para contato ou número.",
                parameters={
                    "to": {
                        "type": "string",
                        "description": "Nome do contato ou número (com código do país, ex: 5511999999999)"
                    },
                    "message": {
                        "type": "string",
                        "description": "Texto da mensagem"
                    }
                },
                required=["to", "message"]
            ),
            self.send_whatsapp
        )
        
        # 2. Mensagens não lidas
        self.register_tool(
            Tool(
                name="get_unread_messages",
                description="Lista as mensagens de WhatsApp não lidas.",
                parameters={
                    "limit": {
                        "type": "integer",
                        "description": "Máximo de mensagens (padrão: 20)"
                    }
                },
                required=[]
            ),
            self.get_unread_messages
        )
        
        # 3. Lista de contatos
        self.register_tool(
            Tool(
                name="get_contacts",
                description="Lista os contatos do WhatsApp.",
                parameters={
                    "search": {
                        "type": "string",
                        "description": "Filtrar por nome"
                    }
                },
                required=[]
            ),
            self.get_contacts
        )
        
        # 4. Histórico de chat
        self.register_tool(
            Tool(
                name="get_chat_history",
                description="Retorna o histórico de mensagens de um contato.",
                parameters={
                    "contact": {
                        "type": "string",
                        "description": "Nome do contato ou número"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Número de mensagens (padrão: 20)"
                    }
                },
                required=["contact"]
            ),
            self.get_chat_history
        )
        
        # 5. Status da conexão
        self.register_tool(
            Tool(
                name="get_whatsapp_status",
                description="Verifica o status da conexão do WhatsApp.",
                parameters={},
                required=[]
            ),
            self.get_whatsapp_status
        )
        
        # 6. Responder mensagem
        self.register_tool(
            Tool(
                name="reply_whatsapp",
                description="Responde à última mensagem de um contato.",
                parameters={
                    "contact": {
                        "type": "string",
                        "description": "Nome do contato"
                    },
                    "message": {
                        "type": "string",
                        "description": "Mensagem de resposta"
                    }
                },
                required=["contact", "message"]
            ),
            self.reply_whatsapp
        )
        
        logger.info(f"✅ {len(self.tools)} ferramentas de WhatsApp registradas")
    
    # === COMUNICAÇÃO COM API ===
    
    def _is_connection_error(self, err_msg: str) -> bool:
        """Indica se o erro é de serviço WhatsApp não rodando."""
        err_lower = (err_msg or "").lower()
        return (
            "connection refused" in err_lower
            or "cannot connect" in err_lower
            or "connection error" in err_lower
            or "connection_reset" in err_lower
            or "nodename nor servname" in err_lower
        )

    def _service_not_running_message(self) -> str:
        """Mensagem padrão quando o serviço WhatsApp não está rodando."""
        return (
            "O serviço do WhatsApp não está rodando. "
            "Para enviar mensagens, inicie o WhatsApp primeiro: "
            "no menu do start.bat escolha opção 3 (WhatsApp) ou 4 (Tudo), "
            "ou execute: cd services/whatsapp && node index.js"
        )

    async def _api_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Faz requisição à API do WhatsApp"""
        url = f"{self.api_url}{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    async with session.get(url, timeout=10) as resp:
                        return await resp.json()
                else:
                    async with session.post(url, json=data, timeout=10) as resp:
                        return await resp.json()
                        
        except aiohttp.ClientConnectorError as e:
            logger.error(f"API WhatsApp inacessível: {e}")
            return {"error": self._service_not_running_message(), "service_down": True}
        except aiohttp.ClientError as e:
            err = str(e)
            if self._is_connection_error(err):
                return {"error": self._service_not_running_message(), "service_down": True}
            logger.error(f"Erro na API: {e}")
            return {"error": err}
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout na API: {e}")
            return {"error": "Timeout ao conectar no WhatsApp. O serviço está rodando?", "service_down": True}
        except Exception as e:
            logger.error(f"Erro: {e}")
            err = str(e)
            if self._is_connection_error(err):
                return {"error": self._service_not_running_message(), "service_down": True}
            return {"error": err}
    
    def _format_phone(self, number: str) -> str:
        """Formata número de telefone"""
        # Remove caracteres não numéricos
        phone = ''.join(filter(str.isdigit, number))
        
        # Adiciona código do Brasil se não tiver
        if len(phone) == 11:  # DDD + número
            phone = '55' + phone
        elif len(phone) == 9:  # Só número
            phone = '5511' + phone  # Assume SP
        
        return phone + '@s.whatsapp.net'
    
    async def _find_contact(self, name: str) -> Optional[str]:
        """Busca contato por nome"""
        if not self._contacts_cache:
            await self.get_contacts()
        
        name_lower = name.lower()
        
        for jid, contact_name in self._contacts_cache.items():
            if name_lower in contact_name.lower():
                return jid
        
        return None
    
    # === IMPLEMENTAÇÃO DAS FERRAMENTAS ===
    
    async def send_whatsapp(self, to: str, message: str) -> str:
        """Envia mensagem de WhatsApp"""
        # Determina o destinatário
        if to.isdigit() or to.startswith('+'):
            jid = self._format_phone(to)
        else:
            # Busca contato
            jid = await self._find_contact(to)
            if not jid:
                return f"❌ Contato não encontrado: {to}"
        
        # Envia via API
        result = await self._api_request("POST", "/send", {
            "to": jid,
            "message": message
        })
        
        if "error" in result:
            err = result["error"]
            if result.get("service_down"):
                return f"❌ **WhatsApp não está rodando**\n\n{err}"
            return f"❌ Erro ao enviar: {err}"
        
        return f"✅ Mensagem enviada para {to}"
    
    async def get_unread_messages(self, limit: int = 20) -> str:
        """Lista mensagens não lidas"""
        result = await self._api_request("GET", "/messages/unread")
        
        if "error" in result:
            # Tenta endpoint alternativo
            result = await self._api_request("GET", "/chats")
            
            if "error" in result:
                return f"❌ Erro: {result['error']}\n\n💡 Verifique se o serviço WhatsApp está rodando em {self.api_url}"
        
        messages = result.get("messages", result.get("chats", []))
        
        if not messages:
            return "📭 Nenhuma mensagem não lida"
        
        self._last_messages = messages[:limit]
        
        lines = ["📬 **Mensagens não lidas**\n"]
        
        for msg in messages[:limit]:
            sender = msg.get('pushName') or msg.get('from', 'Desconhecido')
            text = msg.get('message') or msg.get('body', '')
            time = msg.get('timestamp', '')
            
            lines.append(f"👤 **{sender}**")
            lines.append(f"   {text[:100]}{'...' if len(text) > 100 else ''}")
            if time:
                lines.append(f"   🕐 {time}")
            lines.append("")
        
        return "\n".join(lines)
    
    async def get_contacts(self, search: str = None) -> str:
        """Lista contatos"""
        result = await self._api_request("GET", "/contacts")
        
        if "error" in result:
            return f"❌ Erro: {result['error']}"
        
        contacts = result.get("contacts", [])
        
        # Atualiza cache
        for c in contacts:
            jid = c.get('id', c.get('jid', ''))
            name = c.get('name') or c.get('pushName') or jid.split('@')[0]
            self._contacts_cache[jid] = name
        
        if search:
            contacts = [c for c in contacts 
                       if search.lower() in (c.get('name') or '').lower()]
        
        if not contacts:
            return "📭 Nenhum contato encontrado"
        
        lines = ["📱 **Contatos**\n"]
        
        for c in contacts[:30]:
            name = c.get('name') or c.get('pushName') or 'Sem nome'
            number = c.get('id', '').replace('@s.whatsapp.net', '')
            lines.append(f"• {name} ({number})")
        
        if len(contacts) > 30:
            lines.append(f"\n... e mais {len(contacts) - 30} contatos")
        
        return "\n".join(lines)
    
    async def get_chat_history(self, contact: str, limit: int = 20) -> str:
        """Retorna histórico de chat"""
        # Encontra o contato
        if contact.isdigit() or contact.startswith('+'):
            jid = self._format_phone(contact)
        else:
            jid = await self._find_contact(contact)
            if not jid:
                return f"❌ Contato não encontrado: {contact}"
        
        result = await self._api_request("GET", f"/chat/{jid}?limit={limit}")
        
        if "error" in result:
            return f"❌ Erro: {result['error']}"
        
        messages = result.get("messages", [])
        
        if not messages:
            return f"📭 Nenhuma mensagem com {contact}"
        
        lines = [f"💬 **Chat com {contact}**\n"]
        
        for msg in messages:
            is_me = msg.get('fromMe', False)
            text = msg.get('message') or msg.get('body', '')
            time = msg.get('timestamp', '')
            
            prefix = "🔵 Eu:" if is_me else "⚪ Ele:"
            lines.append(f"{prefix} {text[:150]}")
        
        return "\n".join(lines)
    
    async def get_whatsapp_status(self) -> str:
        """Verifica status da conexão"""
        result = await self._api_request("GET", "/status")
        
        if "error" in result:
            return f"""❌ **WhatsApp Desconectado**

Erro: {result['error']}

💡 Para conectar:
1. Abra o terminal
2. Execute: cd services/whatsapp && node index.js
3. Escaneie o QR Code"""
        
        status = result.get("status", "unknown")
        connected = result.get("connected", False)
        phone = result.get("phone", "")
        
        if connected:
            return f"""✅ **WhatsApp Conectado**

📱 Número: {phone}
🟢 Status: {status}
🔗 API: {self.api_url}"""
        else:
            return f"""⚠️ **WhatsApp Parcialmente Conectado**

📱 Status: {status}

💡 Pode ser necessário escanear o QR Code novamente."""
    
    async def reply_whatsapp(self, contact: str, message: str) -> str:
        """Responde à última mensagem de um contato"""
        # Encontra nas últimas mensagens
        for msg in self._last_messages:
            sender = msg.get('pushName') or msg.get('from', '')
            if contact.lower() in sender.lower():
                jid = msg.get('from') or msg.get('jid')
                if jid:
                    result = await self._api_request("POST", "/send", {
                        "to": jid,
                        "message": message
                    })
                    
                    if "error" in result:
                        return f"❌ Erro: {result['error']}"
                    
                    return f"✅ Resposta enviada para {contact}"
        
        # Se não encontrou, tenta buscar contato
        return await self.send_whatsapp(contact, message)


# === MAIN ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = WhatsAppServer()
    asyncio.run(server.run_stdio())
