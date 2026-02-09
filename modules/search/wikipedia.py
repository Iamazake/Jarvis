# -*- coding: utf-8 -*-
"""
Wikipedia Search - Busca rápida de fatos
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class WikipediaSearch:
    """
    Busca informações na Wikipedia
    
    Útil para:
    - Fatos rápidos
    - Definições
    - Informações sobre pessoas, lugares, eventos
    """
    
    def __init__(self, language: str = 'pt'):
        self.language = language
        self._wiki = None
        
        self._initialize()
    
    def _initialize(self):
        """Inicializa cliente Wikipedia"""
        try:
            import wikipedia
            wikipedia.set_lang(self.language)
            self._wiki = wikipedia
            logger.debug("Wikipedia inicializado")
        except ImportError:
            logger.warning("wikipedia não instalado: pip install wikipedia")
    
    async def search(self, query: str, sentences: int = 3) -> Optional[str]:
        """
        Busca resumo na Wikipedia
        
        Args:
            query: Termo de pesquisa
            sentences: Número de sentenças no resumo
        
        Returns:
            Resumo ou None se não encontrado
        """
        if not self._wiki:
            return None
        
        loop = asyncio.get_event_loop()
        
        try:
            # Busca na Wikipedia
            summary = await loop.run_in_executor(
                None,
                lambda: self._wiki.summary(query, sentences=sentences)
            )
            
            return summary
            
        except self._wiki.exceptions.DisambiguationError as e:
            # Múltiplas opções - tenta a primeira
            try:
                summary = await loop.run_in_executor(
                    None,
                    lambda: self._wiki.summary(e.options[0], sentences=sentences)
                )
                return summary
            except:
                return None
                
        except self._wiki.exceptions.PageError:
            # Página não encontrada
            return None
            
        except Exception as e:
            logger.debug(f"Erro Wikipedia: {e}")
            return None
    
    async def get_page(self, title: str) -> Optional[dict]:
        """
        Obtém página completa da Wikipedia
        
        Returns:
            Dict com title, summary, content, url
        """
        if not self._wiki:
            return None
        
        loop = asyncio.get_event_loop()
        
        try:
            page = await loop.run_in_executor(
                None,
                lambda: self._wiki.page(title)
            )
            
            return {
                'title': page.title,
                'summary': page.summary,
                'content': page.content[:2000],  # Limita tamanho
                'url': page.url
            }
            
        except Exception as e:
            logger.debug(f"Erro ao obter página: {e}")
            return None
    
    async def suggest(self, query: str) -> list:
        """
        Sugere termos de pesquisa
        
        Returns:
            Lista de sugestões
        """
        if not self._wiki:
            return []
        
        loop = asyncio.get_event_loop()
        
        try:
            suggestions = await loop.run_in_executor(
                None,
                lambda: self._wiki.search(query, results=5)
            )
            return suggestions
            
        except Exception as e:
            logger.debug(f"Erro em sugestões: {e}")
            return []
