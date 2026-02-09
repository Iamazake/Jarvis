# -*- coding: utf-8 -*-
"""
Search MCP Server - Pesquisa Web e Informações
Integra DuckDuckGo, Wikipedia, Clima e mais

Autor: JARVIS Team
Versão: 3.0.0
"""

import os
import sys
import asyncio
import aiohttp
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_servers.base import MCPServer, Tool

logger = logging.getLogger(__name__)


class SearchServer(MCPServer):
    """
    MCP Server para pesquisas
    
    Ferramentas:
    - web_search: Pesquisa na web (DuckDuckGo)
    - wikipedia_search: Pesquisa na Wikipedia
    - get_weather: Clima atual
    - get_news: Notícias recentes
    - get_datetime: Data e hora atual
    """
    
    def __init__(self):
        super().__init__("jarvis-search", "3.0.0")
        self._load_env()
    
    def _load_env(self):
        """Carrega variáveis de ambiente"""
        try:
            from dotenv import load_dotenv
            load_dotenv(Path(__file__).parent.parent / '.env')
        except:
            pass
        
        self.weather_api_key = os.getenv('OPENWEATHER_API_KEY', '')
        self.default_city = os.getenv('WEATHER_CITY', 'São Paulo')
    
    async def setup_tools(self):
        """Configura ferramentas de pesquisa"""
        
        # 1. Pesquisa web
        self.register_tool(
            Tool(
                name="web_search",
                description="Pesquisa na internet usando DuckDuckGo. Use para buscar informações atualizadas.",
                parameters={
                    "query": {
                        "type": "string",
                        "description": "O que pesquisar"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Número máximo de resultados (padrão: 5)"
                    }
                },
                required=["query"]
            ),
            self.web_search
        )
        
        # 2. Wikipedia
        self.register_tool(
            Tool(
                name="wikipedia_search",
                description="Pesquisa na Wikipedia em português. Ótimo para definições e informações enciclopédicas.",
                parameters={
                    "query": {
                        "type": "string",
                        "description": "Termo a pesquisar"
                    },
                    "sentences": {
                        "type": "integer",
                        "description": "Número de frases do resumo (padrão: 3)"
                    }
                },
                required=["query"]
            ),
            self.wikipedia_search
        )
        
        # 3. Clima
        self.register_tool(
            Tool(
                name="get_weather",
                description="Retorna o clima atual de uma cidade.",
                parameters={
                    "city": {
                        "type": "string",
                        "description": "Nome da cidade (padrão: São Paulo)"
                    }
                },
                required=[]
            ),
            self.get_weather
        )
        
        # 4. Data e hora
        self.register_tool(
            Tool(
                name="get_datetime",
                description="Retorna a data e hora atual.",
                parameters={
                    "format": {
                        "type": "string",
                        "description": "Formato: full, date, time, weekday"
                    }
                },
                required=[]
            ),
            self.get_datetime
        )
        
        # 5. Calculadora
        self.register_tool(
            Tool(
                name="calculate",
                description="Calcula expressões matemáticas. Ex: 2+2, sqrt(16), sin(45)",
                parameters={
                    "expression": {
                        "type": "string",
                        "description": "Expressão matemática"
                    }
                },
                required=["expression"]
            ),
            self.calculate
        )
        
        logger.info(f"✅ {len(self.tools)} ferramentas de pesquisa registradas")
    
    # === IMPLEMENTAÇÃO DAS FERRAMENTAS ===
    
    async def web_search(self, query: str, max_results: int = 5) -> str:
        """Pesquisa na web"""
        try:
            from duckduckgo_search import DDGS
            
            results = []
            
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        'title': r.get('title', ''),
                        'body': r.get('body', ''),
                        'href': r.get('href', '')
                    })
            
            if not results:
                return f"🔍 Nenhum resultado encontrado para '{query}'"
            
            lines = [f"🔍 **Pesquisa: {query}**\n"]
            
            for i, r in enumerate(results, 1):
                lines.append(f"**{i}. {r['title']}**")
                lines.append(f"   {r['body'][:200]}...")
                lines.append(f"   🔗 {r['href']}\n")
            
            return "\n".join(lines)
            
        except ImportError:
            return "❌ duckduckgo-search não instalado"
        except Exception as e:
            return f"❌ Erro na pesquisa: {str(e)}"
    
    async def wikipedia_search(self, query: str, sentences: int = 3) -> str:
        """Pesquisa na Wikipedia"""
        try:
            import wikipedia
            wikipedia.set_lang('pt')
            
            try:
                summary = wikipedia.summary(query, sentences=sentences)
                page = wikipedia.page(query)
                
                return f"""📚 **Wikipedia: {page.title}**

{summary}

🔗 {page.url}"""
                
            except wikipedia.DisambiguationError as e:
                options = e.options[:5]
                return f"🔀 Múltiplos resultados para '{query}':\n• " + "\n• ".join(options)
                
            except wikipedia.PageError:
                # Tenta buscar
                results = wikipedia.search(query, results=5)
                if results:
                    return f"❓ '{query}' não encontrado. Sugestões:\n• " + "\n• ".join(results)
                return f"❓ Nenhum artigo encontrado para '{query}'"
                
        except ImportError:
            return "❌ wikipedia não instalado"
        except Exception as e:
            return f"❌ Erro: {str(e)}"
    
    async def get_weather(self, city: str = None) -> str:
        """Retorna clima atual"""
        city = city or self.default_city
        
        if not self.weather_api_key:
            return "❌ OPENWEATHER_API_KEY não configurada"
        
        try:
            url = "http://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': city,
                'appid': self.weather_api_key,
                'units': 'metric',
                'lang': 'pt_br'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        return f"❌ Cidade não encontrada: {city}"
                    
                    data = await resp.json()
            
            temp = data['main']['temp']
            feels_like = data['main']['feels_like']
            humidity = data['main']['humidity']
            description = data['weather'][0]['description'].capitalize()
            
            # Ícone baseado na condição
            icons = {
                'clear': '☀️',
                'clouds': '☁️',
                'rain': '🌧️',
                'drizzle': '🌦️',
                'thunderstorm': '⛈️',
                'snow': '❄️',
                'mist': '🌫️',
                'fog': '🌫️'
            }
            
            weather_main = data['weather'][0]['main'].lower()
            icon = icons.get(weather_main, '🌤️')
            
            return f"""{icon} **Clima em {city}**

🌡️ Temperatura: {temp:.1f}°C
🤒 Sensação: {feels_like:.1f}°C
💧 Umidade: {humidity}%
📝 {description}"""
            
        except Exception as e:
            return f"❌ Erro ao buscar clima: {str(e)}"
    
    async def get_datetime(self, format: str = "full") -> str:
        """Retorna data e hora"""
        now = datetime.now()
        
        weekdays = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
        months = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        
        weekday = weekdays[now.weekday()]
        month = months[now.month - 1]
        
        if format == "date":
            return f"📅 {now.day} de {month} de {now.year}"
        elif format == "time":
            return f"🕐 {now.strftime('%H:%M:%S')}"
        elif format == "weekday":
            return f"📆 {weekday}"
        else:  # full
            return f"""📅 **Data e Hora**

• Data: {weekday}, {now.day} de {month} de {now.year}
• Hora: {now.strftime('%H:%M:%S')}
• Semana do ano: {now.isocalendar()[1]}"""
    
    async def calculate(self, expression: str) -> str:
        """Calcula expressões matemáticas"""
        import math
        
        # Funções permitidas
        allowed = {
            'abs': abs, 'round': round, 'min': min, 'max': max,
            'sum': sum, 'pow': pow, 'sqrt': math.sqrt,
            'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
            'log': math.log, 'log10': math.log10,
            'pi': math.pi, 'e': math.e,
            'floor': math.floor, 'ceil': math.ceil
        }
        
        # Limpa expressão
        expr = expression.replace('^', '**')
        
        try:
            result = eval(expr, {"__builtins__": {}}, allowed)
            return f"🔢 {expression} = **{result}**"
        except Exception as e:
            return f"❌ Erro no cálculo: {str(e)}"


# === MAIN ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = SearchServer()
    asyncio.run(server.run_stdio())
