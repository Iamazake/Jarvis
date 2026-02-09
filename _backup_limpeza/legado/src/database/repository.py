# -*- coding: utf-8 -*-
"""
Database Repository - Repository Pattern
Abstração de banco de dados com suporte SQLite e MySQL

Autor: JARVIS Team
Versão: 4.0.0
"""

import sqlite3
import logging
from pathlib import Path
from enum import Enum
from typing import Optional, List, Dict, Any, Union
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Imports opcionais
try:
    import mysql.connector
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False


# Diretórios
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_DB = DATA_DIR / "jarvis.db"


class DatabaseType(Enum):
    """Tipos de banco de dados suportados"""
    SQLITE = "sqlite"
    MYSQL = "mysql"


class Database:
    """
    Repository Pattern - Abstração de banco de dados
    
    Singleton Pattern: Uma conexão por tipo
    
    Uso:
        db = Database()  # SQLite padrão
        db = Database(db_type=DatabaseType.MYSQL, config={...})
        
        results = db.query("SELECT * FROM users WHERE id = ?", (1,))
        db.execute("INSERT INTO users (name) VALUES (?)", ("John",))
    """
    
    _instances: Dict[str, 'Database'] = {}
    
    def __new__(cls, db_type: DatabaseType = None, **kwargs):
        """Singleton por tipo de banco"""
        key = str(db_type or DatabaseType.SQLITE)
        
        if key not in cls._instances:
            instance = super().__new__(cls)
            instance._initialized = False
            cls._instances[key] = instance
        
        return cls._instances[key]
    
    def __init__(self, 
                 db_type: DatabaseType = None,
                 db_path: Path = None,
                 mysql_config: Dict = None):
        """
        Inicializa o banco de dados
        
        Args:
            db_type: Tipo do banco (SQLITE ou MYSQL)
            db_path: Caminho do arquivo SQLite
            mysql_config: Configurações MySQL {host, user, password, database}
        """
        if self._initialized:
            return
        
        self.db_type = db_type or DatabaseType.SQLITE
        self.db_path = db_path or DEFAULT_DB
        self.mysql_config = mysql_config
        self._connection = None
        
        # Garantir diretório
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Tentar conectar
        if self.db_type == DatabaseType.MYSQL and HAS_MYSQL:
            if not self._connect_mysql():
                logger.warning("⚠️ MySQL falhou, usando SQLite")
                self.db_type = DatabaseType.SQLITE
        
        self._create_tables()
        self._initialized = True
        
        logger.info(f"✅ Database: {self.db_type.value}")
    
    @contextmanager
    def connection(self):
        """Context manager para conexão"""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            if self.db_type == DatabaseType.SQLITE:
                conn.close()
    
    def query(self, sql: str, params: tuple = None) -> List[Dict]:
        """
        Executa query e retorna resultados
        
        Args:
            sql: Query SQL (use ? para placeholders)
            params: Parâmetros da query
            
        Returns:
            Lista de dicionários
        """
        sql = self._adapt_sql(sql)
        
        with self.connection() as conn:
            cursor = self._get_cursor(conn)
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            rows = cursor.fetchall()
            
            if self.db_type == DatabaseType.SQLITE:
                return [dict(row) for row in rows]
            return rows
    
    def execute(self, sql: str, params: tuple = None) -> int:
        """
        Executa SQL e retorna lastrowid
        
        Args:
            sql: SQL (INSERT, UPDATE, DELETE)
            params: Parâmetros
            
        Returns:
            ID da última linha inserida
        """
        sql = self._adapt_sql(sql)
        
        with self.connection() as conn:
            cursor = self._get_cursor(conn)
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            return cursor.lastrowid
    
    def execute_many(self, sql: str, params_list: List[tuple]):
        """Executa SQL para múltiplos registros"""
        sql = self._adapt_sql(sql)
        
        with self.connection() as conn:
            cursor = self._get_cursor(conn)
            cursor.executemany(sql, params_list)
    
    # ========== Métodos de Conveniência ==========
    
    def save_conversation(self, 
                          session_id: str,
                          role: str,
                          content: str,
                          contact: str = None) -> int:
        """Salva mensagem de conversa"""
        return self.execute(
            """INSERT INTO conversations 
               (session_id, role, content, contact, created_at)
               VALUES (?, ?, ?, ?, datetime('now', 'localtime'))""",
            (session_id, role, content, contact)
        )
    
    def get_conversation_history(self, 
                                  session_id: str,
                                  limit: int = 20) -> List[Dict]:
        """Obtém histórico de conversa"""
        return self.query(
            """SELECT role, content, created_at 
               FROM conversations 
               WHERE session_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (session_id, limit)
        )
    
    def save_contact_profile(self, profile: Dict) -> int:
        """Salva perfil de contato"""
        return self.execute(
            """INSERT OR REPLACE INTO contact_profiles
               (phone, name, contact_type, tone, emoji_frequency, 
                formality, context, custom_instructions, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))""",
            (
                profile.get("phone", ""),
                profile.get("name", ""),
                profile.get("contact_type", "amigo"),
                profile.get("tone", "casual"),
                profile.get("emoji_frequency", "moderado"),
                profile.get("formality", "media"),
                profile.get("context", ""),
                profile.get("custom_instructions", ""),
            )
        )
    
    def get_contact_profile(self, identifier: str) -> Optional[Dict]:
        """Obtém perfil de contato"""
        rows = self.query(
            """SELECT * FROM contact_profiles 
               WHERE phone = ? OR name LIKE ?
               LIMIT 1""",
            (identifier, f"%{identifier}%")
        )
        return rows[0] if rows else None
    
    # ========== Métodos Privados ==========
    
    def _get_connection(self):
        """Obtém conexão com o banco"""
        if self.db_type == DatabaseType.MYSQL:
            return mysql.connector.connect(**self.mysql_config)
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _get_cursor(self, conn):
        """Obtém cursor apropriado"""
        if self.db_type == DatabaseType.MYSQL:
            return conn.cursor(dictionary=True)
        return conn.cursor()
    
    def _connect_mysql(self) -> bool:
        """Tenta conectar ao MySQL"""
        if not self.mysql_config:
            return False
        
        try:
            conn = mysql.connector.connect(**self.mysql_config)
            conn.close()
            return True
        except Exception as e:
            logger.error(f"❌ MySQL: {e}")
            return False
    
    def _adapt_sql(self, sql: str) -> str:
        """Adapta SQL para o banco atual"""
        if self.db_type == DatabaseType.MYSQL:
            # SQLite usa ?, MySQL usa %s
            sql = sql.replace("?", "%s")
            sql = sql.replace("datetime('now', 'localtime')", "NOW()")
            sql = sql.replace("INSERT OR REPLACE", "REPLACE")
        return sql
    
    def _create_tables(self):
        """Cria tabelas necessárias"""
        tables = [
            """CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                contact TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            
            """CREATE TABLE IF NOT EXISTS contact_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE,
                name TEXT NOT NULL,
                contact_type TEXT DEFAULT 'amigo',
                tone TEXT DEFAULT 'casual',
                emoji_frequency TEXT DEFAULT 'moderado',
                formality TEXT DEFAULT 'media',
                context TEXT,
                custom_instructions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            
            """CREATE TABLE IF NOT EXISTS monitored_contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact TEXT UNIQUE NOT NULL,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
        ]
        
        with self.connection() as conn:
            cursor = self._get_cursor(conn)
            for sql in tables:
                cursor.execute(self._adapt_sql(sql))
        
        logger.debug("📋 Tabelas verificadas")
