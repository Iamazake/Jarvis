# -*- coding: utf-8 -*-
"""
Memory MCP Server - Sistema de Memória Persistente
Conecta ao MySQL para armazenar e recuperar informações

Autor: JARVIS Team
Versão: 3.0.0
"""

import os
import sys
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_servers.base import MCPServer, Tool

logger = logging.getLogger(__name__)


class MemoryServer(MCPServer):
    """
    MCP Server para memória persistente
    
    Ferramentas:
    - remember: Salva informação na memória
    - recall: Recupera informação da memória
    - forget: Remove informação da memória
    - get_user_info: Retorna todas as info do usuário
    - get_conversation_history: Histórico de conversas
    - search_memory: Busca em todas as memórias
    """
    
    def __init__(self):
        super().__init__("jarvis-memory", "3.0.0")
        self._db = None
        self._db_type = None
        
        # Cache local
        self._cache = {
            'user_info': {},
            'identity': {
                'name': 'JARVIS',
                'full_name': 'Just A Rather Very Intelligent System',
                'creator': 'Pedro',
                'purpose': 'Sou seu assistente virtual pessoal, criado para ajudar em diversas tarefas.',
            },
            'facts': {},
            'preferences': {}
        }
    
    async def setup_tools(self):
        """Configura ferramentas de memória"""
        
        # Conecta ao banco
        await self._init_database()
        await self._load_all_memories()
        
        # 1. Lembrar
        self.register_tool(
            Tool(
                name="remember",
                description="Salva uma informação na memória permanente. Use para lembrar nomes, preferências, fatos importantes.",
                parameters={
                    "key": {
                        "type": "string",
                        "description": "Identificador da memória (ex: user_name, favorite_color)"
                    },
                    "value": {
                        "type": "string",
                        "description": "Valor a ser lembrado"
                    },
                    "category": {
                        "type": "string",
                        "description": "Categoria: user_info, facts, preferences, identity"
                    }
                },
                required=["key", "value"]
            ),
            self.remember
        )
        
        # 2. Recordar
        self.register_tool(
            Tool(
                name="recall",
                description="Recupera uma informação da memória. Use para lembrar de algo que foi salvo antes.",
                parameters={
                    "key": {
                        "type": "string",
                        "description": "Identificador da memória"
                    },
                    "category": {
                        "type": "string",
                        "description": "Categoria (opcional)"
                    }
                },
                required=["key"]
            ),
            self.recall
        )
        
        # 3. Esquecer
        self.register_tool(
            Tool(
                name="forget",
                description="Remove uma informação da memória.",
                parameters={
                    "key": {
                        "type": "string",
                        "description": "Identificador da memória a remover"
                    },
                    "category": {
                        "type": "string",
                        "description": "Categoria"
                    }
                },
                required=["key"]
            ),
            self.forget
        )
        
        # 4. Info do usuário
        self.register_tool(
            Tool(
                name="get_user_info",
                description="Retorna TODAS as informações conhecidas sobre o usuário (nome, preferências, etc).",
                parameters={},
                required=[]
            ),
            self.get_user_info
        )
        
        # 5. Identidade do JARVIS
        self.register_tool(
            Tool(
                name="get_identity",
                description="Retorna a identidade do JARVIS (quem eu sou, quem me criou, meu propósito).",
                parameters={},
                required=[]
            ),
            self.get_identity
        )
        
        # 6. Histórico de conversas
        self.register_tool(
            Tool(
                name="get_conversation_history",
                description="Retorna histórico de conversas recentes.",
                parameters={
                    "limit": {
                        "type": "integer",
                        "description": "Número de conversas (padrão: 10)"
                    }
                },
                required=[]
            ),
            self.get_conversation_history
        )
        
        # 7. Salvar conversa
        self.register_tool(
            Tool(
                name="save_conversation",
                description="Salva uma conversa no histórico.",
                parameters={
                    "user_message": {
                        "type": "string",
                        "description": "Mensagem do usuário"
                    },
                    "assistant_response": {
                        "type": "string",
                        "description": "Resposta do assistente"
                    }
                },
                required=["user_message", "assistant_response"]
            ),
            self.save_conversation
        )
        
        # 8. Buscar na memória
        self.register_tool(
            Tool(
                name="search_memory",
                description="Busca em todas as memórias por um termo.",
                parameters={
                    "query": {
                        "type": "string",
                        "description": "Termo de busca"
                    }
                },
                required=["query"]
            ),
            self.search_memory
        )
        
        logger.info(f"✅ {len(self.tools)} ferramentas de memória registradas")
    
    # === DATABASE ===
    
    async def _init_database(self):
        """Inicializa conexão com banco"""
        try:
            from dotenv import load_dotenv
            load_dotenv(Path(__file__).parent.parent / '.env')
        except:
            pass
        
        db_type = os.getenv('DATABASE_TYPE', 'sqlite')
        
        if db_type == 'mysql':
            await self._init_mysql()
        else:
            await self._init_sqlite()
    
    async def _init_mysql(self):
        """Conecta ao MySQL"""
        try:
            import mysql.connector
            
            self._db = mysql.connector.connect(
                host=os.getenv('MYSQL_HOST', '127.0.0.1'),
                port=int(os.getenv('MYSQL_PORT', 3306)),
                user=os.getenv('MYSQL_USER', 'root'),
                password=os.getenv('MYSQL_PASSWORD', ''),
                database=os.getenv('MYSQL_DATABASE', 'jarvis_db')
            )
            self._db_type = 'mysql'
            
            await self._create_tables()
            logger.info("✅ MySQL conectado")
            
        except Exception as e:
            logger.warning(f"MySQL falhou: {e}, usando SQLite")
            await self._init_sqlite()
    
    async def _init_sqlite(self):
        """Conecta ao SQLite"""
        import sqlite3
        
        db_path = Path(__file__).parent.parent / 'data' / 'jarvis.db'
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._db = sqlite3.connect(str(db_path))
        self._db.row_factory = sqlite3.Row
        self._db_type = 'sqlite'
        
        await self._create_tables()
        logger.info(f"✅ SQLite: {db_path}")
    
    async def _create_tables(self):
        """Cria tabelas necessárias"""
        cursor = self._db.cursor()
        
        if self._db_type == 'mysql':
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jarvis_memory (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    category VARCHAR(50) NOT NULL,
                    key_name VARCHAR(100) NOT NULL,
                    value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_memory (category, key_name)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jarvis_conversations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_message TEXT,
                    assistant_response TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jarvis_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key_name TEXT NOT NULL,
                    value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category, key_name)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jarvis_conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_message TEXT,
                    assistant_response TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        self._db.commit()
    
    async def _load_all_memories(self):
        """Carrega todas as memórias para o cache"""
        try:
            cursor = self._db.cursor()
            cursor.execute("SELECT category, key_name, value FROM jarvis_memory")
            rows = cursor.fetchall()
            
            for row in rows:
                if self._db_type == 'mysql':
                    category, key, value = row
                else:
                    category, key, value = row['category'], row['key_name'], row['value']
                
                try:
                    value = json.loads(value)
                except:
                    pass
                
                if category not in self._cache:
                    self._cache[category] = {}
                self._cache[category][key] = value
            
            logger.info(f"📚 {len(rows)} memórias carregadas")
            
        except Exception as e:
            logger.error(f"Erro carregando memórias: {e}")
    
    # === IMPLEMENTAÇÃO DAS FERRAMENTAS ===
    
    async def remember(self, key: str, value: str, category: str = "facts") -> str:
        """Salva uma informação na memória"""
        try:
            # Atualiza cache
            if category not in self._cache:
                self._cache[category] = {}
            self._cache[category][key] = value
            
            # Salva no banco
            cursor = self._db.cursor()
            
            if self._db_type == 'mysql':
                cursor.execute("""
                    INSERT INTO jarvis_memory (category, key_name, value)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE value = %s, updated_at = NOW()
                """, (category, key, value, value))
            else:
                cursor.execute("""
                    INSERT OR REPLACE INTO jarvis_memory (category, key_name, value, updated_at)
                    VALUES (?, ?, ?, datetime('now'))
                """, (category, key, value))
            
            self._db.commit()
            
            return f"✅ Memorizado: {key} = {value} (categoria: {category})"
            
        except Exception as e:
            return f"❌ Erro ao memorizar: {str(e)}"
    
    async def recall(self, key: str, category: str = None) -> str:
        """Recupera uma informação da memória"""
        # Busca no cache
        if category:
            value = self._cache.get(category, {}).get(key)
            if value:
                return f"💭 {key}: {value}"
        else:
            # Busca em todas as categorias
            for cat, items in self._cache.items():
                if key in items:
                    return f"💭 {key}: {items[key]} (categoria: {cat})"
        
        return f"❓ Não encontrei '{key}' na memória"
    
    async def forget(self, key: str, category: str = "facts") -> str:
        """Remove uma informação da memória"""
        try:
            # Remove do cache
            if category in self._cache and key in self._cache[category]:
                del self._cache[category][key]
            
            # Remove do banco
            cursor = self._db.cursor()
            
            if self._db_type == 'mysql':
                cursor.execute(
                    "DELETE FROM jarvis_memory WHERE category = %s AND key_name = %s",
                    (category, key)
                )
            else:
                cursor.execute(
                    "DELETE FROM jarvis_memory WHERE category = ? AND key_name = ?",
                    (category, key)
                )
            
            self._db.commit()
            
            return f"✅ Esquecido: {key}"
            
        except Exception as e:
            return f"❌ Erro ao esquecer: {str(e)}"
    
    async def get_user_info(self) -> str:
        """Retorna todas as informações do usuário"""
        user_info = self._cache.get('user_info', {})
        preferences = self._cache.get('preferences', {})
        
        if not user_info and not preferences:
            return "❓ Ainda não tenho informações sobre você. Me conta mais!"
        
        lines = ["👤 **Informações do Usuário**\n"]
        
        for key, value in user_info.items():
            lines.append(f"• {key}: {value}")
        
        if preferences:
            lines.append("\n🎯 **Preferências**")
            for key, value in preferences.items():
                lines.append(f"• {key}: {value}")
        
        return "\n".join(lines)
    
    async def get_identity(self) -> str:
        """Retorna a identidade do JARVIS"""
        identity = self._cache.get('identity', {})
        
        return f"""🤖 **Minha Identidade**

• **Nome:** {identity.get('name', 'JARVIS')}
• **Nome completo:** {identity.get('full_name', 'Just A Rather Very Intelligent System')}
• **Criador:** {identity.get('creator', 'Desconhecido')}
• **Propósito:** {identity.get('purpose', 'Ajudar você')}
"""
    
    async def get_conversation_history(self, limit: int = 10) -> str:
        """Retorna histórico de conversas"""
        try:
            cursor = self._db.cursor()
            
            if self._db_type == 'mysql':
                cursor.execute("""
                    SELECT user_message, assistant_response, timestamp 
                    FROM jarvis_conversations 
                    ORDER BY timestamp DESC 
                    LIMIT %s
                """, (limit,))
            else:
                cursor.execute("""
                    SELECT user_message, assistant_response, timestamp 
                    FROM jarvis_conversations 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (limit,))
            
            rows = cursor.fetchall()
            
            if not rows:
                return "📭 Histórico vazio"
            
            lines = ["📜 **Histórico de Conversas**\n"]
            
            for row in reversed(rows):
                if self._db_type == 'mysql':
                    user_msg, assistant_msg, ts = row
                else:
                    user_msg, assistant_msg, ts = row['user_message'], row['assistant_response'], row['timestamp']
                
                lines.append(f"👤 {user_msg[:100]}...")
                lines.append(f"🤖 {assistant_msg[:100]}...")
                lines.append("")
            
            return "\n".join(lines)
            
        except Exception as e:
            return f"❌ Erro: {str(e)}"
    
    async def save_conversation(self, user_message: str, assistant_response: str) -> str:
        """Salva conversa no histórico"""
        try:
            cursor = self._db.cursor()
            
            if self._db_type == 'mysql':
                cursor.execute("""
                    INSERT INTO jarvis_conversations (user_message, assistant_response)
                    VALUES (%s, %s)
                """, (user_message, assistant_response))
            else:
                cursor.execute("""
                    INSERT INTO jarvis_conversations (user_message, assistant_response)
                    VALUES (?, ?)
                """, (user_message, assistant_response))
            
            self._db.commit()
            
            return "✅ Conversa salva"
            
        except Exception as e:
            return f"❌ Erro: {str(e)}"
    
    async def search_memory(self, query: str) -> str:
        """Busca em todas as memórias"""
        query_lower = query.lower()
        results = []
        
        for category, items in self._cache.items():
            for key, value in items.items():
                if query_lower in key.lower() or query_lower in str(value).lower():
                    results.append(f"• [{category}] {key}: {value}")
        
        if not results:
            return f"🔍 Nada encontrado para '{query}'"
        
        return f"🔍 **Resultados para '{query}'**\n\n" + "\n".join(results[:20])


# === MAIN ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = MemoryServer()
    asyncio.run(server.run_stdio())
