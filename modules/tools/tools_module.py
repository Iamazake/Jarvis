# -*- coding: utf-8 -*-
"""
Tools Module - Módulo Principal de Ferramentas
Controle do sistema operacional

Autor: JARVIS Team
Versão: 3.0.0
"""

import asyncio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ToolsModule:
    """
    Módulo de ferramentas do sistema
    
    Funcionalidades:
    - Executar comandos shell
    - Gerenciar arquivos/pastas
    - Abrir/fechar aplicativos
    - Informações do sistema
    """
    
    def __init__(self, config):
        self.config = config
        self._running = False
        
        # Componentes
        self.shell = None
        self.file_manager = None
        self.app_launcher = None
        self.system_info = None
        
        self.status = '🔴'
    
    async def start(self):
        """Inicializa componentes"""
        logger.info("🔧 Iniciando módulo de ferramentas...")
        
        try:
            from .shell import ShellExecutor
            self.shell = ShellExecutor()
            logger.info("  ✅ Shell Executor inicializado")
        except Exception as e:
            logger.warning(f"  ⚠️ Shell: {e}")
        
        try:
            from .file_manager import FileManager
            self.file_manager = FileManager(self.config)
            logger.info("  ✅ File Manager inicializado")
        except Exception as e:
            logger.warning(f"  ⚠️ File Manager: {e}")
        
        try:
            from .app_launcher import AppLauncher
            self.app_launcher = AppLauncher()
            logger.info("  ✅ App Launcher inicializado")
        except Exception as e:
            logger.warning(f"  ⚠️ App Launcher: {e}")
        
        try:
            from .system_info import SystemInfo
            self.system_info = SystemInfo()
            logger.info("  ✅ System Info inicializado")
        except Exception as e:
            logger.warning(f"  ⚠️ System Info: {e}")
        
        self._running = True
        self.status = '🟢'
        logger.info("✅ Módulo de ferramentas pronto")
    
    async def stop(self):
        """Para o módulo"""
        self._running = False
        self.status = '🔴'
    
    async def process(self, message: str, intent, context: Dict, metadata: Dict) -> str:
        """
        Processa comandos de ferramentas
        """
        intent_type = intent.type if hasattr(intent, 'type') else str(intent)
        entities = intent.entities if hasattr(intent, 'entities') else {}
        
        if intent_type == 'system_command':
            command = entities.get('command') or entities.get('raw', '')
            return await self.execute_command(command)
        
        elif intent_type == 'file_operation':
            target = entities.get('target', '')
            return await self.handle_file_operation(message, target)
        
        elif intent_type == 'app_control':
            app = entities.get('app', '')
            return await self.handle_app_control(message, app)
        
        elif intent_type == 'system_info':
            return await self.get_system_status()
        
        return "Não entendi o comando de sistema."
    
    async def execute_command(self, command: str, timeout: int = 30) -> str:
        """
        Executa comando no shell
        
        ⚠️ CUIDADO: Pode ser perigoso!
        """
        if not self.shell:
            return "Shell não disponível"
        
        # Lista de comandos perigosos
        dangerous = ['rm -rf', 'format', 'del /f', 'mkfs', ':(){', 'dd if=']
        
        for d in dangerous:
            if d in command.lower():
                return f"⚠️ Comando potencialmente perigoso bloqueado: '{command}'"
        
        result = await self.shell.execute(command, timeout=timeout)
        
        if result['success']:
            output = result['output'][:1000]  # Limita saída
            return f"✅ Comando executado:\n```\n{output}\n```"
        else:
            return f"❌ Erro: {result['error']}"
    
    async def handle_file_operation(self, message: str, target: str) -> str:
        """Processa operações de arquivo"""
        if not self.file_manager:
            return "File Manager não disponível"
        
        message_lower = message.lower()
        
        if 'criar' in message_lower or 'cria' in message_lower:
            if 'pasta' in message_lower or 'diretório' in message_lower:
                result = await self.file_manager.create_directory(target)
                return f"✅ Pasta criada: {result}" if result else "❌ Erro ao criar pasta"
            else:
                result = await self.file_manager.create_file(target)
                return f"✅ Arquivo criado: {result}" if result else "❌ Erro ao criar arquivo"
        
        elif 'listar' in message_lower or 'lista' in message_lower:
            files = await self.file_manager.list_directory(target or '.')
            if files:
                formatted = '\n'.join([f"  {'📁' if f['is_dir'] else '📄'} {f['name']}" for f in files[:20]])
                return f"📂 Conteúdo:\n{formatted}"
            return "Pasta vazia ou não encontrada"
        
        elif 'organizar' in message_lower or 'organiza' in message_lower:
            organized = await self.file_manager.organize_downloads()
            return f"✅ Arquivos organizados: {organized} movidos"
        
        return "Operação de arquivo não reconhecida"
    
    async def handle_app_control(self, message: str, app: str) -> str:
        """Processa controle de aplicativos"""
        if not self.app_launcher:
            return "App Launcher não disponível"
        
        message_lower = message.lower()
        
        if 'abrir' in message_lower or 'abre' in message_lower or 'inicia' in message_lower:
            success = await self.app_launcher.open(app)
            return f"✅ {app} aberto" if success else f"❌ Não consegui abrir {app}"
        
        elif 'fechar' in message_lower or 'fecha' in message_lower:
            success = await self.app_launcher.close(app)
            return f"✅ {app} fechado" if success else f"❌ Não consegui fechar {app}"
        
        return "Comando de aplicativo não reconhecido"
    
    async def get_system_status(self) -> str:
        """Retorna status do sistema"""
        if not self.system_info:
            return "System Info não disponível"
        
        info = await self.system_info.get_all()
        
        return (
            f"💻 **Status do Sistema**\n\n"
            f"🖥️ CPU: {info['cpu_percent']}%\n"
            f"🧠 RAM: {info['memory_percent']}% ({info['memory_used']})\n"
            f"💾 Disco: {info['disk_percent']}% ({info['disk_used']})\n"
            f"🔋 Bateria: {info.get('battery', 'N/A')}\n"
            f"⏰ Uptime: {info['uptime']}"
        )
    
    def is_available(self) -> bool:
        """Verifica se módulo está disponível"""
        return self._running
