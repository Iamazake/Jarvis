# -*- coding: utf-8 -*-
"""
Shell Executor - Executa comandos no terminal
"""

import asyncio
import subprocess
import logging
import platform
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ShellExecutor:
    """
    Executa comandos no shell do sistema
    
    ⚠️ ATENÇÃO: Use com cuidado!
    """
    
    def __init__(self):
        self.is_windows = platform.system() == 'Windows'
        self.shell = 'powershell' if self.is_windows else '/bin/bash'
    
    async def execute(self, command: str, timeout: int = 30, 
                      cwd: Optional[str] = None) -> Dict:
        """
        Executa comando no shell
        
        Args:
            command: Comando a executar
            timeout: Timeout em segundos
            cwd: Diretório de trabalho
        
        Returns:
            Dict com success, output, error
        """
        try:
            loop = asyncio.get_event_loop()
            
            def _run():
                if self.is_windows:
                    # PowerShell no Windows
                    result = subprocess.run(
                        ['powershell', '-Command', command],
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        cwd=cwd
                    )
                else:
                    # Bash no Linux/Mac
                    result = subprocess.run(
                        command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        cwd=cwd
                    )
                return result
            
            result = await loop.run_in_executor(None, _run)
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'output': result.stdout.strip(),
                    'error': None,
                    'return_code': 0
                }
            else:
                return {
                    'success': False,
                    'output': result.stdout.strip(),
                    'error': result.stderr.strip() or 'Comando falhou',
                    'return_code': result.returncode
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'output': '',
                'error': f'Comando excedeu timeout de {timeout}s',
                'return_code': -1
            }
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'return_code': -1
            }
    
    async def execute_background(self, command: str) -> bool:
        """
        Executa comando em background
        
        Returns:
            True se iniciou com sucesso
        """
        try:
            if self.is_windows:
                subprocess.Popen(
                    ['powershell', '-Command', command],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            return True
            
        except Exception as e:
            logger.error(f"Erro executando em background: {e}")
            return False
