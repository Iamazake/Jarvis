# -*- coding: utf-8 -*-
"""
Módulo Database - Repository Pattern
Abstração de banco de dados SQLite/MySQL
"""

from .repository import Database, DatabaseType

__all__ = ['Database', 'DatabaseType']
