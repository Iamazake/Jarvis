#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JARVIS - Entry Point Principal com MCP
Assistente Virtual Inteligente com Ferramentas Autônomas

Autor: JARVIS Team
Versão: 3.0.0

Uso:
    python jarvis.py              # Inicia CLI interativo
    python jarvis.py --voice      # Inicia com modo de voz
    python jarvis.py "comando"    # Executa comando único
    python jarvis.py --mcp        # Usa sistema MCP (novo!)
"""

import sys
import os
import asyncio
import argparse
import logging
from pathlib import Path

# Adiciona diretório ao path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# Carrega .env
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    pass

# Configuração de logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Reduz logging verboso
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('openai').setLevel(logging.WARNING)


async def main():
    """Função principal"""
    parser = argparse.ArgumentParser(
        description='🤖 JARVIS - Assistente Virtual Inteligente',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Exemplos:
    python jarvis.py                    # Inicia CLI com MCP (padrão)
    python jarvis.py --legado           # Inicia com Orchestrator/WhatsApp/autopilot
    python jarvis.py --voice            # Inicia com modo de voz
    python jarvis.py "pesquisa python"  # Executa comando único
    python jarvis.py --status           # Mostra status do sistema
        '''
    )
    
    parser.add_argument('command', nargs='?', help='Comando para executar')
    parser.add_argument('-v', '--voice', action='store_true', help='Ativa modo de voz')
    parser.add_argument('-s', '--status', action='store_true', help='Mostra status')
    parser.add_argument('-d', '--debug', action='store_true', help='Modo debug')
    parser.add_argument('-m', '--mcp', action='store_true', help='Usa sistema MCP (já é o padrão)')
    parser.add_argument('-l', '--legado', action='store_true', help='Usa sistema legado (Orchestrator + intents WhatsApp/autopilot)')
    parser.add_argument('--no-color', action='store_true', help='Desativa cores')
    
    args = parser.parse_args()
    
    # Configura nível de log
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Padrão = MCP. Use --legado para o fluxo com Orchestrator/WhatsApp/autopilot.
    use_legado = args.legado
    use_mcp = args.mcp or (not use_legado)
    if use_mcp:
        await run_mcp_mode(args)
        return
    
    # Sistema legado (Orchestrator, intent classifier, módulos WhatsApp, autopilot)
    from core.jarvis import Jarvis
    
    # Cria instância
    jarvis = Jarvis()
    
    try:
        # Inicia JARVIS
        await jarvis.start()
        
        if args.status:
            # Mostra status e sai
            print_status(jarvis)
            return
        
        if args.command:
            # Executa comando único
            response = await jarvis.process(args.command)
            print(f"\n🤖 {response}\n")
            return
        
        # Modo interativo
        if args.voice:
            await run_voice_mode(jarvis)
        else:
            await run_cli_mode(jarvis)
            
    except KeyboardInterrupt:
        print("\n\n👋 Até logo!")
    finally:
        await jarvis.stop()


async def run_cli_mode(jarvis):
    """Executa modo CLI interativo"""
    from interfaces.cli.main import JarvisCLI
    
    cli = JarvisCLI(jarvis)
    await cli.run()


async def run_voice_mode(jarvis):
    """Executa modo de voz"""
    from interfaces.cli.main import JarvisCLI
    
    cli = JarvisCLI(jarvis)
    await cli.run_with_voice()


async def run_mcp_mode(args):
    """
    Executa JARVIS com sistema MCP (Model Context Protocol)
    
    Novo sistema onde a IA escolhe ferramentas automaticamente.
    """
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║       ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗               ║
║       ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝               ║
║       ██║███████║██████╔╝██║   ██║██║███████╗               ║
║  ██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║               ║
║  ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║               ║
║   ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝               ║
║                                                              ║
║            Just A Rather Very Intelligent System             ║
║                    Versão 3.0.0 MCP                          ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    logger.info("🚀 Iniciando JARVIS com sistema MCP...")

    # Jarvis (Orchestrator + ContextManager) como cérebro de execução: MCP planeja, Orchestrator executa
    from core.jarvis import Jarvis
    jarvis = Jarvis()
    await jarvis.start()

    # Importa componentes MCP
    from core.mcp_client import create_mcp_client
    from core.ai_engine import get_ai

    # Inicializa MCP Client com jarvis injetado (carrega Jarvis Actions: monitor, autopilot, whatsapp_send, etc.)
    mcp_client = await create_mcp_client(jarvis=jarvis)

    # Inicializa AI Engine com MCP
    ai = get_ai(mcp_client)
    
    # TTS (opcional)
    tts = None
    if args.voice:
        try:
            import pyttsx3
            tts = pyttsx3.init()
            tts.setProperty('rate', 180)
            voices = tts.getProperty('voices')
            for voice in voices:
                if 'brazil' in voice.name.lower() or 'portuguese' in voice.name.lower():
                    tts.setProperty('voice', voice.id)
                    break
            logger.info("✅ TTS ativado")
        except Exception as e:
            logger.warning(f"⚠️ TTS não disponível: {e}")
    
    logger.info(f"✅ JARVIS MCP pronto - {len(mcp_client.all_tools)} ferramentas disponíveis")
    
    print("\n💬 Digite sua mensagem (ou 'sair' para encerrar):")
    print("   Comandos: 'ferramentas', 'status', 'limpar'\n")
    
    try:
        while True:
            try:
                user_input = input("Você: ").strip()
                
                if not user_input:
                    continue
                
                # Comandos especiais
                if user_input.lower() in ['sair', 'exit', 'quit']:
                    print("\nJARVIS: Até logo, senhor. Foi um prazer servi-lo.")
                    break
                
                if user_input.lower() == 'ferramentas':
                    print(f"\n{mcp_client.list_tools()}\n")
                    continue
                
                if user_input.lower() == 'status':
                    servers = list(mcp_client.servers.keys())
                    tools = len(mcp_client.all_tools)
                    print(f"""
