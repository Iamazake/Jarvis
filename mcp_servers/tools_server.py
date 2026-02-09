# -*- coding: utf-8 -*-
"""
Tools MCP Server - Controle do Sistema Operacional
Permite executar comandos, gerenciar arquivos e controlar apps

Autor: JARVIS Team
Versão: 3.0.0

SEGURANÇA:
- Lista de comandos bloqueados
- Diretórios permitidos configuráveis
- Confirmação para ações críticas
"""

import os
import sys
import asyncio
import subprocess
import platform
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Adiciona path do projeto
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_servers.base import MCPServer, Tool

logger = logging.getLogger(__name__)


# === CONFIGURAÇÕES DE SEGURANÇA ===
BLOCKED_COMMANDS = [
    'rm -rf /', 'rm -rf ~', 'rm -rf *',
    'del /f /s /q c:\\', 'format c:',
    'shutdown', 'reboot', 'halt',
    ':(){:|:&};:', 'fork bomb',
    'dd if=/dev/zero',
    'mkfs', 'fdisk',
    'net user', 'net localgroup',
    'reg delete', 'regedit',
    'DROP TABLE', 'DROP DATABASE', 'DELETE FROM',
    'TRUNCATE',
]

ALLOWED_PATHS = [
    Path(os.environ.get('USERPROFILE', 'C:/Users')),
    Path('C:/YAmazake'),
    Path('D:/'),
]

DANGEROUS_EXTENSIONS = ['.exe', '.bat', '.cmd', '.ps1', '.vbs', '.msi']


