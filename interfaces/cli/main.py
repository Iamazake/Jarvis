# -*- coding: utf-8 -*-
"""
JARVIS CLI - Interface Interativa Principal
Interface rica com cores e formatação

Autor: JARVIS Team
Versão: 3.0.0
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Optional

from .components import Colors, clear_screen, print_header, print_box, print_typing


class JarvisCLI:
    """
    Interface de linha de comando do JARVIS
    
    Features:
    - Cores e formatação rica
    - Histórico de comandos
    - Autocomplete básico
    - Modo de voz integrado
    """
    
    def __init__(self, jarvis):
        self.jarvis = jarvis
        self._running = False
        self._voice_mode = False
        self._command_history = []
        
        # Comandos especiais do CLI
        self.cli_commands = {
            '/help': self._cmd_help,
            '/status': self._cmd_status,
            '/clear': self._cmd_clear,
            '/voice': self._cmd_voice,
            '/modules': self._cmd_modules,
            '/history': self._cmd_history,
            '/exit': self._cmd_exit,
            '/quit': self._cmd_exit,
        }
    
    async def run(self):
        """Executa o CLI em modo interativo"""
        self._running = True
        
        clear_screen()
        print_header(self.jarvis.name)
        
        # Mensagem de boas-vindas
        await self._greet()
        
        while self._running:
            try:
                # Prompt
                user_input = await self._get_input()
                
                if not user_input:
                    continue
                
                # Adiciona ao histórico
                self._command_history.append(user_input)
                
                # Verifica comandos especiais
                if user_input.startswith('/'):
                    await self._handle_cli_command(user_input)
                    continue
                
                # Processa via JARVIS
                await self._process_message(user_input)
                
            except KeyboardInterrupt:
                print("\n")
                continue
            except EOFError:
                break
        
        print(f"\n{Colors.CYAN}👋 Até logo, senhor!{Colors.END}\n")
    
    async def run_with_voice(self):
        """Executa o CLI com modo de voz ativo"""
        self._voice_mode = True
        
        # Verifica se módulo de voz está disponível
        voice_module = self.jarvis.orchestrator.modules.get('voice')
        
        if not voice_module or not voice_module.is_available():
            print(f"{Colors.YELLOW}⚠️ Módulo de voz não disponível. Iniciando em modo texto.{Colors.END}")
            self._voice_mode = False
            await self.run()
            return
        
        clear_screen()
        print_header(f"{self.jarvis.name} - Modo Voz")
        
        print(f"{Colors.GREEN}🎤 Modo de voz ativo!{Colors.END}")
        print(f"{Colors.CYAN}Diga '{self.jarvis.wake_word}' para ativar ou digite comandos.{Colors.END}\n")
        
        # Inicia escuta de wake word em background
        asyncio.create_task(self._voice_listen_loop(voice_module))
        
        # Continua com CLI normal também
        await self.run()
    
    async def _voice_listen_loop(self, voice_module):
        """Loop de escuta por wake word"""
        async def on_wake():
            print(f"\n{Colors.GREEN}🎯 '{self.jarvis.wake_word}' detectado!{Colors.END}")
            await voice_module.speak("Às suas ordens, senhor.")
            
            # Escuta comando
            print(f"{Colors.CYAN}👂 Ouvindo...{Colors.END}")
            text = await voice_module.listen(timeout=10)
            
            if text:
                print(f"{Colors.BLUE}Você disse: {text}{Colors.END}")
                await self._process_message(text, speak_response=True)
            else:
                print(f"{Colors.YELLOW}Não entendi. Tente novamente.{Colors.END}")
        
        await voice_module.listen_for_wake_word(on_wake)
    
    async def _get_input(self) -> str:
        """Obtém input do usuário"""
        try:
            # Prompt colorido
            prompt = f"\n{Colors.GREEN}Você{Colors.END}: "
            
            # Leitura assíncrona
            loop = asyncio.get_event_loop()
            user_input = await loop.run_in_executor(None, lambda: input(prompt))
            
            return user_input.strip()
            
        except Exception:
            return ""
    
    async def _process_message(self, message: str, speak_response: bool = False):
        """Processa mensagem e exibe resposta"""
        # Mostra indicador de processamento
        print(f"\n{Colors.CYAN}🤖 {self.jarvis.name}:{Colors.END} ", end="", flush=True)
        
        # Processa
        response = await self.jarvis.process(message, source='cli')
        
        # Exibe resposta com efeito de digitação
        await print_typing(response)
        
        # Fala resposta se em modo voz
        if speak_response and self._voice_mode:
            voice_module = self.jarvis.orchestrator.modules.get('voice')
            if voice_module:
                await voice_module.speak(response)
    
    async def _greet(self):
        """Mensagem de boas-vindas"""
        hour = datetime.now().hour
        
        if 5 <= hour < 12:
            greeting = "Bom dia"
        elif 12 <= hour < 18:
            greeting = "Boa tarde"
        else:
            greeting = "Boa noite"
        
        message = f"{greeting}, senhor. {self.jarvis.name} às suas ordens."
        
        print(f"\n{Colors.CYAN}🤖 {self.jarvis.name}:{Colors.END} {message}")
        print(f"{Colors.YELLOW}   Digite /help para ver comandos disponíveis.{Colors.END}\n")
    
    async def _handle_cli_command(self, command: str):
        """Processa comandos especiais do CLI"""
        cmd = command.split()[0].lower()
        args = command.split()[1:] if len(command.split()) > 1 else []
        
        handler = self.cli_commands.get(cmd)
        
        if handler:
            await handler(args)
        else:
            print(f"{Colors.RED}Comando não reconhecido: {cmd}{Colors.END}")
            print(f"Digite {Colors.YELLOW}/help{Colors.END} para ver comandos disponíveis.")
    
    async def _cmd_help(self, args):
        """Mostra ajuda"""
        help_text = f"""
{Colors.BOLD}📖 Comandos do CLI:{Colors.END}

  {Colors.CYAN}/help{Colors.END}      - Mostra esta ajuda
  {Colors.CYAN}/status{Colors.END}    - Status do JARVIS
  {Colors.CYAN}/modules{Colors.END}   - Lista módulos ativos
  {Colors.CYAN}/voice{Colors.END}     - Ativa/desativa modo de voz
  {Colors.CYAN}/clear{Colors.END}     - Limpa a tela
  {Colors.CYAN}/history{Colors.END}   - Histórico de comandos
  {Colors.CYAN}/exit{Colors.END}      - Sair

