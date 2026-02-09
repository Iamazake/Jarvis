# -*- coding: utf-8 -*-
"""
Search Module - Módulo Principal de Pesquisa
Integra várias fontes de pesquisa

Autor: JARVIS Team
Versão: 3.0.0
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SearchModule:
    """
    Módulo de pesquisa inteligente
    
    Funcionalidades:
    - Pesquisa web (DuckDuckGo, Brave, Google)
    - Pesquisa profunda (Tavily, Perplexity)
    - Wikipedia para fatos rápidos
    - Notícias
    - Clima
    """
    
    def __init__(self, config):
        self.config = config
        self._running = False
        
        # Componentes
        self.web_search = None
        self.wikipedia = None
        self.weather = None
        self.news = None
        
        self.status = '🔴'
    
    async def start(self):
        """Inicializa componentes de pesquisa"""
        logger.info("🔍 Iniciando módulo de pesquisa...")
        
        try:
            from .web_search import WebSearch
            self.web_search = WebSearch(self.config)
            logger.info("  ✅ Web Search inicializado")
        except Exception as e:
            logger.warning(f"  ⚠️ Web Search: {e}")
        
        try:
            from .wikipedia import WikipediaSearch
            self.wikipedia = WikipediaSearch(language='pt')
            logger.info("  ✅ Wikipedia inicializado")
        except Exception as e:
            logger.warning(f"  ⚠️ Wikipedia: {e}")
        
        self._running = True
        self.status = '🟢'
        logger.info("✅ Módulo de pesquisa pronto")
    
    async def stop(self):
        """Para o módulo"""
        self._running = False
        self.status = '🔴'
    
    async def process(self, message: str, intent, context: Dict, metadata: Dict) -> str:
        """
        Processa comandos de pesquisa
        
        Args:
            message: Mensagem do usuário
            intent: Intenção classificada
            context: Contexto da conversa
            metadata: Dados extras
        
        Returns:
            Resultado da pesquisa formatado
        """
        intent_type = intent.type if hasattr(intent, 'type') else str(intent)
        entities = intent.entities if hasattr(intent, 'entities') else {}
        
        # Determina o tipo de pesquisa
        if intent_type == 'weather':
            return await self._search_weather()
        
        elif intent_type == 'news':
            topic = entities.get('query', '')
            return await self._search_news(topic)
        
        else:
            # Pesquisa geral
            query = entities.get('query') or message
            return await self.search(query)
    
    async def search(self, query: str, num_results: int = 5) -> str:
        """
        Realiza pesquisa geral
        
        Args:
            query: Termo de pesquisa
            num_results: Número de resultados
        
        Returns:
            Resultado formatado
        """
        results = []
        
        # Tenta Wikipedia primeiro para fatos rápidos
        if self.wikipedia:
            try:
                wiki_result = await self.wikipedia.search(query)
                if wiki_result:
                    results.append(("📚 Wikipedia", wiki_result))
            except Exception as e:
                logger.debug(f"Erro Wikipedia: {e}")
        
        # Pesquisa web
        if self.web_search:
            try:
                web_results = await self.web_search.search(query, num_results)
                if web_results:
                    results.append(("🌐 Web", web_results))
            except Exception as e:
                logger.debug(f"Erro Web Search: {e}")
        
        # Formata resultado
        if not results:
            return f"Desculpe, não encontrei resultados para '{query}'."
        
        response = f"🔍 **Pesquisa: {query}**\n\n"
        
        for source, content in results:
            response += f"{source}:\n{content}\n\n"
        
        return response.strip()
    
    async def _search_weather(self) -> str:
        """Busca previsão do tempo"""
        api_key = self.config.get('OPENWEATHER_API_KEY')
        city = self.config.get('WEATHER_CITY', 'São Paulo')
        
        if not api_key or api_key == 'sua_chave_aqui':
            return "⚠️ API de clima não configurada. Configure OPENWEATHER_API_KEY no .env"
        
        try:
            import aiohttp
            
            url = f"http://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': city,
                'appid': api_key,
                'units': 'metric',
                'lang': 'pt_br'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        temp = data['main']['temp']
                        feels_like = data['main']['feels_like']
                        humidity = data['main']['humidity']
                        description = data['weather'][0]['description']
                        
                        return (
                            f"☁️ **Clima em {city}**\n\n"
                            f"🌡️ Temperatura: {temp:.1f}°C\n"
                            f"🤒 Sensação: {feels_like:.1f}°C\n"
                            f"💧 Umidade: {humidity}%\n"
                            f"📝 {description.capitalize()}"
                        )
                    else:
                        return f"Erro ao buscar clima: {resp.status}"
                        
        except ImportError:
            return "⚠️ Instale aiohttp: pip install aiohttp"
        except Exception as e:
            logger.error(f"Erro buscando clima: {e}")
            return f"Erro ao buscar clima: {str(e)}"
    
    async def _search_news(self, topic: str = "") -> str:
        """Busca notícias"""
        api_key = self.config.get('NEWS_API_KEY')
        
        if not api_key or api_key == 'sua_chave_aqui':
            # Fallback para busca web
            query = f"notícias {topic}" if topic else "notícias brasil hoje"
            return await self.search(query, 5)
        
        try:
            import aiohttp
            
            url = "https://newsapi.org/v2/top-headlines"
            params = {
                'apiKey': api_key,
                'country': 'br',
                'pageSize': 5
            }
            
            if topic:
                params['q'] = topic
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        articles = data.get('articles', [])
                        
                        if not articles:
                            return "Nenhuma notícia encontrada."
                        
                        response = f"📰 **Notícias{' sobre ' + topic if topic else ''}**\n\n"
                        
                        for i, article in enumerate(articles[:5], 1):
                            title = article.get('title', 'Sem título')
                            source = article.get('source', {}).get('name', 'Desconhecido')
                            response += f"{i}. **{title}**\n   _Fonte: {source}_\n\n"
                        
                        return response.strip()
                    else:
                        return f"Erro ao buscar notícias: {resp.status}"
                        
        except ImportError:
            return "⚠️ Instale aiohttp: pip install aiohttp"
        except Exception as e:
            logger.error(f"Erro buscando notícias: {e}")
            return f"Erro ao buscar notícias: {str(e)}"
    
    def is_available(self) -> bool:
        """Verifica se módulo está disponível"""
        return self._running
