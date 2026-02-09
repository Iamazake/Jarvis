# -*- coding: utf-8 -*-
"""
Automation Module - Módulo Principal de Automação
Sistema de workflows automatizados

Autor: JARVIS Team
Versão: 3.1.0
"""

from typing import Dict, Any, Optional, List

from core.logger import get_logger
from core.module_factory import BaseModule
from core.schemas import WorkflowSchema
from .workflow_engine import WorkflowEngine, WorkflowExecution
from .triggers import TriggerManager, Trigger, TriggerType

logger = get_logger(__name__)


class AutomationModule(BaseModule):
    """
    Módulo de Automação
    
    Funcionalidades:
    - Criar e executar workflows
    - Triggers automáticos
    - Histórico de execuções
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.workflow_engine = WorkflowEngine()
        self.trigger_manager = TriggerManager()
    
    async def start(self):
        """Inicializa o módulo"""
        logger.info("⚙️ Iniciando módulo de automação...")
        
        # Inicia trigger manager
        await self.trigger_manager.start()
        
        self._running = True
        self.status = '🟢'
        logger.info("✅ Módulo de automação pronto")
    
    async def stop(self):
        """Para o módulo"""
        await self.trigger_manager.stop()
        self._running = False
        self.status = '🔴'
        logger.info("Módulo de automação parado")
    
    async def process(
        self,
        message: str,
        intent,
        context: Dict,
        metadata: Dict
    ) -> str:
        """Processa comandos de automação"""
        intent_type = intent.type if hasattr(intent, 'type') else str(intent)
        message_lower = message.lower()
        
        # Criar workflow
        if 'criar' in message_lower and 'workflow' in message_lower:
            return await self._handle_create_workflow(message)
        
        # Listar workflows
        elif 'listar' in message_lower and 'workflow' in message_lower:
            return await self._handle_list_workflows()
        
        # Executar workflow
        elif 'executar' in message_lower or 'rodar' in message_lower:
            return await self._handle_execute_workflow(message)
        
        else:
            return "Não entendi o comando de automação. Tente 'criar workflow', 'listar workflows' ou 'executar workflow'."
    
    async def _handle_create_workflow(self, message: str) -> str:
        """Cria workflow"""
        return "Para criar um workflow, use: 'Criar workflow [nome] com trigger [tipo] e ações [ações]'"
    
    async def _handle_list_workflows(self) -> str:
        """Lista workflows"""
        workflows = self.workflow_engine.list_workflows()
        
        if not workflows:
            return "Não há workflows configurados."
        
        response = f"⚙️ **Workflows** ({len(workflows)})\n\n"
        for wf in workflows:
            response += f"• {wf.get('name', wf.get('id'))}\n"
            response += f"  Status: {'✅ Ativo' if wf.get('enabled', True) else '❌ Desativado'}\n\n"
        
        return response
    
    async def _handle_execute_workflow(self, message: str) -> str:
        """Executa workflow"""
        return "Para executar um workflow, use: 'Executar workflow [nome]'"
    
    # Métodos públicos
    
    async def create_workflow(
        self,
        name: str,
        trigger: Dict[str, Any],
        actions: List[Dict[str, Any]],
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cria workflow programaticamente"""
        workflow = {
            'name': name,
            'description': description,
            'trigger': trigger,
            'actions': actions,
            'enabled': True
        }
        
        self.workflow_engine.register_workflow(workflow)
        return workflow
    
    async def execute_workflow(
        self,
        workflow_id: str,
        trigger_data: Dict[str, Any] = None
    ) -> WorkflowExecution:
        """Executa workflow programaticamente"""
        return await self.workflow_engine.execute_workflow(workflow_id, trigger_data)
    
    async def get_execution_history(
        self,
        workflow_id: Optional[str] = None,
        limit: int = 50
    ) -> List[WorkflowExecution]:
        """Obtém histórico de execuções"""
        return self.workflow_engine.get_execution_history(workflow_id, limit)