{Colors.BOLD}💬 Exemplos de comandos:{Colors.END}

  {Colors.GREEN}"Pesquisa sobre Python 3.12"{Colors.END}
  {Colors.GREEN}"Qual a previsão do tempo?"{Colors.END}
  {Colors.GREEN}"Abre o VS Code"{Colors.END}
  {Colors.GREEN}"Verifica minhas mensagens do WhatsApp"{Colors.END}
  {Colors.GREEN}"Me lembra de fazer backup às 18h"{Colors.END}
  {Colors.GREEN}"Qual o uso de CPU?"{Colors.END}
"""
        print(help_text)
    
    async def _cmd_status(self, args):
        """Mostra status"""
        status = self.jarvis.status
        
        print_box("Status do JARVIS", [
            f"Nome: {status['name']}",
            f"Versão: {status['version']}",
            f"Status: {'🟢 Online' if status['running'] else '🔴 Offline'}",
            f"Uptime: {status['uptime']}",
            f"Contexto: {status['context_size']} mensagens"
        ])
    
    async def _cmd_modules(self, args):
        """Lista módulos"""
        modules = self.jarvis.status.get('modules', {})
        
        lines = []
        for name, mod_status in modules.items():
            lines.append(f"{mod_status} {name}")
        
        print_box("Módulos Ativos", lines or ["Nenhum módulo carregado"])
    
    async def _cmd_voice(self, args):
        """Toggle modo de voz"""
        self._voice_mode = not self._voice_mode
        
        if self._voice_mode:
            print(f"{Colors.GREEN}🎤 Modo de voz ATIVADO{Colors.END}")
        else:
            print(f"{Colors.YELLOW}🔇 Modo de voz DESATIVADO{Colors.END}")
    
    async def _cmd_clear(self, args):
        """Limpa tela"""
        clear_screen()
        print_header(self.jarvis.name)
    
    async def _cmd_history(self, args):
        """Mostra histórico"""
        if not self._command_history:
            print(f"{Colors.YELLOW}Histórico vazio{Colors.END}")
            return
        
        print(f"\n{Colors.BOLD}📜 Histórico:{Colors.END}")
        for i, cmd in enumerate(self._command_history[-10:], 1):
            print(f"  {i}. {cmd}")
    
    async def _cmd_exit(self, args):
        """Sair do CLI"""
        self._running = False
