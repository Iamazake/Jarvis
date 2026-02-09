"""
Configurações centralizadas do JARVIS
Carrega variáveis de ambiente e define valores padrão
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Diretório base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
PLUGINS_DIR = BASE_DIR / "plugins"

# Criar diretórios necessários
for dir_path in [DATA_DIR, LOGS_DIR, PLUGINS_DIR]:
    dir_path.mkdir(exist_ok=True)


@dataclass
class JarvisSettings:
    """Configurações principais do JARVIS"""
    name: str = os.getenv("JARVIS_NAME", "Jarvis")
    wake_word: str = os.getenv("JARVIS_WAKE_WORD", "jarvis")
    language: str = os.getenv("JARVIS_LANGUAGE", "pt-BR")
    voice_speed: int = int(os.getenv("JARVIS_VOICE_SPEED", "180"))
    log_level: str = os.getenv("JARVIS_LOG_LEVEL", "INFO")


@dataclass
class AISettings:
    """Configurações de provedores de IA"""
    provider: str = os.getenv("AI_PROVIDER", "openai")
    
    # OpenAI
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
    
    # Anthropic
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    
    # Ollama
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2")


@dataclass
class WeatherSettings:
    """Configurações de clima"""
    api_key: Optional[str] = os.getenv("OPENWEATHER_API_KEY")
    city: str = os.getenv("WEATHER_CITY", "São Paulo")
    units: str = os.getenv("WEATHER_UNITS", "metric")


@dataclass
class NewsSettings:
    """Configurações de notícias"""
    api_key: Optional[str] = os.getenv("NEWS_API_KEY")
    country: str = os.getenv("NEWS_COUNTRY", "br")


@dataclass
class EmailSettings:
    """Configurações de email"""
    address: Optional[str] = os.getenv("EMAIL_ADDRESS")
    password: Optional[str] = os.getenv("EMAIL_PASSWORD")
    smtp_server: str = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("EMAIL_SMTP_PORT", "587"))


@dataclass
class SpotifySettings:
    """Configurações do Spotify"""
    client_id: Optional[str] = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret: Optional[str] = os.getenv("SPOTIFY_CLIENT_SECRET")


@dataclass
class PathSettings:
    """Configurações de caminhos do sistema"""
    downloads: Path = Path(os.getenv("DOWNLOADS_PATH", "~/Downloads")).expanduser()
    documents: Path = Path(os.getenv("DOCUMENTS_PATH", "~/Documents")).expanduser()
    pictures: Path = Path(os.getenv("PICTURES_PATH", "~/Pictures")).expanduser()
    videos: Path = Path(os.getenv("VIDEOS_PATH", "~/Videos")).expanduser()
    music: Path = Path(os.getenv("MUSIC_PATH", "~/Music")).expanduser()


@dataclass
class DatabaseSettings:
    """Configurações de banco de dados"""
    path: Path = Path(os.getenv("DATABASE_PATH", str(DATA_DIR / "jarvis.db")))


@dataclass
class WebSettings:
    """Configurações da interface web"""
    host: str = os.getenv("WEB_HOST", "127.0.0.1")
    port: int = int(os.getenv("WEB_PORT", "5000"))
    secret_key: str = os.getenv("WEB_SECRET_KEY", "jarvis-secret-key-change-me")


@dataclass
class SmartHomeSettings:
    """Configurações de casa inteligente"""
    homeassistant_url: Optional[str] = os.getenv("HOMEASSISTANT_URL")
    homeassistant_token: Optional[str] = os.getenv("HOMEASSISTANT_TOKEN")


@dataclass
class Config:
    """Configuração global do aplicativo"""
    jarvis: JarvisSettings = field(default_factory=JarvisSettings)
    ai: AISettings = field(default_factory=AISettings)
    weather: WeatherSettings = field(default_factory=WeatherSettings)
    news: NewsSettings = field(default_factory=NewsSettings)
    email: EmailSettings = field(default_factory=EmailSettings)
    spotify: SpotifySettings = field(default_factory=SpotifySettings)
    paths: PathSettings = field(default_factory=PathSettings)
    database: DatabaseSettings = field(default_factory=DatabaseSettings)
    web: WebSettings = field(default_factory=WebSettings)
    smart_home: SmartHomeSettings = field(default_factory=SmartHomeSettings)


# Instância global de configuração
config = Config()