📊 **Status do JARVIS v3.0.0 MCP**

🔧 MCP Servers: {', '.join(servers)}
🛠️ Ferramentas: {tools}
🤖 Modelo: {ai.model}
🔊 TTS: {'Ativo' if tts else 'Inativo'}
⏱️ Histórico: {len(ai.conversation_history)} mensagens
""")
                    continue
                
                if user_input.lower() == 'limpar':
                    ai.clear_history()
                    print("\nJARVIS: Histórico de conversa limpo.\n")
                    continue
                
                # Processa com IA
                response = await ai.process(user_input)
                print(f"\nJARVIS: {response.text}\n")
                
                # TTS
                if tts:
                    try:
                        clean = response.text
                        for c in ['**', '*', '`', '#', '📊', '🔧', '🛠️', '🤖', '🔊', '⏱️', '❌', '✅', '🚀']:
                            clean = clean.replace(c, '')
                        tts.say(clean)
                        tts.runAndWait()
                    except:
                        pass
                
            except KeyboardInterrupt:
                print("\n\nJARVIS: Encerrando por interrupção...")
                break
                
    finally:
        await mcp_client.stop()
        await jarvis.stop()
        logger.info("JARVIS encerrado.")


def print_status(jarvis):
    """Imprime status do JARVIS"""
    status = jarvis.status
    
    print("\n" + "=" * 50)
    print(f"🤖 {status['name']} v{status['version']}")
    print("=" * 50)
    print(f"Status: {'🟢 Online' if status['running'] else '🔴 Offline'}")
    print(f"Uptime: {status['uptime']}")
    print(f"Contexto: {status['context_size']} mensagens")
    
    print("\n📦 Módulos:")
    for name, mod_status in status.get('modules', {}).items():
        print(f"  {mod_status} {name}")
    
    print("=" * 50 + "\n")


if __name__ == '__main__':
    # Verifica Python 3.8+
    if sys.version_info < (3, 8):
        print("❌ JARVIS requer Python 3.8 ou superior")
        sys.exit(1)
    
    # Executa
    asyncio.run(main())
