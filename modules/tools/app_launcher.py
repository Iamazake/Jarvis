# -*- coding: utf-8 -*-
"""
App Launcher - Controle de Aplicativos
"""

import asyncio
import subprocess
import platform
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class AppLauncher:
    """
    Abre e fecha aplicativos
    
    Suporta Windows, Linux e macOS
    """
    
    def __init__(self):
        self.system = platform.system()
        
        # Mapeamento de nomes comuns para comandos
        self.app_aliases = {
            # Navegadores
            'chrome': self._get_chrome_cmd(),
            'firefox': self._get_firefox_cmd(),
            'edge': self._get_edge_cmd(),
            
            # Editores
            'vscode': self._get_vscode_cmd(),
            'code': self._get_vscode_cmd(),
            'notepad': 'notepad' if self.system == 'Windows' else 'gedit',
            'notepad++': 'notepad++',
            
            # Comunicação
            'discord': self._get_discord_cmd(),
            'telegram': self._get_telegram_cmd(),
            'whatsapp': self._get_whatsapp_cmd(),
            'spotify': self._get_spotify_cmd(),
            
            # Utilitários
            'explorer': 'explorer' if self.system == 'Windows' else 'nautilus',
            'terminal': self._get_terminal_cmd(),
            'calculadora': 'calc' if self.system == 'Windows' else 'gnome-calculator',
        }
    
    def _get_chrome_cmd(self) -> str:
        if self.system == 'Windows':
            return 'start chrome'
        elif self.system == 'Darwin':
            return 'open -a "Google Chrome"'
        return 'google-chrome'
    
    def _get_firefox_cmd(self) -> str:
        if self.system == 'Windows':
            return 'start firefox'
        elif self.system == 'Darwin':
            return 'open -a Firefox'
        return 'firefox'
    
    def _get_edge_cmd(self) -> str:
        if self.system == 'Windows':
            return 'start msedge'
        elif self.system == 'Darwin':
            return 'open -a "Microsoft Edge"'
        return 'microsoft-edge'
    
    def _get_vscode_cmd(self) -> str:
        if self.system == 'Windows':
            return 'code'
        elif self.system == 'Darwin':
            return 'open -a "Visual Studio Code"'
        return 'code'
    
    def _get_discord_cmd(self) -> str:
        if self.system == 'Windows':
            return 'start discord:'
        elif self.system == 'Darwin':
            return 'open -a Discord'
        return 'discord'
    
    def _get_telegram_cmd(self) -> str:
        if self.system == 'Windows':
            return 'start telegram:'
        elif self.system == 'Darwin':
            return 'open -a Telegram'
        return 'telegram-desktop'
    
    def _get_whatsapp_cmd(self) -> str:
        if self.system == 'Windows':
            return 'start whatsapp:'
        return 'whatsapp-desktop'
    
    def _get_spotify_cmd(self) -> str:
        if self.system == 'Windows':
            return 'start spotify:'
        elif self.system == 'Darwin':
            return 'open -a Spotify'
        return 'spotify'
    
    def _get_terminal_cmd(self) -> str:
        if self.system == 'Windows':
            return 'start wt'  # Windows Terminal
        elif self.system == 'Darwin':
            return 'open -a Terminal'
        return 'gnome-terminal'
    
    async def open(self, app_name: str, args: str = '') -> bool:
        """
        Abre um aplicativo
        
        Args:
            app_name: Nome do app (pode ser alias ou caminho completo)
            args: Argumentos adicionais
        
        Returns:
            True se abriu com sucesso
        """
        app_lower = app_name.lower().strip()
        
        # Resolve alias
        cmd = self.app_aliases.get(app_lower, app_name)
        
        if args:
            cmd = f"{cmd} {args}"
        
        try:
            logger.info(f"Abrindo: {cmd}")
            
            if self.system == 'Windows':
                subprocess.Popen(
                    cmd,
                    shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Erro abrindo {app_name}: {e}")
            return False
    
    async def close(self, app_name: str) -> bool:
        """
        Fecha um aplicativo
        
        Args:
            app_name: Nome do processo
        
        Returns:
            True se fechou com sucesso
        """
        app_lower = app_name.lower().strip()
        
        # Nomes de processo comuns
        process_names = {
            'chrome': 'chrome',
            'firefox': 'firefox',
            'vscode': 'Code',
            'code': 'Code',
            'discord': 'Discord',
            'spotify': 'Spotify',
            'notepad': 'notepad',
        }
        
        process = process_names.get(app_lower, app_name)
        
        try:
            if self.system == 'Windows':
                subprocess.run(
                    ['taskkill', '/F', '/IM', f'{process}.exe'],
                    capture_output=True
                )
            else:
                subprocess.run(
                    ['pkill', '-f', process],
                    capture_output=True
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Erro fechando {app_name}: {e}")
            return False
    
    async def is_running(self, app_name: str) -> bool:
        """Verifica se app está rodando"""
        try:
            if self.system == 'Windows':
                result = subprocess.run(
                    ['tasklist', '/FI', f'IMAGENAME eq {app_name}.exe'],
                    capture_output=True,
                    text=True
                )
                return app_name.lower() in result.stdout.lower()
            else:
                result = subprocess.run(
                    ['pgrep', '-f', app_name],
                    capture_output=True
                )
                return result.returncode == 0
                
        except Exception:
            return False
    
    async def open_url(self, url: str) -> bool:
        """Abre URL no navegador padrão"""
        try:
            import webbrowser
            webbrowser.open(url)
            return True
        except Exception as e:
            logger.error(f"Erro abrindo URL: {e}")
            return False
