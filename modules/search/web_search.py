# -*- coding: utf-8 -*-
"""
Web Search - Pesquisa na Web
Usa DuckDuckGo (gratuito) ou APIs pagas (Tavily, Brave)
"""

import asyncio
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class WebSearch:
    """
    Pesquisa na web usando múltiplas fontes
    
    Ordem de prioridade:
    1. Tavily (melhor para IA, pago)
    2. Brave Search (bom e barato)
    3. DuckDuckGo (gratuito)
    """
    
    def __init__(self, config):
        self.config = config
        self._tavily_key = config.get('TAVILY_API_KEY')
        self._brave_key = config.get('BRAVE_API_KEY')
    
    async def search(self, query: str, num_results: int = 5) -> str:
        """
        Realiza pesquisa web
        
        Args:
            query: Termo de pesquisa
            num_results: Número máximo de resultados
        
        Returns:
            Resultados formatados em string
        """
        # Tenta Tavily primeiro (melhor para contexto de IA)
        if self._tavily_key and self._tavily_key != 'sua_chave_aqui':
            try:
                return await self._search_tavily(query, num_results)
            except Exception as e:
                logger.debug(f"Tavily falhou: {e}")
        
        # Tenta Brave Search
        if self._brave_key and self._brave_key != 'sua_chave_aqui':
            try:
                return await self._search_brave(query, num_results)
            except Exception as e:
                logger.debug(f"Brave falhou: {e}")
        
        # Fallback: DuckDuckGo (gratuito)
        try:
            return await self._search_duckduckgo(query, num_results)
        except Exception as e:
            logger.error(f"DuckDuckGo falhou: {e}")
            return None
    
    async def _search_tavily(self, query: str, num_results: int) -> str:
        """Pesquisa usando Tavily (otimizado para IA)"""
        try:
            from tavily import TavilyClient
            
            client = TavilyClient(api_key=self._tavily_key)
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.search(
                    query=query,
                    search_depth="basic",
                    max_results=num_results
                )
            )
            
            results = response.get('results', [])
            
            if not results:
                return None
            
            # Formata resultados
            formatted = []
            for r in results[:num_results]:
                title = r.get('title', 'Sem título')
                content = r.get('content', '')[:200]
                url = r.get('url', '')
                formatted.append(f"• **{title}**\n  {content}...\n  🔗 {url}")
            
            return '\n\n'.join(formatted)
            
        except ImportError:
            raise ImportError("Instale tavily-python: pip install tavily-python")
    
    async def _search_brave(self, query: str, num_results: int) -> str:
        """Pesquisa usando Brave Search"""
        import aiohttp
        
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            'X-Subscription-Token': self._brave_key,
            'Accept': 'application/json'
        }
        params = {
            'q': query,
            'count': num_results
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get('web', {}).get('results', [])
                    
                    if not results:
                        return None
                    
                    formatted = []
                    for r in results[:num_results]:
                        title = r.get('title', 'Sem título')
                        description = r.get('description', '')[:200]
                        url = r.get('url', '')
                        formatted.append(f"• **{title}**\n  {description}\n  🔗 {url}")
                    
                    return '\n\n'.join(formatted)
                else:
                    raise Exception(f"Brave API error: {resp.status}")
    
    async def _search_duckduckgo(self, query: str, num_results: int) -> str:
        """Pesquisa usando DuckDuckGo (gratuito)"""
        try:
            from duckduckgo_search import DDGS
            
            loop = asyncio.get_event_loop()
            
            def _search():
                with DDGS() as ddgs:
                    results = list(ddgs.text(
                        query,
                        region='br-pt',
                        safesearch='moderate',
                        max_results=num_results
                    ))
                return results
            
            results = await loop.run_in_executor(None, _search)
            
            if not results:
                return None
            
            formatted = []
            for r in results[:num_results]:
                title = r.get('title', 'Sem título')
                body = r.get('body', '')[:200]
                url = r.get('href', '')
                formatted.append(f"• **{title}**\n  {body}\n  🔗 {url}")
            
            return '\n\n'.join(formatted)
            
        except ImportError:
            raise ImportError("Instale duckduckgo-search: pip install duckduckgo-search")
    
    async def search_deep(self, query: str) -> str:
        """
        Pesquisa profunda com contexto expandido
        Usa Tavily com search_depth="advanced"
        """
        if not self._tavily_key or self._tavily_key == 'sua_chave_aqui':
            # Fallback para pesquisa normal com mais resultados
            return await self.search(query, num_results=10)
        
        try:
            from tavily import TavilyClient
            
            client = TavilyClient(api_key=self._tavily_key)
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.search(
                    query=query,
                    search_depth="advanced",
                    max_results=10,
                    include_answer=True
                )
            )
            
            # Tavily pode retornar uma resposta direta
            answer = response.get('answer')
            results = response.get('results', [])
            
            output = []
            
            if answer:
                output.append(f"**Resposta:**\n{answer}\n")
            
            if results:
                output.append("**Fontes:**")
                for r in results[:5]:
                    title = r.get('title', '')
                    url = r.get('url', '')
                    output.append(f"• {title}\n  🔗 {url}")
            
            return '\n'.join(output)
            
        except Exception as e:
            logger.error(f"Erro em pesquisa profunda: {e}")
            return await self.search(query, num_results=10)
