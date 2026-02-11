# -*- coding: utf-8 -*-
"""
Orchestrator - Orquestrador de Módulos
Cérebro do JARVIS - decide o que fazer e roteia para módulos

Autor: JARVIS Team
Versão: 3.0.0
"""

import asyncio
import os
import re
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .intent_classifier import IntentClassifier, Intent
from .execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Orquestrador central do JARVIS
    
    Responsabilidades:
    - Classificar intenções do usuário
    - Rotear para o módulo correto
    - Gerenciar execução paralela
    - Combinar respostas de múltiplos módulos
    """
    
    def __init__(self, config):
        self.config = config
        self.intent_classifier = IntentClassifier()
        self.modules: Dict[str, Any] = {}
        self._running = False
        
        # Fila de tarefas pendentes
        self._task_queue: asyncio.Queue = asyncio.Queue()
        
        # Registro de ações proativas agendadas
        self._scheduled_tasks: List[Dict] = []
        
        # Task do worker (cancelada explicitamente em stop())
        self._worker_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Inicializa todos os módulos"""
        logger.info("🔧 Iniciando orquestrador...")
        self._running = True
        
        # Carrega módulos disponíveis
        await self._load_modules()
        
        # Inicia worker para processar fila; evita duplicata se start() chamado 2x
        existing = getattr(self, '_worker_task', None)
        if existing is not None and not existing.done():
            logger.warning("Task worker já em execução, não criando outra")
        else:
            self._worker_task = asyncio.create_task(
                self._task_worker(), name="orchestrator_task_worker"
            )
        
        logger.info(f"✅ Orquestrador pronto - {len(self.modules)} módulos carregados")
    
    async def stop(self):
        """Para todos os módulos"""
        self._running = False
        
        # Cancelar e aguardar worker com timeout para evitar race com module.stop()
        task = getattr(self, '_worker_task', None)
        if task is not None:
            task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=2.0)
            except asyncio.CancelledError:
                pass
            except asyncio.TimeoutError:
                logger.warning("Timeout aguardando _task_worker encerrar (2s)")
        
        for name, module in self.modules.items():
            try:
                if hasattr(module, 'stop'):
                    await module.stop()
                logger.info(f"  ⏹️  {name} parado")
            except Exception as e:
                logger.error(f"  ❌ Erro parando {name}: {e}")
    
    async def _load_modules(self):
        """Carrega módulos habilitados"""
        # Módulos disponíveis
        available_modules = {
            'ai': ('modules.ai', 'AIModule'),
            'voice': ('modules.voice', 'VoiceModule'),
            'whatsapp': ('modules.whatsapp', 'WhatsAppModule'),
            'search': ('modules.search', 'SearchModule'),
            'tools': ('modules.tools', 'ToolsModule'),
            'calendar': ('modules.calendar', 'CalendarModule'),
            'memory': ('modules.memory', 'MemoryModule'),
        }
        
        disable_voice = os.getenv('JARVIS_DISABLE_VOICE', '').strip().lower() in ('1', 'true', 'yes')
        for name, (module_path, class_name) in available_modules.items():
            if name == 'voice' and disable_voice:
                logger.info("  ⏭️  voice ignorado (JARVIS_DISABLE_VOICE=1)")
                continue
            try:
                module = __import__(module_path, fromlist=[class_name])
                module_class = getattr(module, class_name)
                self.modules[name] = module_class(self.config)
                if hasattr(self.modules[name], 'start'):
                    await self.modules[name].start()
                logger.info(f"  ✅ {name} carregado")
            except ImportError:
                logger.debug(f"  ⏭️  {name} não disponível")
            except Exception as e:
                logger.warning(f"  ⚠️  {name}: {e}")
        
        # Sempre garante módulo de IA básico
        if 'ai' not in self.modules:
            await self._load_basic_ai()
    
    async def _load_basic_ai(self):
        """Carrega módulo básico de IA (fallback quando modules.ai falha) — sem depender de src/"""
        try:
            from core.ai_engine import JarvisAI
            engine = JarvisAI()
            # Wrapper para a interface do módulo (process(message, intent, context, metadata) -> str)
            class _AIFallback:
                def __init__(self, e):
                    self._engine = e
                async def process(self, message, intent, context, metadata):
                    r = await self._engine.process(message)
                    return r.text if hasattr(r, 'text') else str(r)
            self.modules['ai'] = _AIFallback(engine)
            logger.info("  ✅ ai (fallback core.ai_engine) carregado")
        except Exception as e:
            logger.error("  ❌ Falha ao carregar IA: %s", e)
    
    async def process(
        self, message: str, context: Dict, source: str, metadata: Dict
    ) -> tuple:
        """
        Processa uma mensagem e retorna (resposta, metadata).
        REGRA: Se houver pending_plan, NUNCA reclassificar — só interpretar sim/não e executar ou cancelar.
        """
        # 0. Plano pendente: só interpreta sim/não, não reclassifica
        plan = context.get("pending_plan")
        if plan is not None:
            plan = ExecutionPlan.from_dict(plan) if isinstance(plan, dict) else plan
            if getattr(plan, "status", None) == "awaiting_confirmation":
                msg = (message or "").strip().lower()
                if self._user_confirmed_plan(msg):
                    response, out_meta = await self._execute_plan(plan, context, source, metadata)
                    out_meta["clear_pending_plan"] = True
                    return response, out_meta
                if self._user_cancelled_plan(msg):
                    return "Tarefa cancelada.", {"clear_pending_plan": True}
                return "Posso prosseguir? (Responda sim ou não.)", {}

        # 0b. Confirmação de sugestão de envio ("Quer que eu envie para X?" → usuário disse "sim")
        session = context.get("session") or {}
        suggested = session.get("suggested_send")
        if suggested and isinstance(suggested, dict) and suggested.get("contact"):
            msg = (message or "").strip().lower()
            if self._user_confirmed_plan(msg):
                contact = (suggested.get("contact") or "").strip()
                tone = (suggested.get("tone") or "fofinha").strip()
                plan = self._create_send_compose_plan(contact, f"mensagem {tone}")
                plan.formality = "informal"
                plan.tone = "romantic" if tone in ("fofinha", "fofinho", "amorosa") else ""
                return (
                    plan.summary + " Posso prosseguir?",
                    {"pending_plan": plan.to_dict(), "clear_suggested_send": True},
                )
            if self._user_cancelled_plan(msg):
                return "Tudo bem.", {"clear_suggested_send": True}

        # 0c. Comando global "para com isso" / parar (nunca cair em app_control)
        if self._is_stop_command(message):
            return "Entendido. Parando.", {"clear_suggested_send": True}

        # 1. Comandos compostos: "mande mensagem para X e monitore a conversa"
        parts = self.intent_classifier.split_compound(message)
        if len(parts) > 1:
            responses = []
            out_meta = {}
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                resp, meta = await self._process_one(part, context, source, metadata)
                responses.append(resp)
                if meta:
                    out_meta.update(meta)
            combined = "\n\n".join(responses)
            if 'memory' in self.modules:
                await self.modules['memory'].save_conversation(message, combined, "compound")
            return combined, out_meta

        return await self._process_one(message, context, source, metadata)

    async def _process_one(
        self, message: str, context: Dict, source: str, metadata: Dict
    ) -> tuple:
        """Processa uma única mensagem. Retorna (resposta, metadata)."""
        # 1. Classificar intenção
        intent = await self.intent_classifier.classify(message, context)
        logger.info(f"📋 Intenção: {intent.type} (confiança: {intent.confidence:.2f})")

        # 1b. Envio com mensagem composta → criar plano (uma confirmação, contato travado)
        if intent.type == "whatsapp_send" and self._should_compose_message(message):
            contacts = self._extract_contacts_for_plan(message, context, intent)
            if not contacts:
                contact = (intent.entities.get("contact") or "").strip() or (context.get("last_contact") or "").strip() or (context.get("last_monitored_contact") or "").strip()
                contact = self._strip_article_from_contact(contact) or contact
                contacts = [contact] if contact else []
            if contacts:
                contact = contacts[0]
                plan = self._create_send_compose_plan(contact, message)
                if len(contacts) >= 2:
                    plan.summary = (
                        f"Por enquanto envio para um contato por vez. Vou enviar para **{contact}**. "
                        f"(Para enviar também para **{contacts[1]}**, peça em seguida.)"
                    )
                return (
                    plan.summary + " Posso prosseguir?",
                    {"pending_plan": plan.to_dict()},
                )

        # 1c. whatsapp_send sem contato → usar contexto ou perguntar (nunca cair em app_control/conversation)
        if intent.type == "whatsapp_send":
            contact = (getattr(intent, "entities", None) or {}).get("contact") or self._extract_contact_for_plan(message, context, intent)
            contact = (contact or "").strip() or (context.get("last_contact") or "").strip() or (context.get("last_monitored_contact") or "").strip()
            contact = self._strip_article_from_contact(contact) or contact
            if not contact:
                return "Para quem devo enviar a mensagem? (Diga o nome do contato ou 'para [nome]'.)", {}
            if not getattr(intent, "entities", None):
                intent.entities = {}
            intent.entities["contact"] = contact.strip()

        # Regra: verbo de envio → nunca pedir "responda em conversa?" (conversation não compete com WhatsApp)
        if intent.type == "conversation" and intent.confidence < 0.7 and self._has_send_verb(message):
            return (
                "Parece que você quer enviar uma mensagem. Diga para quem e o quê (ex.: envie para [nome] dizendo que ...).",
                {},
            )

        # Pergunta "qual conversa está monitorando?" → responder com last_monitored_contact
        if intent.type == "conversation" and ("monitorando" in (message or "").lower() or "qual conversa" in (message or "").lower()):
            monitored = (context.get("last_monitored_contact") or "").strip()
            if monitored:
                return f"No momento estou monitorando a conversa de **{monitored}**.", {}

        # Continuação de envio: "tchuchuca foramto fofinho" → sugerir envio (não pedir "responda em conversa?")
        if intent.type == "conversation" and intent.confidence < 0.7 and self._looks_like_send_continuation(message):
            name = self._extract_name_from_continuation(message)
            if name:
                return (
                    f"Entendi. Quer que eu envie uma mensagem fofinha para **{name}**?",
                    {"set_suggested_send": {"contact": name, "tone": "fofinha"}},
                )

        # Regra de ouro: confiança < 0.7 → confirmar, não executar (exceto conversa/cumprimentos/ajuda)
        # NUNCA pedir confirmação para conversation, greeting, thanks, farewell, help, system_info
        CONFIDENCE_THRESHOLD = 0.7
        NO_CONFIRM_INTENTS = ('greeting', 'thanks', 'farewell', 'conversation', 'conversation_question', 'help', 'system_info', 'weather', 'wiki', 'search', 'news', 'whatsapp_autoreply_enable', 'whatsapp_autoreply_disable', 'whatsapp_autopilot_status', 'whatsapp_autopilot_set_tone', 'whatsapp_monitor_status', 'whatsapp_monitor_disable')
        if intent.confidence < CONFIDENCE_THRESHOLD and intent.type not in NO_CONFIRM_INTENTS:
            desc = self._intent_description_for_confirm(intent.type)
            return (
                f"Você quer que eu {desc}? (Responda sim para confirmar.)",
                {},
            )

        # 1d. Monitor com dois contatos → perguntar qual primeiro (sem suporte a lista ainda)
        if intent.type == "whatsapp_monitor":
            contact = ((getattr(intent, "entities", None) or {}).get("contact") or "").strip()
            if contact and " e " in contact:
                parts = [p.strip() for p in contact.split(" e ", 1)]
                if len(parts) == 2 and parts[0] and parts[1]:
                    return (
                        f"Posso monitorar um por vez. Qual você quer monitorar primeiro: **{parts[0]}** ou **{parts[1]}**?",
                        {},
                    )

        # 2. Aprende com a mensagem (se módulo de memória disponível)
        if 'memory' in self.modules:
            learned = await self.modules['memory'].learn_from_message(message)
            if learned:
                logger.info(f"🧠 Aprendi: {', '.join(learned)}")

        # 3. Adiciona contexto de memória
        memory_context = ""
        if 'memory' in self.modules:
            memory_context = await self.modules['memory'].get_context_for_ai()

        enriched_context = {**context}
        if memory_context:
            enriched_context['memory'] = memory_context

        # 4. Rotear baseado na intenção
        response, out_meta = await self._route_to_module(
            intent, message, enriched_context, source, metadata
        )

        # 5. Salva conversa
        if 'memory' in self.modules:
            await self.modules['memory'].save_conversation(
                message, response, intent.type
            )

        return response, out_meta or {}

    async def execute_action(
        self,
        intent_type: str,
        entities: Dict,
        message: str,
        context: Dict,
        source: str = "cli",
        metadata: Dict = None,
    ) -> tuple:
        """
        Executa uma ação estruturada (chamado pelo MCP / Jarvis Actions).
        Não aplica confirmação de confiança nem compose message; a IA já decidiu a ação.
        Retorna (response, out_meta).
        """
        from .intent_classifier import Intent

        intent = Intent(
            type=intent_type,
            confidence=1.0,
            entities=dict(entities) if entities else {},
        )
        metadata = metadata or {}
        enriched_context = {**context}
        if "memory" in self.modules:
            try:
                memory_context = await self.modules["memory"].get_context_for_ai()
                if memory_context:
                    enriched_context["memory"] = memory_context
            except Exception as e:
                logger.debug("Memória não disponível para execute_action: %s", e)
        response, out_meta = await self._route_to_module(
            intent, message, enriched_context, source, metadata
        )
        return response, out_meta or {}

    def _intent_description_for_confirm(self, intent_type: str) -> str:
        """Descrição curta da intenção para mensagem de confirmação."""
        descriptions = {
            'conversation': 'responda em conversa',
            'whatsapp_send': 'envie uma mensagem no WhatsApp',
            'whatsapp_reply': 'responda uma mensagem no WhatsApp',
            'whatsapp_read': 'leia as mensagens de um contato',
            'whatsapp_check': 'verifique as mensagens não lidas',
            'whatsapp_monitor': 'monitore um contato',
            'whatsapp_autoreply_enable': 'ative auto-resposta para um contato',
            'whatsapp_autoreply_disable': 'desative auto-resposta para um contato',
            'whatsapp_autopilot_status': 'mostre status do autopilot',
            'whatsapp_autopilot_set_tone': 'mude o tom do autopilot',
            'whatsapp_monitor_status': 'mostre status de monitoramento',
            'whatsapp_monitor_disable': 'cancele o monitoramento',
            'search': 'pesquise na web',
            'app_control': 'execute um aplicativo',
            'reminder': 'crie um lembrete',
            'capabilities': 'liste minhas capacidades',
        }
        return descriptions.get(intent_type, f'execute a ação "{intent_type}"')

    def _user_confirmed_plan(self, msg: str) -> bool:
        """Resposta do usuário indica confirmação (sim, pode, manda, etc.)."""
        confirm = ("sim", "s", "pode", "confirmo", "quero", "pode prosseguir", "manda", "envie", "envia", "ok", "positivo")
        return msg in confirm or msg.startswith(("sim ", "pode "))

    def _has_send_verb(self, message: str) -> bool:
        """True se a mensagem contém verbo de envio (envie, mande, responda). Conversation não compete com isso."""
        msg = (message or "").lower()
        return any(v in msg for v in ("envie", "envia", "enviar", "mande", "manda", "mandar", "responda", "responde"))

    CONTINUATION_TONE_WORDS = frozenset({"fofinho", "fofinha", "carinhoso", "amoroso", "foramto", "formato", "legal", "lindo"})

    def _looks_like_send_continuation(self, message: str) -> bool:
        """Mensagem curta com nome + tom (ex.: 'tchuchuca foramto fofinho') → continuação de envio."""
        msg = (message or "").strip().lower()
        words = [w for w in msg.split() if w.isalpha() and len(w) > 1]
        if len(words) > 6 or len(words) < 2:
            return False
        has_tone = any(w in self.CONTINUATION_TONE_WORDS for w in words)
        has_name_like = any(w not in self.CONTINUATION_TONE_WORDS for w in words)
        return has_tone and has_name_like

    def _extract_name_from_continuation(self, message: str) -> Optional[str]:
        """Extrai nome do contato de mensagem tipo 'tchuchuca foramto fofinho' (primeira palavra que não é tom)."""
        words = (message or "").strip().split()
        for w in words:
            clean = w.strip(".,!?").lower()
            if len(clean) > 1 and clean not in self.CONTINUATION_TONE_WORDS and clean.isalpha():
                return clean.title()
        return None

    def _user_cancelled_plan(self, msg: str) -> bool:
        """Resposta do usuário indica cancelamento."""
        cancel = ("não", "nao", "n", "cancela", "cancelar", "para", "para com isso", "não quero")
        return msg in cancel or msg.startswith(("não ", "nao "))

    def _is_stop_command(self, message: str) -> bool:
        """Comando global de parar: 'para com isso', 'pare', 'cancela', etc. Não depende de classificação."""
        msg = (message or "").strip().lower()
        stop_phrases = ("para com isso", "para com isso.", "para com iso", "para com iso.", "pare", "cancela", "cancelar", "para.", "para!")
        return msg in stop_phrases or msg == "para"

    def _looks_like_direct_question_or_greeting(self, message: str) -> bool:
        """True se a mensagem é pergunta direta ou cumprimento; conversation deve ir direto para a IA."""
        msg = (message or "").strip().lower()
        if msg.endswith("?"):
            return True
        phrases = (
            "como vc está", "como você está", "como está", "vc está", "você está",
            "quantas", "quantos", "consegue fazer", "conversar contigo", "conversar com você",
            "conversar aqui", "responder amigo", "responder amigo",
        )
        return any(p in msg for p in phrases)

    # Palavras que NUNCA fazem parte do nome do contato (só tom/conteúdo/instrução)
    CONTACT_STOP_WORDS = frozenset({
        "modo", "linguagem", "linguame", "declaração", "declaracao", "amor", "mensagem", "mensagnem",
        "formal", "informal", "se", "apresentando", "apresente", "fazendo", "zoando", "ela", "ele", "mais",
        "use", "usar", "pode", "profissional", "amorosa", "que", "uma", "com", "para", "e", "no", "na",
        "de", "do", "da", "pro", "pra", "por", "o", "a", "um", "sobre", "vc", "você", "voce",
        "namorada", "namorado", "minha", "meu", "minhas", "meus", "é", "eh", "dizendo", "falando",
    })

    def _strip_article_from_contact(self, contact: Optional[str]) -> Optional[str]:
        """Remove artigo 'o ' ou 'a ' do início do contato para exibição e envio."""
        if not (contact or "").strip():
            return contact
        c = (contact or "").strip()
        for prefix in ("o ", "a "):
            if c.lower().startswith(prefix):
                c = c[len(prefix):].strip()
                break
        return c if c else contact

    def _extract_contact_for_plan(self, message: str, context: Dict, intent: Intent) -> Optional[str]:
        """Extrai APENAS o contato: nome após 'para', sem tom/conteúdo. Nunca usa texto livre como nome."""
        msg = (message or "").strip()
        # " para ela" / " pra ela" → contexto (monitored ou last)
        m_ela = re.search(r"\b(?:para|pra)\s+(?:ela|ele)\s*$", msg, re.I)
        if m_ela:
            out = (context.get("last_monitored_contact") or context.get("last_contact") or "").strip()
            return self._strip_article_from_contact(out) or None
        # " para Nome" → só palavras que são nome (até primeira stop word); máx 4 palavras
        m = re.search(r"\b(?:para|pra)\s+(.+?)(?:\s*$)", msg, re.I)
        if m:
            segment = m.group(1).strip()
            words = segment.split()
            name_parts = []
            for w in words:
                if w.lower() in self.CONTACT_STOP_WORDS:
                    break
                if len(name_parts) >= 4:
                    break
                name_parts.append(w)
            name = " ".join(name_parts).strip()
            if name and len(name) > 1:
                return self._strip_article_from_contact(name) or name
        # Entidades do classificador (já podem vir limpas)
        entities = getattr(intent, "entities", None) or {}
        contact = (entities.get("contact") or "").strip()
        if contact:
            # Aplica mesma regra: trunca na primeira stop word
            words = contact.split()
            name_parts = []
            for w in words:
                if w.lower() in self.CONTACT_STOP_WORDS:
                    break
                if len(name_parts) >= 4:
                    break
                name_parts.append(w)
            name = " ".join(name_parts).strip()
            if name:
                return self._strip_article_from_contact(name) or name
        last = (context.get("last_contact") or "").strip() or None
        return self._strip_article_from_contact(last) if last else None

    def _extract_contacts_for_plan(self, message: str, context: Dict, intent: Intent) -> List[str]:
        """Extrai lista de contatos para 'para X e Y'. Retorna [X] ou [X, Y]; vazio se nenhum."""
        single = self._extract_contact_for_plan(message, context, intent)
        if not single:
            return []
        msg = (message or "").strip()
        m = re.search(r"\b(?:para|pra)\s+(?:a\s+|o\s+)?(.+?)(?:\s*$)", msg, re.I)
        if not m:
            return [single]
        segment = m.group(1).strip()
        if " e " not in segment:
            return [single]
        parts = re.split(r"\s+e\s+", segment, maxsplit=1)
        if len(parts) < 2:
            return [single]
        contacts = []
        for part in parts:
            part = part.strip()
            words = part.split()
            name_parts = []
            for w in words:
                if w.lower() in self.CONTACT_STOP_WORDS:
                    break
                if len(name_parts) >= 4:
                    break
                name_parts.append(w)
            name = " ".join(name_parts).strip()
            name = self._strip_article_from_contact(name) or name
            if name and len(name) > 1:
                contacts.append(name)
        return contacts if len(contacts) >= 2 else [single]

    def _parse_tone_from_message(self, message: str) -> tuple:
        """Extrai tom/relacionamento/formalidade da mensagem (nunca contato). Retorna (tone, relationship, formality)."""
        msg = (message or "").lower()
        tone, relationship, formality = "", "", ""
        if any(x in msg for x in ("namorada", "namorado", "amorosa", "amor", "fofinha", "fofinho", "declaração de amor", "declaracao de amor")):
            tone = "romantic"
            if "namorada" in msg:
                relationship = "girlfriend"
            elif "namorado" in msg:
                relationship = "boyfriend"
        if "informal" in msg or "mais informal" in msg:
            formality = "informal"
        if "formal" in msg or "profissional" in msg or "modo profissional" in msg:
            formality = "formal"
        if not formality and tone == "romantic":
            formality = "informal"
        return tone, relationship, formality

    def _create_send_compose_plan(self, target_contact: str, message: str = "") -> ExecutionPlan:
        """Cria plano: compor mensagem → enviar para contato fixo. Tom/formalidade vêm da mensagem."""
        tone, relationship, formality = self._parse_tone_from_message(message)
        summary = f"Vou enviar uma mensagem para **{target_contact}**"
        if tone == "romantic" or relationship:
            summary += ", com um tom mais amoroso"
        elif formality == "formal":
            summary += ", de forma profissional"
        elif formality == "informal":
            summary += ", de forma mais informal"
        else:
            summary += ", me apresentando e explicando minhas funções"
        if not summary.endswith("."):
            summary += "."
        return ExecutionPlan(
            target_contact=target_contact,
            steps=[
                {"type": "compose_message"},
                {"type": "whatsapp_send", "use_previous_output": True},
            ],
            status="awaiting_confirmation",
            summary=summary,
            tone=tone,
            relationship=relationship,
            formality=formality,
        )

    async def _execute_plan(
        self, plan: ExecutionPlan, context: Dict, source: str, metadata: Dict
    ) -> tuple:
        """Executa o plano: compor mensagem com IA e enviar para plan.target_contact."""
        contact = (plan.target_contact or "").strip()
        if not contact:
            return "Não foi possível executar: contato não definido no plano.", {}

        # Step 1: compor mensagem (com tom do plano)
        composed = await self._compose_message_via_ai(plan)
        if not composed:
            return "Não consegui gerar a mensagem. Tente novamente.", {}
        plan.composed_message = composed

        # Step 2: enviar via WhatsApp (contato sempre do plano)
        whatsapp = self.modules.get("whatsapp")
        if not whatsapp or not hasattr(whatsapp, "process"):
            return "Módulo WhatsApp indisponível.", {}

        fake_intent = Intent(type="whatsapp_send", confidence=1.0, entities={"contact": contact})
        send_meta = {**(metadata or {}), "composed_message": composed}
        try:
            result = await whatsapp.process(
                message="", intent=fake_intent, context={**context, "last_contact": contact}, metadata=send_meta
            )
            if isinstance(result, tuple) and len(result) >= 2:
                response, out_meta = result[0], (result[1] or {})
            else:
                response, out_meta = result, {}
            plan.status = "executed"
            return response, out_meta
        except Exception as e:
            logger.exception("Erro ao executar plano: %s", e)
            return f"Erro ao enviar: {str(e)}", {}

    def _get_capabilities_response(self) -> str:
        """Retorna texto com as capacidades do JARVIS (para apresentação)."""
        try:
            from pathlib import Path
            path = Path(__file__).parent.parent / "docs" / "CAPACIDADES_JARVIS.md"
            if path.exists():
                return path.read_text(encoding="utf-8").strip()
        except Exception as e:
            logger.debug("Não foi possível carregar CAPACIDADES_JARVIS.md: %s", e)
        return (
            "**JARVIS – Capacidades**\n\n"
            "• **WhatsApp:** enviar e ler mensagens, monitorar contato, resumir conversa, ver não lidas.\n"
            "• **Pesquisa:** buscar na web, clima, notícias.\n"
            "• **Agenda:** lembretes, alarme, compromissos.\n"
            "• **Produtividade:** relatório do dia/semana, sessão de foco.\n"
            "• **Sentimento, backup, segurança, tradução, automação, sistema/arquivos.**\n"
            "• **Conversa:** IA para perguntas e diálogo.\n\n"
            "Documento completo: docs/CAPACIDADES_JARVIS.md"
        )

    def _should_compose_message(self, message: str) -> bool:
        """Verifica se o usuário pediu para montar/criar uma mensagem (apresentação, funções, tom, declaração)."""
        msg = (message or "").lower()
        keywords = [
            "se apresentando", "se apresente", "apresente", "apresentando",
            "suas funções", "suas funcoes", "o que consegue", "consegue fazer",
            "monte uma mensagem", "crie uma mensagem", "faça uma mensagem",
            "sua própria mensagem", "sua propria mensagem", "mensagem sobre você", "mensagem sobre voce",
            "tudo que consegue", "tudo que vc consegue", "o que você consegue", "o que vc consegue",
            "maneira séria", "maneira seria", "profissional", "se apresetnando",
            "declaração de amor", "declaracao de amor", "linguagem amorosa", "linguagem mais amorosa",
            "mais informal", "mais formal", "tom amoroso", "mensagem de amor",
            "fofinha", "fofinho", "mensagem fofinha", "mensagem fofinho",
        ]
        return any(k in msg for k in keywords)

    async def _compose_message_via_ai(self, plan: Optional[ExecutionPlan] = None) -> Optional[str]:
        """Gera mensagem do Jarvis (apresentação/capacidades). Se plan tiver tone/relationship/formality, usa no prompt."""
        base = (
            "Gere uma única mensagem curta em português (máximo 2 ou 3 parágrafos) "
            "para o assistente Jarvis se apresentar e listar suas principais funções/capacidades, "
            "para enviar por WhatsApp. Inclua: cumprimento, quem é o Jarvis, o que ele consegue fazer. "
        )
        if plan:
            if getattr(plan, "tone", None) == "romantic" or getattr(plan, "relationship", None) == "girlfriend":
                base += "Use um tom amoroso e carinhoso, adequado para namorada. "
            elif getattr(plan, "formality", None) == "formal":
                base += "Seja profissional e formal. "
            elif getattr(plan, "formality", None) == "informal":
                base += "Seja cordial e informal, sem ser frio. "
            else:
                base += "Seja cordial, objetivo e direto. "
        else:
            base += "Seja cordial, objetivo e direto. "
        base += "Responda só com o texto da mensagem, sem título ou explicação."
        try:
            ai_module = self.modules.get('ai')
            if not ai_module or not hasattr(ai_module, 'process'):
                logger.debug("no_response: _compose_message_via_ai reason=no_ai_module")
                return None
            result = await ai_module.process(
                message=base,
                intent=Intent(type='conversation', confidence=1.0, entities={}),
                context={},
                metadata={}
            )
            if isinstance(result, tuple):
                text = result[0]
            else:
                text = result
            composed = (text or "").strip()[:2000] or None
            if composed is None:
                logger.debug("no_response: _compose_message_via_ai reason=empty_text")
            return composed
        except Exception as e:
            logger.warning("Falha ao gerar mensagem com IA: %s", e)
            logger.debug("no_response: _compose_message_via_ai reason=exception")
            return None

    async def _route_to_module(
        self, intent: Intent, message: str, context: Dict, source: str, metadata: Dict
    ) -> tuple:
        """Roteia para o módulo apropriado. Retorna (resposta, metadata)."""
        # Mapeamento intenção -> módulo
        intent_to_module = {
            'search': 'search',
            'weather': 'search',
            'news': 'search',
            'whatsapp_send': 'whatsapp',
            'whatsapp_autoreply_enable': 'whatsapp',
            'whatsapp_autoreply_disable': 'whatsapp',
            'whatsapp_autopilot_status': 'whatsapp',
            'whatsapp_autopilot_summary': 'whatsapp',
            'whatsapp_autopilot_set_tone': 'whatsapp',
            'whatsapp_monitor_status': 'whatsapp',
            'whatsapp_monitor_disable': 'whatsapp',
            'whatsapp_check': 'whatsapp',
            'whatsapp_read': 'whatsapp',
            'whatsapp_monitor': 'whatsapp',
            'whatsapp_reply': 'whatsapp',
            'reminder': 'calendar',
            'alarm': 'calendar',
            'schedule': 'calendar',
            'file_operation': 'tools',
            'system_command': 'tools',
            'system_info': 'tools',
            'app_control': 'tools',
            'conversation': 'ai',
            'conversation_question': 'ai',
            'question': 'ai',
            'unknown': 'ai',
            'sentiment': 'sentiment',
            'productivity': 'productivity',
            'backup': 'backup',
            'security': 'security',
            'translation': 'translation',
            'automation': 'automation',
        }
        
        # Resposta fixa para "o que você consegue fazer" / capacidades (para apresentação ao time)
        if intent.type == 'capabilities':
            return self._get_capabilities_response(), {}

        module_name = intent_to_module.get(intent.type, 'ai')

        # Se intenção é enviar ou responder mensagem e o usuário pediu "montar/apresentar/sério e profissional", gera texto com IA
        if intent.type in ('whatsapp_send', 'whatsapp_reply') and 'ai' in self.modules:
            if self._should_compose_message(message):
                composed = await self._compose_message_via_ai()
                if composed:
                    metadata = {**(metadata or {}), 'composed_message': composed}

        # Se módulo não disponível, usa IA
        if module_name not in self.modules:
            module_name = 'ai'

        module = self.modules.get(module_name)

        if not module:
            return "Desculpe, não consigo processar isso no momento.", {}

        try:
            out_meta = {}
            if hasattr(module, 'process'):
                req_meta = {**(metadata or {}), 'source': source}
                result = await module.process(
                    message=message,
                    intent=intent,
                    context=context,
                    metadata=req_meta
                )
                if isinstance(result, tuple) and len(result) >= 2:
                    response, out_meta = result[0], (result[1] or {})
                else:
                    response = result
                if response is None:
                    logger.debug(
                        "no_response: _route_to_module module_returned_none module=%s intent=%s",
                        module_name, intent.type,
                    )
            elif hasattr(module, 'generate'):
                profile = metadata.get('profile', {})
                response, _ = module.generate(
                    profile, message, '', context.get('history', [])
                )
            else:
                response = "Módulo não implementa processamento."

            out_meta["last_intent"] = intent.type
            return response, out_meta

        except Exception as e:
            logger.error(f"Erro no módulo {module_name}: {e}")

            if module_name != 'ai' and 'ai' in self.modules:
                return await self._route_to_module(
                    Intent(type='conversation', confidence=0.5, entities={}),
                    message, context, source, metadata
                )

            return f"Desculpe, ocorreu um erro ao processar: {str(e)}", {}
    
    async def check_proactive(self) -> Optional[Dict]:
        """
        Verifica se há ações proativas a executar
        
        Returns:
            Dict com ação proativa ou None
        """
        now = datetime.now()
        
        # Verifica lembretes agendados
        for task in self._scheduled_tasks:
            if task['time'] <= now and not task.get('executed'):
                task['executed'] = True
                return {
                    'type': 'reminder',
                    'message': task['message'],
                    'source': task.get('source', 'system')
                }
        
        # Verifica módulos por ações proativas
        for name, module in self.modules.items():
            if hasattr(module, 'check_proactive'):
                try:
                    proactive = await module.check_proactive()
                    if proactive:
                        return proactive
                except Exception as e:
                    logger.debug(f"Erro verificando proativo em {name}: {e}")
        
        return None
    
    def schedule_task(self, time: datetime, message: str, source: str = 'user'):
        """Agenda uma tarefa proativa"""
        self._scheduled_tasks.append({
            'time': time,
            'message': message,
            'source': source,
            'executed': False
        })
        logger.info(f"⏰ Tarefa agendada para {time}: {message[:50]}...")
    
    async def _task_worker(self):
        """Worker para processar fila de tarefas assíncronas"""
        while self._running:
            try:
                task = await asyncio.wait_for(
                    self._task_queue.get(),
                    timeout=1.0
                )
                
                # Processa tarefa
                await self._execute_task(task)
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no worker: {e}")
    
    async def _execute_task(self, task: Dict):
        """Executa uma tarefa da fila"""
        task_type = task.get('type')
        
        if task_type == 'module_call':
            module = self.modules.get(task['module'])
            if module and hasattr(module, task['method']):
                method = getattr(module, task['method'])
                await method(**task.get('kwargs', {}))
    
    def get_modules_status(self) -> Dict[str, str]:
        """Retorna status de todos os módulos"""
        status = {}
        for name, module in self.modules.items():
            if hasattr(module, 'status'):
                status[name] = module.status
            elif hasattr(module, 'is_available'):
                status[name] = '🟢' if module.is_available() else '🔴'
            else:
                status[name] = '🟢'
        return status
