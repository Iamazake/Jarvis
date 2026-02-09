# -*- coding: utf-8 -*-
"""
MCP Base - Protocolo Base para MCP Servers
Model Context Protocol implementation

Autor: JARVIS Team
Versão: 3.0.0
"""

import json
import sys
import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@dataclass
class Tool:
    """Definição de uma ferramenta MCP"""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": self.parameters,
                "required": self.required
            }
        }


@dataclass
class ToolResult:
    """Resultado da execução de uma ferramenta"""
    success: bool
    content: Any
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        if self.success:
            return {
                "content": [
                    {"type": "text", "text": str(self.content)}
                ]
            }
        else:
            return {
                "content": [
                    {"type": "text", "text": f"Erro: {self.error}"}
                ],
                "isError": True
            }


class MCPServer(ABC):
    """
    Classe base para MCP Servers
    
    Implementa o protocolo MCP sobre stdio
    """
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.tools: Dict[str, Tool] = {}
        self.handlers: Dict[str, Callable] = {}
        self._running = False
    
    def register_tool(self, tool: Tool, handler: Callable):
        """Registra uma ferramenta e seu handler"""
        self.tools[tool.name] = tool
        self.handlers[tool.name] = handler
        logger.debug(f"Ferramenta registrada: {tool.name}")
    
    @abstractmethod
    async def setup_tools(self):
        """Configura as ferramentas do server (implementar nas subclasses)"""
        pass
    
    async def handle_request(self, request: Dict) -> Dict:
        """Processa uma requisição MCP"""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "initialize":
                result = await self._handle_initialize(params)
            elif method == "tools/list":
                result = await self._handle_list_tools()
            elif method == "tools/call":
                result = await self._handle_call_tool(params)
            elif method == "ping":
                result = {"status": "ok"}
            else:
                return self._error_response(request_id, -32601, f"Método não encontrado: {method}")
            
            return self._success_response(request_id, result)
            
        except Exception as e:
            logger.error(f"Erro processando requisição: {e}")
            return self._error_response(request_id, -32603, str(e))
    
    async def _handle_initialize(self, params: Dict) -> Dict:
        """Inicialização do protocolo"""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": self.name,
                "version": self.version
            }
        }
    
    async def _handle_list_tools(self) -> Dict:
        """Lista todas as ferramentas disponíveis"""
        return {
            "tools": [tool.to_dict() for tool in self.tools.values()]
        }
    
    async def _handle_call_tool(self, params: Dict) -> Dict:
        """Executa uma ferramenta"""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        
        if tool_name not in self.handlers:
            return ToolResult(False, None, f"Ferramenta não encontrada: {tool_name}").to_dict()
        
        try:
            handler = self.handlers[tool_name]
            
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**arguments)
            else:
                result = handler(**arguments)
            
            return ToolResult(True, result).to_dict()
            
        except Exception as e:
            logger.error(f"Erro executando {tool_name}: {e}")
            return ToolResult(False, None, str(e)).to_dict()
    
    def _success_response(self, request_id: Any, result: Any) -> Dict:
        """Monta resposta de sucesso"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }
    
    def _error_response(self, request_id: Any, code: int, message: str) -> Dict:
        """Monta resposta de erro"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }
    
    async def run_stdio(self):
        """Executa o server via stdio (para MCP)"""
        self._running = True
        await self.setup_tools()
        
        logger.info(f"🚀 {self.name} MCP Server iniciado")
        
        while self._running:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                request = json.loads(line)
                response = await self.handle_request(request)
                
                print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON inválido: {e}")
            except Exception as e:
                logger.error(f"Erro no loop principal: {e}")
    
    async def run_embedded(self):
        """Executa o server em modo embarcado (sem stdio)"""
        self._running = True
        await self.setup_tools()
        logger.info(f"🚀 {self.name} MCP Server (embedded) iniciado")
    
    def stop(self):
        """Para o server"""
        self._running = False


class MCPClient:
    """
    Cliente MCP para conectar a múltiplos servers
    
    Pode usar servers embarcados (in-process) ou via subprocess
    """
    
    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        self.all_tools: Dict[str, tuple] = {}  # tool_name -> (server_name, tool)
    
    def register_server(self, name: str, server: MCPServer):
        """Registra um server embarcado"""
        self.servers[name] = server
    
    async def initialize_all(self):
        """Inicializa todos os servers"""
        for name, server in self.servers.items():
            await server.run_embedded()
            
            # Coleta todas as ferramentas
            for tool_name, tool in server.tools.items():
                self.all_tools[tool_name] = (name, tool)
            
            logger.info(f"✅ {name}: {len(server.tools)} ferramentas")
    
    def get_tools_for_ai(self) -> List[Dict]:
        """Retorna ferramentas formatadas para a IA"""
        tools = []
        for tool_name, (server_name, tool) in self.all_tools.items():
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
    
    async def call_tool(self, tool_name: str, arguments: Dict) -> Any:
        """Chama uma ferramenta de qualquer server"""
        if tool_name not in self.all_tools:
            raise ValueError(f"Ferramenta não encontrada: {tool_name}")
        
        server_name, tool = self.all_tools[tool_name]
        server = self.servers[server_name]
        
        result = await server._handle_call_tool({
            "name": tool_name,
            "arguments": arguments
        })
        
        # Extrai o texto do resultado
        if "content" in result and len(result["content"]) > 0:
            return result["content"][0].get("text", "")
        
        return result
    
    async def stop_all(self):
        """Para todos os servers"""
        for server in self.servers.values():
            server.stop()
