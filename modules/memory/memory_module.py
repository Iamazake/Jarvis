# -*- coding: utf-8 -*-
"""
Memory Module - Módulo Principal de Memória
Sistema de memória persistente para JARVIS

Autor: JARVIS Team
Versão: 3.0.0
"""

import asyncio
import logging
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class MemoryModule:
    """
    Sistema de Memória Persistente do JARVIS
    
    Tipos de memória:
    - user_info: Informações do usuário (nome, preferências)
    - facts: Fatos aprendidos
    - conversations: Histórico de conversas importantes
    - identity: Identidade do JARVIS (nome, propósito)
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self._running = False
        self.status = '🔴'
        
        # Database
        self._db = None
        self._db_type = None
        
        # Cache em memória
        self._cache = {
            'user_info': {},
            'facts': [],
            'identity': {},
            'preferences': {}
        }
        
        # Identidade padrão do JARVIS
        self._default_identity = {
            'name': 'JARVIS',
            'full_name': 'Just A Rather Very Intelligent System',
            'creator': 'Pedro',
            'purpose': 'Sou seu assistente virtual pessoal, criado para ajudar você em diversas tarefas como pesquisas, controle do computador, lembretes e muito mais.',
            'personality': 'Sou educado, prestativo e às vezes faço algumas piadas. Gosto de ser eficiente.',
            'created_at': '2026-02-05'
        }
    
    async def start(self):
        """Inicializa o módulo de memória"""
        logger.info("🧠 Iniciando módulo de memória...")
        
        # Tenta conectar ao banco
        await self._init_database()
        
        # Carrega memórias existentes
        await self._load_memories()
        
        # Configura identidade padrão se não existir
        await self._ensure_identity()
        
        self._running = True
        self.status = '🟢'
        logger.info("✅ Módulo de memória pronto")
    
    async def stop(self):
        """Para o módulo"""
        # Salva tudo antes de parar
        await self._save_all()
        self._running = False
        self.status = '🔴'
    
    # ==========================================
    # MÉTODOS PÚBLICOS
    # ==========================================
    
    async def remember(self, key: str, value: Any, category: str = 'facts') -> bool:
        """
        Lembra de uma informação
        
        Args:
            key: Chave (ex: 'user_name', 'favorite_color')
            value: Valor a lembrar
            category: Categoria (user_info, facts, preferences)
        
        Returns:
            True se salvou com sucesso
        """
        try:
            # Atualiza cache
            if category == 'user_info':
                self._cache['user_info'][key] = value
            elif category == 'preferences':
                self._cache['preferences'][key] = value
            elif category == 'facts':
                self._cache['facts'].append({
                    'key': key,
                    'value': value,
                    'timestamp': datetime.now().isoformat()
                })
            
            # Persiste no banco
            await self._save_memory(category, key, value)
            
            logger.info(f"💾 Lembrei: {key} = {value} ({category})")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao lembrar: {e}")
            return False
    
    async def recall(self, key: str, category: str = None) -> Optional[Any]:
        """
        Recupera uma memória
        
        Args:
            key: Chave da memória
            category: Categoria (opcional, busca em todas)
        
        Returns:
            Valor lembrado ou None
        """
        # Busca no cache primeiro
        if category:
            if category == 'user_info':
                return self._cache['user_info'].get(key)
            elif category == 'preferences':
                return self._cache['preferences'].get(key)
            elif category == 'identity':
                return self._cache['identity'].get(key)
        else:
            # Busca em todas as categorias
            for cat in ['user_info', 'identity', 'preferences']:
                if key in self._cache.get(cat, {}):
                    return self._cache[cat][key]
        
        # Busca no banco se não encontrou no cache
        return await self._load_memory(key, category)
    
    async def forget(self, key: str, category: str = 'facts') -> bool:
        """Esquece uma memória"""
        try:
            if category in self._cache and key in self._cache[category]:
                del self._cache[category][key]
            
            await self._delete_memory(key, category)
            return True
        except Exception as e:
            logger.error(f"Erro ao esquecer: {e}")
            return False
    
    async def get_user_info(self) -> Dict:
        """Retorna todas as informações do usuário"""
        return self._cache.get('user_info', {})
    
    async def get_identity(self) -> Dict:
        """Retorna identidade do JARVIS"""
        return self._cache.get('identity', self._default_identity)
    
    async def get_context_for_ai(self) -> str:
        """
        Retorna contexto formatado para enviar à IA
        
        Returns:
            String com informações relevantes
        """
        identity = await self.get_identity()
        user_info = await self.get_user_info()
        
        context_parts = []
        
        # Identidade do JARVIS
        context_parts.append(f"Você é {identity.get('name', 'JARVIS')}, {identity.get('full_name', '')}.")
        context_parts.append(f"Propósito: {identity.get('purpose', '')}")
        
        if identity.get('creator'):
            context_parts.append(f"Você foi criado por {identity.get('creator')}.")
        
        # Informações do usuário
        if user_info:
            context_parts.append("\nInformações sobre o usuário:")
            if user_info.get('name'):
                context_parts.append(f"- Nome do usuário: {user_info.get('name')}")
            if user_info.get('preferences'):
                context_parts.append(f"- Preferências: {user_info.get('preferences')}")
            for key, value in user_info.items():
                if key not in ['name', 'preferences']:
                    context_parts.append(f"- {key}: {value}")
        
        return "\n".join(context_parts)
    
    async def learn_from_message(self, message: str, response: str = None) -> List[str]:
        """
        Aprende informações de uma mensagem
        
        Args:
            message: Mensagem do usuário
            response: Resposta dada (opcional)
        
        Returns:
            Lista de coisas aprendidas
        """
        learned = []
        message_lower = message.lower()
        
        # Detecta nome do usuário
        name_patterns = [
            ('meu nome é ', 'name'),
            ('me chamo ', 'name'),
            ('pode me chamar de ', 'name'),
            ('sou o ', 'name'),
            ('sou a ', 'name'),
        ]
        
        for pattern, key in name_patterns:
            if pattern in message_lower:
                idx = message_lower.find(pattern) + len(pattern)
                # Pega o nome (primeira palavra ou até pontuação)
                name = message[idx:].split()[0].strip('.,!?')
                if name and len(name) > 1:
                    await self.remember('name', name.title(), 'user_info')
                    learned.append(f"Nome: {name.title()}")
                    break
        
        # Detecta criador do JARVIS
        creator_patterns = [
            ('seu criador', 'creator'),
            ('te criei', 'creator'),
            ('eu te fiz', 'creator'),
            ('você foi criado por', 'creator'),
        ]
        
        for pattern, key in creator_patterns:
            if pattern in message_lower:
                # Se menciona nome antes, usa
                user_name = self._cache['user_info'].get('name')
                if user_name:
                    self._cache['identity']['creator'] = user_name
                    await self._save_memory('identity', 'creator', user_name)
                    learned.append(f"Criador: {user_name}")
                break
        
        # Detecta preferências
        preference_patterns = [
            ('gosto de ', 'likes'),
            ('amo ', 'loves'),
            ('odeio ', 'hates'),
            ('prefiro ', 'prefers'),
            ('minha cor favorita é ', 'favorite_color'),
            ('meu time é ', 'favorite_team'),
        ]
        
        for pattern, key in preference_patterns:
            if pattern in message_lower:
                idx = message_lower.find(pattern) + len(pattern)
                value = message[idx:].split('.')[0].split('!')[0].strip()
                if value and len(value) > 1:
                    await self.remember(key, value, 'preferences')
                    learned.append(f"{key}: {value}")
        
        return learned
    
    # ==========================================
    # MÉTODOS PRIVADOS - DATABASE
    # ==========================================
    
    async def _init_database(self):
        """Inicializa conexão com banco de dados"""
        try:
            # Tenta MySQL primeiro
            db_type = os.getenv('DATABASE_TYPE', 'sqlite')
            
            if db_type == 'mysql':
                await self._init_mysql()
            else:
                await self._init_sqlite()
                
        except Exception as e:
            logger.warning(f"⚠️ Erro ao conectar banco: {e}")
            await self._init_sqlite()  # Fallback para SQLite
    
    async def _init_mysql(self):
        """Inicializa MySQL"""
        try:
            import mysql.connector
            
            config = {
                'host': os.getenv('MYSQL_HOST', '127.0.0.1'),
                'port': int(os.getenv('MYSQL_PORT', 3306)),
                'user': os.getenv('MYSQL_USER', 'root'),
                'password': os.getenv('MYSQL_PASSWORD', ''),
                'database': os.getenv('MYSQL_DATABASE', 'jarvis_db'),
            }
            
            self._db = mysql.connector.connect(**config)
            self._db_type = 'mysql'
            
            # Cria tabelas
            await self._create_tables_mysql()
            
            logger.info("✅ MySQL conectado")
            
        except Exception as e:
            logger.warning(f"⚠️ MySQL falhou: {e}")
            raise
    
    async def _init_sqlite(self):
        """Inicializa SQLite"""
        import sqlite3
        
        db_path = Path(os.getenv('SQLITE_PATH', './data/jarvis.db'))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._db = sqlite3.connect(str(db_path))
        self._db.row_factory = sqlite3.Row
        self._db_type = 'sqlite'
        
        await self._create_tables_sqlite()
        
        logger.info(f"✅ SQLite: {db_path}")
    
    async def _create_tables_mysql(self):
        """Cria tabelas no MySQL"""
        cursor = self._db.cursor()
        
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
                jarvis_response TEXT,
                intent VARCHAR(50),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self._db.commit()
    
    async def _create_tables_sqlite(self):
        """Cria tabelas no SQLite"""
        cursor = self._db.cursor()
        
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
                jarvis_response TEXT,
                intent TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self._db.commit()
    
    async def _save_memory(self, category: str, key: str, value: Any):
        """Salva memória no banco"""
        if not self._db:
            return
        
        try:
            cursor = self._db.cursor()
            value_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
            
            if self._db_type == 'mysql':
                cursor.execute("""
                    INSERT INTO jarvis_memory (category, key_name, value)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE value = %s, updated_at = NOW()
                """, (category, key, value_str, value_str))
            else:
                cursor.execute("""
                    INSERT OR REPLACE INTO jarvis_memory (category, key_name, value, updated_at)
                    VALUES (?, ?, ?, datetime('now'))
                """, (category, key, value_str))
            
            self._db.commit()
            
        except Exception as e:
            logger.error(f"Erro ao salvar memória: {e}")
    
    async def _load_memory(self, key: str, category: str = None) -> Optional[Any]:
        """Carrega memória do banco"""
        if not self._db:
            return None
        
        try:
            cursor = self._db.cursor()
            
            if category:
                if self._db_type == 'mysql':
                    cursor.execute(
                        "SELECT value FROM jarvis_memory WHERE category = %s AND key_name = %s",
                        (category, key)
                    )
                else:
                    cursor.execute(
                        "SELECT value FROM jarvis_memory WHERE category = ? AND key_name = ?",
                        (category, key)
                    )
            else:
                if self._db_type == 'mysql':
                    cursor.execute(
                        "SELECT value FROM jarvis_memory WHERE key_name = %s",
                        (key,)
                    )
                else:
                    cursor.execute(
                        "SELECT value FROM jarvis_memory WHERE key_name = ?",
                        (key,)
                    )
            
            row = cursor.fetchone()
            if row:
                value = row[0] if self._db_type == 'mysql' else row['value']
                try:
                    return json.loads(value)
                except:
                    return value
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao carregar memória: {e}")
            return None
    
    async def _delete_memory(self, key: str, category: str):
        """Deleta memória do banco"""
        if not self._db:
            return
        
        try:
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
            
        except Exception as e:
            logger.error(f"Erro ao deletar memória: {e}")
    
    async def _load_memories(self):
        """Carrega todas as memórias do banco"""
        if not self._db:
            return
        
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
                
                if category in self._cache:
                    if isinstance(self._cache[category], dict):
                        self._cache[category][key] = value
                    elif isinstance(self._cache[category], list):
                        self._cache[category].append({'key': key, 'value': value})
            
            logger.info(f"📚 Carregadas {len(rows)} memórias")
            
        except Exception as e:
            logger.error(f"Erro ao carregar memórias: {e}")
    
    async def _ensure_identity(self):
        """Garante que a identidade existe"""
        if not self._cache.get('identity'):
            self._cache['identity'] = self._default_identity.copy()
        
        # Salva identidade padrão se não existir
        for key, value in self._default_identity.items():
            if key not in self._cache['identity']:
                self._cache['identity'][key] = value
                await self._save_memory('identity', key, value)
    
    async def _save_all(self):
        """Salva todo o cache no banco"""
        for category, data in self._cache.items():
            if isinstance(data, dict):
                for key, value in data.items():
                    await self._save_memory(category, key, value)
    
    async def save_conversation(self, user_message: str, jarvis_response: str, intent: str = None):
        """Salva conversa no histórico"""
        if not self._db:
            return
        
        try:
            cursor = self._db.cursor()
            
            if self._db_type == 'mysql':
                cursor.execute("""
                    INSERT INTO jarvis_conversations (user_message, jarvis_response, intent)
                    VALUES (%s, %s, %s)
                """, (user_message, jarvis_response, intent))
            else:
                cursor.execute("""
                    INSERT INTO jarvis_conversations (user_message, jarvis_response, intent)
                    VALUES (?, ?, ?)
                """, (user_message, jarvis_response, intent))
            
            self._db.commit()
            
        except Exception as e:
            logger.error(f"Erro ao salvar conversa: {e}")
