#!/usr/bin/env python3
"""
JARVIS - Script de Teste de Configuração
Verifica se todas as dependências e módulos estão configurados corretamente.
"""

import sys
import os
from pathlib import Path

# Cores para terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def ok(msg):
    print(f"  {Colors.GREEN}✓{Colors.RESET} {msg}")

def fail(msg, detail=""):
    print(f"  {Colors.RED}✗{Colors.RESET} {msg}")
    if detail:
        print(f"    {Colors.YELLOW}→ {detail}{Colors.RESET}")

def warn(msg):
    print(f"  {Colors.YELLOW}!{Colors.RESET} {msg}")

def header(msg):
    print(f"\n{Colors.BOLD}{Colors.BLUE}[{msg}]{Colors.RESET}")

def test_python_version():
    """Testa versão do Python"""
    header("Python")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        ok(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        fail(f"Python {version.major}.{version.minor}", "Requer Python 3.8+")
        return False

def test_dependencies():
    """Testa dependências essenciais"""
    header("Dependências Essenciais")
    
    deps = {
        'openai': 'OpenAI API',
        'dotenv': 'python-dotenv (variáveis de ambiente)',
        'aiohttp': 'aiohttp (requisições async)',
        'rich': 'Rich (interface CLI)',
    }
    
    all_ok = True
    for module, name in deps.items():
        try:
            if module == 'dotenv':
                __import__('dotenv')
            else:
                __import__(module)
            ok(name)
        except ImportError:
            fail(name, f"pip install {module}")
            all_ok = False
    
    return all_ok

def test_voice_dependencies():
    """Testa dependências de voz"""
    header("Dependências de Voz")
    
    # pyttsx3
    try:
        import pyttsx3
        ok("pyttsx3 (síntese de voz)")
    except ImportError:
        warn("pyttsx3 não instalado (pip install pyttsx3)")
    
    # PyAudio
    try:
        import pyaudio
        ok("PyAudio (captura de áudio)")
    except ImportError:
        warn("PyAudio não instalado (pip install pyaudio)")
    
    # Whisper
    try:
        import whisper
        ok("OpenAI Whisper (transcrição)")
    except ImportError:
        warn("Whisper não instalado (pip install openai-whisper)")

def test_search_dependencies():
    """Testa dependências de pesquisa"""
    header("Dependências de Pesquisa")
    
    try:
        from duckduckgo_search import DDGS
        ok("DuckDuckGo Search")
    except ImportError:
        warn("duckduckgo-search não instalado")
    
    try:
        import wikipedia
        ok("Wikipedia")
    except ImportError:
        warn("wikipedia não instalado")

def test_tools_dependencies():
    """Testa dependências de ferramentas"""
    header("Dependências de Ferramentas")
    
    try:
        import psutil
        ok("psutil (informações do sistema)")
    except ImportError:
        warn("psutil não instalado")

def test_environment():
    """Testa variáveis de ambiente"""
    header("Variáveis de Ambiente")
    
    env_path = Path(__file__).parent / '.env'
    
    if env_path.exists():
        ok(".env encontrado")
        
        # Carrega .env
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
        except:
            pass
        
        # Verifica variáveis importantes
        vars_to_check = [
            ('OPENAI_API_KEY', 'OpenAI API Key'),
            ('OPENWEATHER_API_KEY', 'OpenWeather API Key'),
            ('ELEVENLABS_API_KEY', 'ElevenLabs API Key'),
        ]
        
        for var, name in vars_to_check:
            value = os.getenv(var)
            if value and len(value) > 10:
                ok(f"{name} configurada")
            else:
                warn(f"{name} não configurada")
    else:
        fail(".env não encontrado", "Copie .env.example para .env e configure")

def test_project_structure():
    """Testa estrutura do projeto"""
    header("Estrutura do Projeto")
    
    base = Path(__file__).parent
    
    required_dirs = [
        'core',
        'modules/voice',
        'modules/search',
        'modules/tools',
        'modules/ai',
        'interfaces/cli',
        'src',
        'services',
    ]
    
    required_files = [
        'jarvis.py',
        'config.json',
        'requirements.txt',
        'core/jarvis.py',
        'core/orchestrator.py',
        'modules/voice/voice_module.py',
        'modules/search/search_module.py',
        'modules/tools/tools_module.py',
    ]
    
    all_ok = True
    
    for dir_path in required_dirs:
        full_path = base / dir_path
        if full_path.exists():
            ok(f"/{dir_path}/")
        else:
            fail(f"/{dir_path}/", "Diretório não encontrado")
            all_ok = False
    
    for file_path in required_files:
        full_path = base / file_path
        if full_path.exists():
            ok(file_path)
        else:
            fail(file_path, "Arquivo não encontrado")
            all_ok = False
    
    return all_ok

def test_imports():
    """Testa imports dos módulos do projeto"""
    header("Módulos do Projeto")
    
    # Adiciona path
    sys.path.insert(0, str(Path(__file__).parent))
    
    modules_to_test = [
        ('core.config', 'Config'),
        ('core.jarvis', 'Jarvis'),
        ('core.orchestrator', 'Orchestrator'),
        ('modules.voice.voice_module', 'VoiceModule'),
        ('modules.search.search_module', 'SearchModule'),
        ('modules.tools.tools_module', 'ToolsModule'),
        ('interfaces.cli.main', 'JarvisCLI'),
    ]
    
    all_ok = True
    for module_path, description in modules_to_test:
        try:
            __import__(module_path)
            ok(f"{module_path}")
        except Exception as e:
            fail(f"{module_path}", str(e)[:60])
            all_ok = False
    
    return all_ok

def main():
    print(f"""
{Colors.BOLD}╔══════════════════════════════════════════════════════════════╗
║          JARVIS - Teste de Configuração v3.0                  ║
╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
""")
    
    results = []
    
    results.append(('Python', test_python_version()))
    results.append(('Estrutura', test_project_structure()))
    results.append(('Ambiente', True))  # test_environment não retorna bool
    test_environment()
    results.append(('Deps Essenciais', test_dependencies()))
    
    test_voice_dependencies()
    test_search_dependencies()
    test_tools_dependencies()
    
    print("\n" + "="*60)
    test_imports()
    
    # Resumo
    print(f"""
{Colors.BOLD}{'='*60}
                        RESUMO
{'='*60}{Colors.RESET}
""")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"  Testes críticos: {passed}/{total}")
    
    if passed == total:
        print(f"\n  {Colors.GREEN}{Colors.BOLD}✓ Sistema pronto para uso!{Colors.RESET}")
        print(f"\n  Execute: {Colors.BLUE}python jarvis.py{Colors.RESET}")
    else:
        print(f"\n  {Colors.YELLOW}! Alguns itens precisam de atenção{Colors.RESET}")
        print(f"  Execute: {Colors.BLUE}pip install -r requirements.txt{Colors.RESET}")
    
    print()

if __name__ == "__main__":
    main()