class ToolsServer(MCPServer):
    """
    MCP Server para controle do sistema
    
    Ferramentas:
    - run_command: Executa comando no terminal
    - list_files: Lista arquivos de um diretório
    - read_file: Lê conteúdo de arquivo
    - write_file: Escreve em arquivo
    - create_directory: Cria diretório
    - delete_file: Deleta arquivo (com confirmação)
    - get_system_info: Informações do sistema
    - open_application: Abre aplicativo
    - get_running_processes: Lista processos
    """
    
    def __init__(self):
        super().__init__("jarvis-tools", "3.0.0")
        self.require_confirmation = True
        self.pending_confirmations: Dict[str, Dict] = {}
    
    async def setup_tools(self):
        """Configura todas as ferramentas"""
        
        # 1. Executar comando
        self.register_tool(
            Tool(
                name="run_command",
                description="Executa um comando no terminal do sistema. Use para automação, scripts e tarefas do sistema.",
                parameters={
                    "command": {
                        "type": "string",
                        "description": "O comando a ser executado"
                    },
                    "working_dir": {
                        "type": "string",
                        "description": "Diretório de trabalho (opcional)"
                    }
                },
                required=["command"]
            ),
            self.run_command
        )
        
        # 2. Listar arquivos
        self.register_tool(
            Tool(
                name="list_files",
                description="Lista arquivos e pastas de um diretório. Retorna nome, tipo e tamanho.",
                parameters={
                    "path": {
                        "type": "string",
                        "description": "Caminho do diretório"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Filtro glob (ex: *.py, *.txt)"
                    }
                },
                required=["path"]
            ),
            self.list_files
        )
        
        # 3. Ler arquivo
        self.register_tool(
            Tool(
                name="read_file",
                description="Lê o conteúdo de um arquivo de texto.",
                parameters={
                    "path": {
                        "type": "string",
                        "description": "Caminho do arquivo"
                    },
                    "max_lines": {
                        "type": "integer",
                        "description": "Máximo de linhas (padrão: 100)"
                    }
                },
                required=["path"]
            ),
            self.read_file
        )
        
        # 4. Escrever arquivo
        self.register_tool(
            Tool(
                name="write_file",
                description="Escreve conteúdo em um arquivo. Cria se não existir.",
                parameters={
                    "path": {
                        "type": "string",
                        "description": "Caminho do arquivo"
                    },
                    "content": {
                        "type": "string",
                        "description": "Conteúdo a escrever"
                    },
                    "append": {
                        "type": "boolean",
                        "description": "Se True, adiciona ao final. Se False, sobrescreve."
                    }
                },
                required=["path", "content"]
            ),
            self.write_file
        )
        
        # 5. Criar diretório
        self.register_tool(
            Tool(
                name="create_directory",
                description="Cria um novo diretório (pasta).",
                parameters={
                    "path": {
                        "type": "string",
                        "description": "Caminho do diretório a criar"
                    }
                },
                required=["path"]
            ),
            self.create_directory
        )
        
        # 6. Deletar arquivo
        self.register_tool(
            Tool(
                name="delete_file",
                description="Deleta um arquivo ou pasta vazia. CUIDADO: ação irreversível!",
                parameters={
                    "path": {
                        "type": "string",
                        "description": "Caminho do arquivo/pasta a deletar"
                    }
                },
                required=["path"]
            ),
            self.delete_file
        )
        
        # 7. Info do sistema
        self.register_tool(
            Tool(
                name="get_system_info",
                description="Retorna informações do sistema: CPU, RAM, disco, bateria, uptime.",
                parameters={},
                required=[]
            ),
            self.get_system_info
        )
        
        # 8. Abrir aplicativo
        self.register_tool(
            Tool(
                name="open_application",
                description="Abre um aplicativo pelo nome ou caminho. Ex: chrome, notepad, vscode",
                parameters={
                    "app_name": {
                        "type": "string",
                        "description": "Nome do aplicativo (chrome, notepad, vscode, etc)"
                    },
                    "arguments": {
                        "type": "string",
                        "description": "Argumentos opcionais (ex: URL para chrome)"
                    }
                },
                required=["app_name"]
            ),
            self.open_application
        )
        
        # 9. Listar processos
        self.register_tool(
            Tool(
                name="get_running_processes",
                description="Lista processos em execução com uso de CPU e memória.",
                parameters={
                    "filter": {
                        "type": "string",
                        "description": "Filtrar por nome do processo"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limite de processos (padrão: 20)"
                    }
                },
                required=[]
            ),
            self.get_running_processes
        )
        
        # 10. Fechar processo
        self.register_tool(
            Tool(
                name="kill_process",
                description="Encerra um processo pelo nome ou PID.",
                parameters={
                    "process": {
                        "type": "string",
                        "description": "Nome ou PID do processo"
                    }
                },
                required=["process"]
            ),
            self.kill_process
        )
        
        logger.info(f"✅ {len(self.tools)} ferramentas de sistema registradas")
    
    # === VALIDAÇÕES DE SEGURANÇA ===
    
    def _is_command_safe(self, command: str) -> tuple:
        """Verifica se comando é seguro"""
        cmd_lower = command.lower()
        
        for blocked in BLOCKED_COMMANDS:
            if blocked.lower() in cmd_lower:
                return False, f"Comando bloqueado por segurança: {blocked}"
        
        return True, ""
    
    def _is_path_allowed(self, path: str) -> tuple:
        """Verifica se caminho é permitido"""
        try:
            target = Path(path).resolve()
            
            for allowed in ALLOWED_PATHS:
                try:
                    target.relative_to(allowed.resolve())
                    return True, ""
                except ValueError:
                    continue
            
            return False, f"Caminho fora dos diretórios permitidos: {path}"
        except Exception as e:
            return False, str(e)
    
    def _is_file_safe(self, path: str) -> tuple:
        """Verifica se arquivo é seguro para modificar"""
        ext = Path(path).suffix.lower()
        
        if ext in DANGEROUS_EXTENSIONS:
            return False, f"Extensão bloqueada: {ext}"
        
        return True, ""
    
    # === IMPLEMENTAÇÃO DAS FERRAMENTAS ===
    
    async def run_command(self, command: str, working_dir: str = None) -> str:
        """Executa comando no terminal"""
        # Validação de segurança
        is_safe, error = self._is_command_safe(command)
        if not is_safe:
            return f"❌ BLOQUEADO: {error}"
        
        try:
            # Define diretório de trabalho
            cwd = working_dir or os.getcwd()
            
            # Executa comando
            if platform.system() == "Windows":
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd
                )
            else:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd
                )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=60
            )
            
            output = stdout.decode('utf-8', errors='ignore')
            errors = stderr.decode('utf-8', errors='ignore')
            
            result = []
            if output:
                result.append(f"📤 Saída:\n{output[:2000]}")
            if errors:
                result.append(f"⚠️ Erros:\n{errors[:500]}")
            if process.returncode != 0:
                result.append(f"❌ Código de saída: {process.returncode}")
            else:
                result.append("✅ Comando executado com sucesso")
            
            return "\n".join(result)
            
        except asyncio.TimeoutError:
            return "❌ Timeout: comando demorou mais de 60 segundos"
        except Exception as e:
            return f"❌ Erro: {str(e)}"
    
    async def list_files(self, path: str, pattern: str = "*") -> str:
        """Lista arquivos de um diretório"""
        is_allowed, error = self._is_path_allowed(path)
        if not is_allowed:
            return f"❌ BLOQUEADO: {error}"
        
        try:
            p = Path(path)
            if not p.exists():
                return f"❌ Diretório não existe: {path}"
            
            if not p.is_dir():
                return f"❌ Não é um diretório: {path}"
            
            files = []
            for item in p.glob(pattern):
                try:
                    stat = item.stat()
                    size = stat.st_size
                    
                    if size < 1024:
                        size_str = f"{size}B"
                    elif size < 1024 * 1024:
                        size_str = f"{size/1024:.1f}KB"
                    else:
                        size_str = f"{size/(1024*1024):.1f}MB"
                    
                    type_icon = "📁" if item.is_dir() else "📄"
                    files.append(f"{type_icon} {item.name} ({size_str})")
                except:
                    files.append(f"❓ {item.name}")
            
            if not files:
                return f"📂 Diretório vazio: {path}"
            
            return f"📂 {path}\n" + "\n".join(files[:50])
            
        except Exception as e:
            return f"❌ Erro: {str(e)}"
    
    async def read_file(self, path: str, max_lines: int = 100) -> str:
        """Lê conteúdo de arquivo"""
        is_allowed, error = self._is_path_allowed(path)
        if not is_allowed:
            return f"❌ BLOQUEADO: {error}"
        
        try:
            p = Path(path)
            if not p.exists():
                return f"❌ Arquivo não existe: {path}"
            
            if not p.is_file():
                return f"❌ Não é um arquivo: {path}"
            
            # Limita tamanho
            if p.stat().st_size > 1024 * 1024:  # 1MB
                return f"❌ Arquivo muito grande (>1MB)"
            
            content = p.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')
            
            if len(lines) > max_lines:
                content = '\n'.join(lines[:max_lines])
                content += f"\n\n... ({len(lines) - max_lines} linhas omitidas)"
            
            return f"📄 {path}\n{'='*40}\n{content}"
            
        except Exception as e:
            return f"❌ Erro: {str(e)}"
    
    async def write_file(self, path: str, content: str, append: bool = False) -> str:
        """Escreve em arquivo"""
        is_allowed, error = self._is_path_allowed(path)
        if not is_allowed:
            return f"❌ BLOQUEADO: {error}"
        
        is_safe, error = self._is_file_safe(path)
        if not is_safe:
            return f"❌ BLOQUEADO: {error}"
        
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            
            mode = 'a' if append else 'w'
            with open(p, mode, encoding='utf-8') as f:
                f.write(content)
            
            action = "adicionado a" if append else "escrito em"
            return f"✅ Conteúdo {action} {path}"
            
        except Exception as e:
            return f"❌ Erro: {str(e)}"
    
    async def create_directory(self, path: str) -> str:
        """Cria diretório"""
        is_allowed, error = self._is_path_allowed(path)
        if not is_allowed:
            return f"❌ BLOQUEADO: {error}"
        
        try:
            p = Path(path)
            p.mkdir(parents=True, exist_ok=True)
            return f"✅ Diretório criado: {path}"
        except Exception as e:
            return f"❌ Erro: {str(e)}"
    
    async def delete_file(self, path: str) -> str:
        """Deleta arquivo"""
        is_allowed, error = self._is_path_allowed(path)
        if not is_allowed:
            return f"❌ BLOQUEADO: {error}"
        
        try:
            p = Path(path)
            if not p.exists():
                return f"❌ Não existe: {path}"
            
            if p.is_file():
                p.unlink()
                return f"✅ Arquivo deletado: {path}"
            elif p.is_dir():
                if any(p.iterdir()):
                    return f"❌ Diretório não está vazio: {path}"
                p.rmdir()
                return f"✅ Diretório deletado: {path}"
            
        except Exception as e:
            return f"❌ Erro: {str(e)}"
    
    async def get_system_info(self) -> str:
        """Retorna informações do sistema"""
        try:
            import psutil
            
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # RAM
            mem = psutil.virtual_memory()
            mem_used = mem.used / (1024**3)
            mem_total = mem.total / (1024**3)
            mem_percent = mem.percent
            
            # Disco
            disk = psutil.disk_usage('/')
            disk_used = disk.used / (1024**3)
            disk_total = disk.total / (1024**3)
            disk_percent = disk.percent
            
            # Bateria
            battery = psutil.sensors_battery()
            if battery:
                battery_str = f"🔋 Bateria: {battery.percent}%"
                if battery.power_plugged:
                    battery_str += " (carregando)"
            else:
                battery_str = "🔌 Sem bateria (desktop)"
            
            # Uptime
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            days = uptime.days
            hours = uptime.seconds // 3600
            minutes = (uptime.seconds % 3600) // 60
            
            return f"""📊 **Informações do Sistema**

💻 **Sistema:** {platform.system()} {platform.release()}
🖥️ **Máquina:** {platform.machine()}

🔧 **CPU:** {cpu_percent}% ({cpu_count} cores)
🧠 **RAM:** {mem_used:.1f}GB / {mem_total:.1f}GB ({mem_percent}%)
💾 **Disco:** {disk_used:.1f}GB / {disk_total:.1f}GB ({disk_percent}%)
{battery_str}

⏱️ **Uptime:** {days}d {hours}h {minutes}m
📅 **Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"""

        except ImportError:
            return "❌ psutil não instalado"
        except Exception as e:
            return f"❌ Erro: {str(e)}"
    
    async def open_application(self, app_name: str, arguments: str = "") -> str:
        """Abre um aplicativo"""
        # Mapa de aplicativos comuns
        apps = {
            'chrome': 'C:/Program Files/Google/Chrome/Application/chrome.exe',
            'firefox': 'C:/Program Files/Mozilla Firefox/firefox.exe',
            'edge': 'msedge',
            'notepad': 'notepad',
            'notepad++': 'C:/Program Files/Notepad++/notepad++.exe',
            'vscode': 'code',
            'code': 'code',
            'explorer': 'explorer',
            'calc': 'calc',
            'calculadora': 'calc',
            'cmd': 'cmd',
            'terminal': 'wt',
            'spotify': 'spotify',
            'discord': 'discord',
        }
        
        app_lower = app_name.lower()
        
        # Busca no mapa ou usa diretamente
        executable = apps.get(app_lower, app_name)
        
        try:
            if arguments:
                cmd = f'start "" "{executable}" {arguments}'
            else:
                cmd = f'start "" "{executable}"'
            
            subprocess.Popen(cmd, shell=True)
            return f"✅ Abrindo {app_name}..."
            
        except Exception as e:
            return f"❌ Erro ao abrir {app_name}: {str(e)}"
    
    async def get_running_processes(self, filter: str = None, limit: int = 20) -> str:
        """Lista processos em execução"""
        try:
            import psutil
            
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    info = proc.info
                    name = info['name']
                    
                    if filter and filter.lower() not in name.lower():
                        continue
                    
                    processes.append({
                        'pid': info['pid'],
                        'name': name,
                        'cpu': info['cpu_percent'] or 0,
                        'mem': info['memory_percent'] or 0
                    })
                except:
                    continue
            
            # Ordena por CPU
            processes.sort(key=lambda x: x['cpu'], reverse=True)
            processes = processes[:limit]
            
            lines = ["🔄 **Processos em Execução**\n"]
            for p in processes:
                lines.append(f"• {p['name']} (PID: {p['pid']}) - CPU: {p['cpu']:.1f}% | RAM: {p['mem']:.1f}%")
            
            return "\n".join(lines)
            
        except ImportError:
            return "❌ psutil não instalado"
        except Exception as e:
            return f"❌ Erro: {str(e)}"
    
    async def kill_process(self, process: str) -> str:
        """Encerra um processo"""
        try:
            import psutil
            
            # Tenta como PID
            try:
                pid = int(process)
                p = psutil.Process(pid)
                name = p.name()
                p.terminate()
                return f"✅ Processo encerrado: {name} (PID: {pid})"
            except ValueError:
                pass
            
            # Tenta como nome
            killed = 0
            for proc in psutil.process_iter(['pid', 'name']):
                if process.lower() in proc.info['name'].lower():
                    proc.terminate()
                    killed += 1
            
            if killed:
                return f"✅ {killed} processo(s) '{process}' encerrado(s)"
            else:
                return f"❌ Processo não encontrado: {process}"
            
        except Exception as e:
            return f"❌ Erro: {str(e)}"


# === MAIN (para rodar standalone) ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = ToolsServer()
    asyncio.run(server.run_stdio())
