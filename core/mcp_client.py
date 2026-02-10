# -*- coding: utf-8 -*-
"""
JARVIS MCP Client - Cliente que conecta todos os MCP Servers
Permite que a IA use ferramentas de forma inteligente

Autor: JARVIS Team
Versão: 3.0.0
"""

import asyncio
import json
import logging
import os
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class JarvisMCPClient:
    """
    Cliente MCP para o JARVIS
    
    Integra todos os MCP Servers e fornece interface unificada
    para a IA chamar ferramentas.
    """
    
    def __init__(self, config: Dict = None, jarvis=None):
        self.config = config or {}
        self.jarvis = jarvis
        self.servers = {}
        self.all_tools = {}
        self._running = False

        # Carrega .env
        try:
            from dotenv import load_dotenv
            load_dotenv(Path(__file__).parent.parent / '.env')
        except Exception:
            pass

    async def start(self):
        """Inicializa todos os MCP Servers"""
        logger.info("🚀 Iniciando MCP Client...")

        # Importa e inicializa cada server
        await self._load_server('tools', 'ToolsServer', 'tools_server')
        await self._load_server('memory', 'MemoryServer', 'memory_server')
        await self._load_server('search', 'SearchServer', 'search_server')
        await self._load_server('whatsapp', 'WhatsAppServer', 'whatsapp_server')

        # Jarvis Actions (Orchestrator como skills) só quando jarvis foi injetado
        if self.jarvis:
            await self._load_server(
                'jarvis_actions',
                'JarvisActionsServer',
                'jarvis_actions_server',
                jarvis=self.jarvis,
            )

        self._running = True
        logger.info(f"✅ MCP Client pronto - {len(self.all_tools)} ferramentas disponíveis")

        return self

    async def _load_server(
        self, name: str, class_name: str, module_name: str, **kwargs
    ):
        """Carrega um MCP Server. kwargs são passados ao construtor do server."""
        try:
            module = __import__(f'mcp_servers.{module_name}', fromlist=[class_name])
            server_class = getattr(module, class_name)

            server = server_class(**kwargs) if kwargs else server_class()
            await server.run_embedded()

            self.servers[name] = server

            # Coleta ferramentas
            for tool_name, tool in server.tools.items():
                self.all_tools[tool_name] = {
                    'server': name,
                    'tool': tool,
                    'handler': server.handlers[tool_name]
                }

            logger.info(f"  ✅ {name}: {len(server.tools)} ferramentas")

        except Exception as e:
            logger.warning(f"  ⚠️ {name}: {e}")
    
    async def stop(self):
        """Para todos os servers"""
        for name, server in self.servers.items():
            server.stop()
        self._running = False
    
    def _tool_names_to_hide_when_jarvis(self) -> set:
        """Quando jarvis está presente, envio/resposta WhatsApp passam pelo Orchestrator (whatsapp_send)."""
        return {'send_whatsapp', 'reply_whatsapp'}

    def get_tools_for_openai(self) -> List[Dict]:
        """
        Retorna ferramentas no formato OpenAI Function Calling.
        Com jarvis injetado, esconde send_whatsapp/reply_whatsapp para usar apenas whatsapp_send (Orchestrator).
        """
        tools = []
        hide = self._tool_names_to_hide_when_jarvis() if self.jarvis else set()
        for tool_name, info in self.all_tools.items():
            if tool_name in hide:
                continue
            tool = info['tool']
            tools.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": tool.parameters,
                        "required": tool.required
                    }
                }
            })
        return tools
    
    def get_tools_for_anthropic(self) -> List[Dict]:
        """
        Retorna ferramentas no formato Anthropic Claude.
        Com jarvis injetado, esconde send_whatsapp/reply_whatsapp.
        """
        tools = []
        hide = self._tool_names_to_hide_when_jarvis() if self.jarvis else set()
        for tool_name, info in self.all_tools.items():
            if tool_name in hide:
                continue
            tool = info['tool']
            tools.append({
                "name": tool_name,
                "description": tool.description,
                "input_schema": {
                    "type": "object",
                    "properties": tool.parameters,
                    "required": tool.required
                }
            })
        return tools
    
    async def call_tool(self, tool_name: str, arguments: Dict) -> str:
        """
        Executa uma ferramenta
        
        Args:
            tool_name: Nome da ferramenta
            arguments: Argumentos
            
        Returns:
            Resultado da execução
        """
        if tool_name not in self.all_tools:
            return f"❌ Ferramenta não encontrada: {tool_name}"
        
        info = self.all_tools[tool_name]
        handler = info['handler']
        
        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**arguments)
            else:
                result = handler(**arguments)
            
            logger.debug(f"🔧 {tool_name}: OK")
            return str(result)
            
        except Exception as e:
            logger.error(f"🔧 {tool_name}: {e}")
            return f"❌ Erro ao executar {tool_name}: {str(e)}"
    
    async def process_tool_calls(self, tool_calls: List[Dict]) -> List[Dict]:
        """
        Processa múltiplas chamadas de ferramentas (OpenAI format)
        
        Args:
            tool_calls: Lista de tool_calls do OpenAI
            
        Returns:
            Lista de resultados
        """
        results = []
        
        for tc in tool_calls:
            tool_name = tc.get('function', {}).get('name', '')
            
            try:
                arguments = json.loads(tc.get('function', {}).get('arguments', '{}'))
            except:
                arguments = {}
            
            result = await self.call_tool(tool_name, arguments)
            
            results.append({
                "tool_call_id": tc.get('id', ''),
                "role": "tool",
                "content": result
            })
        
        return results
    
    def list_tools(self) -> str:
        """Lista todas as ferramentas disponíveis"""
        lines = ["🔧 **Ferramentas Disponíveis**\n"]
        
        # Agrupa por servidor
        by_server = {}
        for tool_name, info in self.all_tools.items():
            server = info['server']
            if server not in by_server:
                by_server[server] = []
            by_server[server].append((tool_name, info['tool'].description))
        
        server_names = {
            'tools': '🖥️ Sistema',
            'memory': '🧠 Memória',
            'search': '🔍 Pesquisa',
            'whatsapp': '📱 WhatsApp',
            'jarvis_actions': '📋 WhatsApp (Orchestrator)',
        }
        
        for server, tools in by_server.items():
            lines.append(f"\n**{server_names.get(server, server)}**")
            for name, desc in tools:
                lines.append(f"• `{name}`: {desc[:60]}...")
        
        return "\n".join(lines)
    
    def get_system_prompt(self) -> str:
        """
        Retorna system prompt com instruções sobre ferramentas
        
        Returns:
            String para usar como system prompt
        """
        # Pega contexto da memória se disponível
        memory_context = ""
        if 'memory' in self.servers:
            identity = self.servers['memory']._cache.get('identity', {})
            user_info = self.servers['memory']._cache.get('user_info', {})
            
            memory_context = f"""
=== MINHA IDENTIDADE ===
Nome: {identity.get('name', 'JARVIS')}
Criador: {identity.get('creator', 'Desconhecido')}
Propósito: {identity.get('purpose', 'Assistente virtual')}

=== INFORMAÇÕES DO USUÁRIO ===
"""
            for k, v in user_info.items():
                memory_context += f"- {k}: {v}\n"

        prompt_base = f"""Você é JARVIS, um assistente virtual inteligente inspirado no J.A.R.V.I.S. do Homem de Ferro.

{memory_context}

=== REGRAS ===
1. Sempre responda em português brasileiro
2. Seja direto, educado e com um leve humor britânico
3. Use as ferramentas disponíveis para realizar tarefas
4. Se não souber algo, admita e busque informação
5. Chame o usuário pelo nome quando souber
6. Salve informações importantes usando a ferramenta 'remember'

=== FERRAMENTAS DISPONÍVEIS ===
Você tem acesso a {len(self.all_tools)} ferramentas para:
- 🖥️ Controlar o computador (executar comandos, abrir apps, gerenciar arquivos)
- 🧠 Lembrar informações (salvar e recuperar memórias)
- 🔍 Pesquisar na web (DuckDuckGo, Wikipedia, clima)
- 📱 WhatsApp (enviar mensagens, ver conversas, monitorar, autopilot)
"""
        if self.jarvis:
            prompt_whatsapp = """
=== WHATSAPP (use SEMPRE as ferramentas jarvis_actions) ===
Para qualquer comando de WhatsApp use as ferramentas do Orchestrator:
- Monitorar conversa → whatsapp_monitor(contact)
- Ativar autopilot / auto-resposta → whatsapp_autoreply_enable(contact, tone?)
- Desativar autopilot / "pare de responder" → whatsapp_autoreply_disable(contact?) (contact opcional: usa contato ativo)
- Mudar tom do autopilot → whatsapp_autopilot_set_tone(contact, tone)
- Status do autopilot → whatsapp_autopilot_status()
- Status do monitoramento → whatsapp_monitor_status()
- Cancelar monitoramento / parar de monitorar → whatsapp_monitor_disable(contact?) (não confundir com desativar autopilot)
- Enviar mensagem → whatsapp_send(contact, message)

NUNCA diga que não pode enviar ou monitorar. Use whatsapp_send para enviar; use whatsapp_autoreply_disable quando o usuário disser "pare de responder" ou "desative autopilot"; use whatsapp_monitor_disable quando disser "cancele o monitoramento" ou "pare de monitorar" (nunca interprete como envio).
"""
        else:
            prompt_whatsapp = """
=== WHATSAPP ===
Use send_whatsapp quando o usuário pedir para enviar ou responder. Se o serviço estiver fora do ar, diga para iniciar com opção 3 ou 4 no start.bat.
"""
        return (
            prompt_base
            + prompt_whatsapp
            + """
USE AS FERRAMENTAS quando for útil. Não apenas descreva o que faria - FAÇA usando as ferramentas!

Exemplos:
- Se perguntarem seu nome → Use get_identity
- Se pedirem para lembrar algo → Use remember
- Se perguntarem o clima → Use get_weather
- Se pedirem para pesquisar → Use web_search
- Enviar/monitorar/autopilot WhatsApp → Use as ferramentas whatsapp_* (whatsapp_send, whatsapp_monitor, etc.)
"""
        )


# === FUNÇÃO AUXILIAR PARA CRIAR CLIENTE ===
async def create_mcp_client(jarvis=None) -> JarvisMCPClient:
    """Cria e inicializa o cliente MCP. Se jarvis for passado, carrega Jarvis Actions (Orchestrator como skills)."""
    client = JarvisMCPClient(jarvis=jarvis)
    await client.start()
    return client
