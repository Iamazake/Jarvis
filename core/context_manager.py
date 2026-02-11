# -*- coding: utf-8 -*-
"""
Context Manager - Gerenciador de Contexto
Mantém histórico e contexto da conversa

Autor: JARVIS Team
Versão: 3.0.0
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import deque, OrderedDict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── Storage path único: JARVIS_DATA_DIR (obrigatório para consistência com Node/WhatsApp) ──
# Defina JARVIS_DATA_DIR no .env (ex: C:\YAmazake\jarvis\data) para que Python e Node leiam o mesmo context_state.json.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = Path(os.getenv('JARVIS_DATA_DIR', '').strip() or str(_REPO_ROOT / 'data')).resolve()
CONTEXT_STATE_FILENAME = 'context_state.json'
# Log de diagnóstico do agente (jarvis/debug_agent.log quando cwd=jarvis)
DEBUG_AGENT_LOG = Path(__file__).resolve().parent.parent / "debug_agent.log"


class LRUCache(OrderedDict):
    """Cache com tamanho máximo; remove o item menos recentemente usado ao exceder."""

    def __init__(self, maxsize: int = 500, *args, **kwargs):
        self.maxsize = maxsize
        super().__init__(*args, **kwargs)

    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        super().__setitem__(key, value)
        if len(self) > self.maxsize:
            self.popitem(last=False)


@dataclass
class Message:
    """Representa uma mensagem no histórico"""
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = 'cli'  # 'cli', 'voice', 'whatsapp'
    metadata: Dict = field(default_factory=dict)


class ContextManager:
    """
    Gerencia o contexto da conversa
    
    Funcionalidades:
    - Histórico de mensagens (últimas N)
    - Contexto de curto prazo (sessão)
    - Referências a entidades mencionadas
    - Estado de fluxos em andamento
    """
    
    def __init__(self, max_history: int = 20, context_ttl_minutes: int = 30, lru_maxsize: int = 500):
        self.max_history = max_history
        self.context_ttl = timedelta(minutes=context_ttl_minutes)
        
        # Persistência: usa _DATA_DIR (env JARVIS_DATA_DIR ou <repo>/data) — path absoluto único
        self._persistence_file = _DATA_DIR / CONTEXT_STATE_FILENAME
        
        # Histórico de mensagens (FIFO)
        self.messages: deque = deque(maxlen=max_history)
        
        # Contexto da sessão atual
        self._session_context: Dict[str, Any] = {}
        
        # Entidades mencionadas (nomes, lugares, etc)
        self._entities: Dict[str, Any] = {}
        
        # Última intenção detectada
        self._last_intent: Optional[str] = None
        
        # Último contato mencionado (para "monitore a conversa dele", "responde pra ele")
        self._last_contact: Optional[str] = None
        self._last_contact_at: Optional[datetime] = None

        # Contatos que o usuário pediu para monitorar nesta sessão ("resuma do contato que pedi pra monitorar")
        self._monitored_contacts: List[str] = []
        # JID do último contato monitorado (para "quando ela mandar" ativar autopilot pelo JID certo)
        self._last_monitored_jid: Optional[str] = None
        # Alvo ativo único: substituído a cada "monitore X" ou "autopilot para X" (evita "ela" = Douglas quando acabou de monitorar Tchuchuca)
        self._active_target_jid: Optional[str] = None
        self._active_target_name: Optional[str] = None

        # Cache LRU de últimas mensagens por contato (evita crescimento ilimitado)
        # {"nome_ou_jid": {"text": "...", "timestamp": datetime, "from_me": False}}
        self._last_message_by_contact: LRUCache = LRUCache(maxsize=lru_maxsize)

        # Autopilot por JID (ou nome legado): key = jid normalizado ou nome_lower; alias nome_lower -> jid
        self._autopilot_contacts: Dict[str, Dict[str, Any]] = {}
        self._autopilot_alias: Dict[str, str] = {}  # name_lower -> normalized_jid (ou key legado)

        # JID real por nome: atualizado quando o webhook recebe mensagem (display_name -> jid do evento)
        # Garante que "ative autopilot para X" use o mesmo JID que o webhook recebe
        self._contact_jid_by_name: Dict[str, str] = {}  # name_lower -> normalized_jid

        # Últimas N mensagens por JID (WhatsApp) para contexto da IA; persistido em disco
        self._conversation_history_per_jid: Dict[str, List[Dict[str, str]]] = {}  # jid -> [{role, content}, ...]
        self._max_conversation_per_jid: int = 8  # últimas 8 mensagens (4 pares user/assistant)
        self._current_whatsapp_jid: Optional[str] = None  # JID da conversa atual (setado em run_jarvis_message)

        # Flag: narrar ações enquanto executa (estilo Stark)
        self._explain_actions: bool = True
        
        # Plano de execução pendente (confirmação única: "Posso prosseguir?" → sim executa)
        self._pending_plan: Optional[Any] = None

        # Fluxos em andamento
        self._active_flows: Dict[str, Dict] = {}
        
        # Timestamp da última interação
        self._last_interaction: datetime = datetime.now()
        
        self._load_state()
        logger.debug("ContextManager storage_path=%s", self._persistence_file)

    @property
    def storage_path(self) -> str:
        """Caminho absoluto do arquivo de persistência (útil para diagnóstico)."""
        return str(self._persistence_file)
    
    def _load_state(self):
        """Carrega monitored_contacts, last_messages e autopilot_contacts do disco."""
        path = str(self._persistence_file)
        if not self._persistence_file.exists():
            logger.warning("context_state_read path=%s file_missing=1 (assumindo OFF para todos)", path)
            return
        try:
            data = json.loads(self._persistence_file.read_text(encoding="utf-8"))
            self._monitored_contacts = list(data.get("monitored_contacts", []))
            for key, val in data.get("last_messages", {}).items():
                ts = val.get("timestamp")
                if isinstance(ts, str):
                    try:
                        val = {**val, "timestamp": datetime.fromisoformat(ts)}
                    except (ValueError, TypeError):
                        val = {**val, "timestamp": datetime.now()}
                self._last_message_by_contact[key] = val
            now = datetime.now()
            enabled_jids = []
            for key, val in data.get("autopilot_contacts", {}).items():
                expires = val.get("expires_at")
                if isinstance(expires, str):
                    try:
                        expires = datetime.fromisoformat(expires)
                    except (ValueError, TypeError):
                        expires = now
                if expires and expires > now:
                    self._autopilot_contacts[key] = {**val, "expires_at": expires}
                    if val.get("enabled", True):
                        exp_iso = expires.isoformat() if hasattr(expires, 'isoformat') else str(expires) if expires else None
                        enabled_jids.append((key, exp_iso))
            self._autopilot_alias = dict(data.get("autopilot_alias", {}))
            self._last_monitored_jid = data.get("last_monitored_jid") or None
            self._active_target_jid = data.get("active_target_jid") or None
            self._active_target_name = data.get("active_target_name") or None
            self._contact_jid_by_name = dict(data.get("contact_jid_by_name", {}))
            # Histórico de conversa por JID (últimas N por contato)
            for jid, msgs in data.get("conversation_by_jid", {}).items():
                if isinstance(msgs, list) and msgs:
                    self._conversation_history_per_jid[jid] = msgs[-self._max_conversation_per_jid:]
            logger.info("context_state_read path=%s enabled_jids=%s", path, enabled_jids)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Não foi possível carregar context_state path=%s: %s", path, e)
    
    def _save_state(self):
        """Persiste monitored_contacts e last_messages em disco."""
        path = str(self._persistence_file)
        try:
            self._persistence_file.parent.mkdir(parents=True, exist_ok=True)
            autopilot_ser = {}
            enabled_list = []
            for k, v in self._autopilot_contacts.items():
                exp = v.get("expires_at")
                autopilot_ser[k] = {
                    "enabled": v.get("enabled", True),
                    "tone": v.get("tone", "fofinho"),
                    "expires_at": exp,
                    "created_at": v.get("created_at"),
                    "display_name": v.get("display_name"),
                }
                if v.get("enabled", True):
                    exp_iso = exp.isoformat() if hasattr(exp, 'isoformat') and exp else str(exp) if exp else None
                    enabled_list.append((k, exp_iso))
            data = {
                "monitored_contacts": self._monitored_contacts,
                "last_monitored_jid": self._last_monitored_jid,
                "active_target_jid": self._active_target_jid,
                "active_target_name": self._active_target_name,
                "autopilot_contacts": autopilot_ser,
                "autopilot_alias": self._autopilot_alias,
                "contact_jid_by_name": self._contact_jid_by_name,
                "last_messages": {
                    k: {
                        "text": v.get("text", ""),
                        "timestamp": v.get("timestamp", datetime.now()),
                        "from_me": v.get("from_me", False),
                    }
                    for k, v in self._last_message_by_contact.items()
                },
                "conversation_by_jid": dict(
                    list({
                        jid: list(msgs[-self._max_conversation_per_jid:])
                        for jid, msgs in self._conversation_history_per_jid.items()
                    }.items())[-100:]  # mantém só os 100 JIDs mais recentes
                ),
            }
            self._persistence_file.write_text(
                json.dumps(data, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
            logger.info("context_state_write path=%s jid_enabled=%s", path, enabled_list)
        except OSError as e:
            logger.warning("Não foi possível salvar context_state path=%s: %s", path, e)
    
    def add_message(self, role: str, content: str, source: str = 'cli',
                    metadata: Dict = None):
        """Adiciona mensagem ao histórico. Se source=whatsapp e metadata.jid, também no histórico por JID."""
        msg = Message(
            role=role,
            content=content,
            source=source,
            metadata=metadata or {}
        )
        self.messages.append(msg)
        self._last_interaction = datetime.now()

        if source == 'whatsapp' and metadata and metadata.get('jid'):
            jid = str(metadata['jid']).strip()
            if jid:
                self._conversation_history_per_jid.setdefault(jid, [])
                self._conversation_history_per_jid[jid].append({'role': role, 'content': content})
                self._conversation_history_per_jid[jid] = self._conversation_history_per_jid[jid][-self._max_conversation_per_jid:]
                self._save_state()

        # Limpa contexto se passou muito tempo
        self._check_context_expiry()
    
    def get_context(self) -> Dict:
        """Retorna contexto completo para processamento. Para WhatsApp usa últimas 8 msgs do JID atual."""
        max_hist = self._max_conversation_per_jid if self._current_whatsapp_jid else 10
        history = self.get_history_for_ai(max_messages=max_hist, jid=self._current_whatsapp_jid)
        return {
            'history': history,
            'last_intent': self._last_intent,
            'last_contact': self._last_contact,
            'monitored_contacts': list(self._monitored_contacts),
            'last_monitored_contact': self.get_last_monitored_contact(),
            'last_monitored_jid': self._last_monitored_jid,
            'active_target_jid': self._active_target_jid,
            'active_target_name': self._active_target_name,
            'contact_jid_by_name': self._contact_jid_by_name.copy(),
            'autopilot_list': self.list_autopilot(),
            'entities': self._entities.copy(),
            'session': self._session_context.copy(),
            'active_flows': list(self._active_flows.keys()),
            'message_count': len(self.messages),
            'last_messages': self.get_all_last_messages(),
            'explain_actions': self._explain_actions,
            'pending_plan': self._pending_plan,
        }
    
    def get_history_for_ai(self, max_messages: int = 10, jid: Optional[str] = None) -> List[Dict]:
        """
        Retorna histórico formatado para a IA (formato OpenAI).
        Se jid for passado e houver histórico para esse JID (WhatsApp), usa as últimas max_messages.
        """
        if jid and self._conversation_history_per_jid.get(jid):
            msgs = self._conversation_history_per_jid[jid][-max_messages:]
            return [{'role': m['role'], 'content': m['content']} for m in msgs]
        history = []
        messages = list(self.messages)[-max_messages:]
        for msg in messages:
            history.append({'role': msg.role, 'content': msg.content})
        return history

    def set_current_whatsapp_jid(self, jid: Optional[str]) -> None:
        """Define o JID da conversa WhatsApp atual (para get_context usar histórico desse contato)."""
        self._current_whatsapp_jid = (jid or '').strip() or None
    
    def set_last_intent(self, intent: str):
        """Define última intenção detectada"""
        self._last_intent = intent

    def set_last_contact(self, contact: str):
        """Define último contato mencionado (nome ou jid) para referências como 'dele', 'ele'."""
        if contact:
            self._last_contact = contact
            self._last_contact_at = datetime.now()
            logger.debug("last_contact definido: %s", contact)

    def get_last_contact(self) -> Optional[str]:
        """Retorna o último contato mencionado na conversa."""
        return self._last_contact

    def add_monitored_contact(self, name_or_jid: str):
        """Registra contato que o usuário pediu para monitorar (para resolver 'do contato que pedi pra monitorar')."""
        if name_or_jid and name_or_jid not in self._monitored_contacts:
            self._monitored_contacts.append(name_or_jid)
            logger.debug("monitored_contact adicionado: %s", name_or_jid)
            self._save_state()

    def get_monitored_contacts(self) -> List[str]:
        """Retorna lista de contatos que o usuário pediu para monitorar nesta sessão."""
        return list(self._monitored_contacts)

    def get_last_monitored_contact(self) -> Optional[str]:
        """Retorna o último contato adicionado ao monitoramento (ou o único, se houver só um)."""
        if not self._monitored_contacts:
            return None
        return self._monitored_contacts[-1]

    def remove_monitored_contact(self, name_or_jid: str) -> bool:
        """Remove contato da lista de monitorados. Retorna True se estava na lista."""
        if not name_or_jid:
            return False
        key_lower = (name_or_jid or "").strip().lower()
        before = len(self._monitored_contacts)
        self._monitored_contacts = [
            c for c in self._monitored_contacts
            if (c or "").strip().lower() != key_lower
        ]
        removed = before > len(self._monitored_contacts)
        if removed:
            if not self._monitored_contacts:
                self._last_monitored_jid = None
            an = (self._active_target_name or "").strip().lower()
            if an == key_lower:
                self._active_target_jid = None
                self._active_target_name = None
            self._save_state()
            logger.debug("monitored_contact removido: %s", name_or_jid.strip())
        return removed

    # ── Plano de execução (confirmação única, contato travado) ──

    def set_pending_plan(self, plan: Any):
        """Define plano pendente de confirmação. NUNCA reclassificar intenção enquanto houver plano."""
        self._pending_plan = plan
        logger.debug("pending_plan definido: %s", getattr(plan, "plan_id", plan))

    def get_pending_plan(self) -> Optional[Any]:
        """Retorna o plano pendente (ExecutionPlan ou None)."""
        return self._pending_plan

    def clear_pending_plan(self):
        """Limpa plano pendente após execução ou cancelamento."""
        self._pending_plan = None
        logger.debug("pending_plan limpo")
    
    # ── Cache de últimas mensagens por contato ──

    def update_last_message(self, contact: str, text: str, from_me: bool = False):
        """Atualiza cache da última mensagem de/para um contato."""
        self._last_message_by_contact[contact.lower()] = {
            'text': text,
            'timestamp': datetime.now(),
            'from_me': from_me,
        }
        logger.debug("last_message atualizado para %s: %s...", contact, text[:40])
        self._save_state()

    def get_last_message(self, contact: str) -> Optional[Dict[str, Any]]:
        """Retorna última mensagem de um contato (ou None)."""
        return self._last_message_by_contact.get(contact.lower())

    def get_all_last_messages(self) -> Dict[str, Dict[str, Any]]:
        """Retorna dict completo de últimas mensagens."""
        return dict(self._last_message_by_contact)

    # ── Autopilot (auto-resposta por contato com TTL; identidade por JID) ──

    def _normalize_jid(self, jid: str) -> str:
        """
        JID único: lowercase, strip.
        Converte formato LID (Baileys) para padrão: 5511...:XX@lid -> 5511...@s.whatsapp.net,
        para que autopilot reconheça a mesma pessoa mesmo quando o webhook envia @lid.
        """
        if not jid or "@" not in jid:
            return ""
        raw = jid.strip().lower()
        if raw.endswith("@lid") and ":" in raw:
            number = raw.split(":")[0].lstrip("+")
            if number.isdigit():
                raw = f"{number}@s.whatsapp.net"
        return raw

    def normalize_jid(self, jid: str) -> str:
        """Normaliza JID para uso consistente (expõe _normalize_jid, ex.: LID -> @s.whatsapp.net)."""
        return self._normalize_jid(jid) if jid else ""

    def _normalize_contact_key(self, contact: str) -> str:
        """Chave única para contato (nome ou JID) — legado e compat."""
        if not contact:
            return ""
        return contact.strip().lower()

    def _autopilot_lookup_key(self, identifier: str) -> Optional[str]:
        """Retorna a chave em _autopilot_contacts para este identifier (JID ou nome)."""
        if not identifier:
            return None
        raw = identifier.strip()
        key_lower = raw.lower()
        if "@" in raw:
            out = self._normalize_jid(raw) or None
            # #region agent log
            try:
                import json as _j; open(DEBUG_AGENT_LOG, 'a', encoding='utf-8').write(_j.dumps({"location": "context_manager._autopilot_lookup_key", "message": "jid_lookup", "data": {"identifier": identifier[:80], "key_found": (out[:50] if out else None)}, "timestamp": __import__("time").time() * 1000, "hypothesisId": "H1_H4"}) + "\n")
            except Exception:
                pass
            # #endregion
            return out
        if key_lower in self._autopilot_alias:
            out = self._autopilot_alias[key_lower]
            # #region agent log
            try:
                import json as _j; open(DEBUG_AGENT_LOG, 'a', encoding='utf-8').write(_j.dumps({"location": "context_manager._autopilot_lookup_key", "message": "alias_hit", "data": {"identifier": identifier[:80], "key_found": (out[:50] if out else None)}, "timestamp": __import__("time").time() * 1000, "hypothesisId": "H1"}) + "\n")
            except Exception:
                pass
            # #endregion
            return out
        out = key_lower if key_lower in self._autopilot_contacts else None
        # #region agent log
        try:
            import json as _j; open(DEBUG_AGENT_LOG, 'a', encoding='utf-8').write(_j.dumps({"location": "context_manager._autopilot_lookup_key", "message": "name_lookup", "data": {"identifier": identifier[:80], "key_lower": key_lower[:50], "key_found": (out[:50] if out else None), "in_contacts": key_lower in self._autopilot_contacts}, "timestamp": __import__("time").time() * 1000, "hypothesisId": "H1"}) + "\n")
        except Exception:
            pass
        # #endregion
        return out

    def enable_autopilot(
        self,
        jid: str,
        display_name: Optional[str] = None,
        tone: str = "fofinho",
        ttl_minutes: int = 120,
    ) -> None:
        """Ativa autopilot para um contato por JID (identidade estável). Nome só para exibição/alias.
        Se receber só nome (sem @) e já tivermos JID em contact_jid_by_name, grava por JID para match futuro.
        Para grupos (@g.us): autopilot só é ativado quando o usuário pedir explicitamente (ex.: ative autopilot para o grupo X)."""
        if jid and "@" not in jid:
            existing_jid = self.get_jid_for_contact(jid)
            if existing_jid:
                display_name = display_name or jid
                jid = existing_jid
        key = self._normalize_jid(jid) if jid and "@" in jid else self._normalize_contact_key(jid)
        if not key:
            return
        now = datetime.now()
        expires_at = now + timedelta(minutes=ttl_minutes)
        self._autopilot_contacts[key] = {
            "enabled": True,
            "tone": tone or "fofinho",
            "expires_at": expires_at,
            "created_at": now,
            "display_name": display_name or key,
        }
        if display_name:
            name_lower = display_name.strip().lower()
            self._autopilot_alias[name_lower] = key
            if name_lower in self._autopilot_contacts and name_lower != key:
                del self._autopilot_contacts[name_lower]
        logger.info("Autopilot ativado para %s (jid=%s, tom=%s, TTL=%s min)", display_name or key, key, tone, ttl_minutes)
        self._save_state()

    def disable_autopilot(self, contact: str) -> tuple:
        """Desativa autopilot para um contato (JID ou nome). Retorna (True, removed_info) se estava ativo, (False, None) caso contrário. removed_info = {jid, created_at} para gerar resumo."""
        key = self._autopilot_lookup_key(contact)
        if not key:
            key = self._normalize_contact_key(contact)
        if key and key in self._autopilot_contacts:
            entry = self._autopilot_contacts[key]
            created_at = entry.get("created_at")
            removed_info = {"jid": key, "created_at": created_at} if ("@" in key) else None
            del self._autopilot_contacts[key]
            for k, v in list(self._autopilot_alias.items()):
                if v == key:
                    del self._autopilot_alias[k]
            self._save_state()
            logger.info("Autopilot desativado para %s", contact)
            return True, removed_info
        return False, None

    def get_autopilot(self, contact: str) -> Optional[Dict[str, Any]]:
        """Retorna config do autopilot para o contato (JID ou nome) ou None se desativado/expirado."""
        key = self._autopilot_lookup_key(contact)
        if not key:
            key = self._normalize_contact_key(contact)
        entry = self._autopilot_contacts.get(key) if key else None
        if not entry or not entry.get("enabled"):
            return None
        expires = entry.get("expires_at")
        if isinstance(expires, datetime) and expires < datetime.now():
            del self._autopilot_contacts[key]
            self._save_state()
            return None
        return entry

    def refresh_autopilot_ttl(self, jid: str, ttl_minutes: int = 120) -> bool:
        """
        Renova o TTL do autopilot para o JID quando o contato envia mensagem.
        Evita que o autopilot expire no meio da conversa (evidência: debug log return_false_after_jid_loop
        com key_found mas get_autopilot retornando None por entrada já expirada).
        Retorna True se havia entrada e foi renovada.
        """
        if not jid or "@" not in jid:
            return False
        key = self._normalize_jid(jid)
        if not key or key not in self._autopilot_contacts:
            return False
        entry = self._autopilot_contacts[key]
        if not entry.get("enabled"):
            return False
        now = datetime.now()
        expires = entry.get("expires_at")
        if isinstance(expires, datetime) and expires < now:
            return False
        entry["expires_at"] = now + timedelta(minutes=ttl_minutes)
        self._save_state()
        logger.debug("Autopilot TTL renovado para %s (+%s min)", key[:30], ttl_minutes)
        return True

    def is_autopilot_enabled_for(self, identifier: str) -> bool:
        """
        True se autopilot está ativo para este contato (JID ou nome).
        Unifica mesma pessoa: se o identifier for JID e não estiver em autopilot,
        verifica se algum nome que aponta para esse JID (contact_jid_by_name) tem autopilot
        (ex.: Tchuchuca e Dhyellen são a mesma pessoa com dois nomes).
        Também considera match por substring: autopilot "Dhyellen" bate com pushName "Dhyellen Moreira".
        """
        # #region agent log
        _debug_log = str(DEBUG_AGENT_LOG)
        # #endregion
        direct = self.get_autopilot(identifier)
        if direct is not None:
            # #region agent log
            try:
                import json as _j; open(_debug_log, 'a', encoding='utf-8').write(_j.dumps({"location": "context_manager.is_autopilot_enabled_for", "message": "direct_hit", "data": {"identifier": (identifier or "")[:80], "has_at": "@" in (identifier or "")}, "timestamp": __import__("time").time() * 1000, "hypothesisId": "H1"}) + "\n")
            except Exception:
                pass
            # #endregion
            return True
        has_at = "@" in (identifier or "")
        if not identifier or not has_at:
            # #region agent log
            try:
                import json as _j; open(_debug_log, 'a', encoding='utf-8').write(_j.dumps({"location": "context_manager.is_autopilot_enabled_for", "message": "return_false_no_jid_path", "data": {"identifier": (identifier or "")[:80], "reason": "identifier_has_no_at"}, "timestamp": __import__("time").time() * 1000, "hypothesisId": "H1"}) + "\n")
            except Exception:
                pass
            # #endregion
            return False
        jid_norm = self._normalize_jid(identifier)
        if not jid_norm:
            # #region agent log
            try:
                import json as _j; open(_debug_log, 'a', encoding='utf-8').write(_j.dumps({"location": "context_manager.is_autopilot_enabled_for", "message": "return_false_jid_norm_empty", "data": {"identifier": identifier[:80]}, "timestamp": __import__("time").time() * 1000, "hypothesisId": "H4"}) + "\n")
            except Exception:
                pass
            # #endregion
            return False
        for name, stored_jid in self._contact_jid_by_name.items():
            if self._normalize_jid(stored_jid) != jid_norm:
                continue
            if self.get_autopilot(name) is not None:
                return True
            # Match por substring: autopilot ativado para "dhyellen" e pushName "dhyellen moreira"
            for ap_key, entry in self._autopilot_contacts.items():
                if "@" in ap_key or not entry.get("enabled"):
                    continue
                if ap_key in name or name in ap_key:
                    if self.get_autopilot(ap_key) is not None:
                        # #region agent log
                        try:
                            import json as _j; open(DEBUG_AGENT_LOG, 'a', encoding='utf-8').write(_j.dumps({"location": "context_manager.is_autopilot_enabled_for", "message": "substring_match", "data": {"identifier": identifier[:80], "name": name[:50], "ap_key": ap_key[:50]}, "timestamp": __import__("time").time() * 1000, "hypothesisId": "H1"}) + "\n")
                        except Exception:
                            pass
                        # #endregion
                        return True
        # #region agent log
        try:
            import json as _j; open(_debug_log, 'a', encoding='utf-8').write(_j.dumps({"location": "context_manager.is_autopilot_enabled_for", "message": "return_false_after_jid_loop", "data": {"identifier": identifier[:80], "jid_norm": (jid_norm or "")[:50]}, "timestamp": __import__("time").time() * 1000, "hypothesisId": "H1_H4"}) + "\n")
        except Exception:
            pass
        # #endregion
        return False

    def list_autopilot(self) -> List[Dict[str, Any]]:
        """Lista contatos com autopilot ativo (expira os vencidos). Uma entrada por JID (dedupe por jid)."""
        now = datetime.now()
        result = []
        to_remove = []
        seen_jids = set()
        for key, entry in self._autopilot_contacts.items():
            if not entry.get("enabled"):
                to_remove.append(key)
                continue
            expires = entry.get("expires_at")
            if isinstance(expires, datetime) and expires < now:
                to_remove.append(key)
                continue
            jid = key if ("@" in key) else self._autopilot_alias.get(key)
            if jid and jid in seen_jids:
                continue
            if jid:
                seen_jids.add(jid)
            result.append({
                "contact": entry.get("display_name") or key,
                "tone": entry.get("tone", "fofinho"),
                "expires_at": expires,
            })
        for k in to_remove:
            del self._autopilot_contacts[k]
        if to_remove:
            self._save_state()
        return result

    def set_last_monitored_jid(self, jid: Optional[str]) -> None:
        """Define o JID do último contato que o usuário pediu para monitorar."""
        self._last_monitored_jid = self._normalize_jid(jid) if (jid and "@" in jid) else (jid or None)

    def get_last_monitored_jid(self) -> Optional[str]:
        """Retorna o JID do último contato monitorado."""
        return self._last_monitored_jid

    def set_active_target(self, jid: Optional[str], name: Optional[str]) -> None:
        """Define o alvo ativo único (substitui a cada 'monitore X' ou 'autopilot para X'). Usado para pronome 'ela/ele'."""
        self._active_target_jid = self._normalize_jid(jid) if (jid and "@" in jid) else (jid or None)
        self._active_target_name = (name or "").strip() or None
        if self._active_target_jid or self._active_target_name:
            logger.debug("active_target definido: jid=%s name=%s", self._active_target_jid, self._active_target_name)
        self._save_state()

    def get_active_target(self) -> tuple:
        """Retorna (active_target_jid, active_target_name)."""
        return (self._active_target_jid, self._active_target_name)

    def update_contact_seen(self, jid: str, display_name: Optional[str] = None) -> None:
        """
        Atualiza o índice nome -> JID quando o webhook recebe uma mensagem.
        Assim, ao ativar autopilot por nome, usamos o mesmo JID que o API recebe.
        Regra de ouro: display_name_normalizado -> jid_real_do_evento.
        """
        if not jid or "@" not in jid:
            return
        normalized_jid = self._normalize_jid(jid)
        if not normalized_jid:
            return
        if display_name:
            key = display_name.strip().lower()
            if key:
                self._contact_jid_by_name[key] = normalized_jid
                logger.debug("contact_seen: %s -> %s", key, normalized_jid)
                # #region agent log
                try:
                    import json as _j; open(DEBUG_AGENT_LOG, 'a', encoding='utf-8').write(_j.dumps({"location": "context_manager.update_contact_seen", "message": "contact_seen", "data": {"jid": normalized_jid[:50], "display_name": key[:50]}, "timestamp": __import__("time").time() * 1000, "hypothesisId": "H3"}) + "\n")
                except Exception:
                    pass
                # #endregion
        self._save_state()

    def get_jid_for_contact(self, name: str) -> Optional[str]:
        """Retorna o JID já visto para este nome (webhook), ou None."""
        if not name:
            return None
        key = name.strip().lower()
        return self._contact_jid_by_name.get(key)

    def update_autopilot_tone(self, contact: str, tone: str) -> bool:
        """Atualiza o tom do autopilot para o contato (JID ou nome). Retorna True se encontrou e atualizou."""
        key = self._autopilot_lookup_key(contact)
        if not key:
            key = self._normalize_contact_key(contact)
        entry = self._autopilot_contacts.get(key) if key else None
        if not entry or not entry.get("enabled"):
            return False
        entry["tone"] = (tone or "fofinho").strip().lower()
        self._save_state()
        logger.info("Tom do autopilot atualizado para %s: %s", contact, tone)
        return True

    # ── Explain Actions (narração Stark) ──

    @property
    def explain_actions(self) -> bool:
        return self._explain_actions

    @explain_actions.setter
    def explain_actions(self, value: bool):
        self._explain_actions = value

    def add_entity(self, entity_type: str, value: Any, confidence: float = 1.0):
        """
        Adiciona entidade ao contexto
        
        Args:
            entity_type: Tipo (contact, location, date, etc)
            value: Valor da entidade
            confidence: Confiança (0-1)
        """
        self._entities[entity_type] = {
            'value': value,
            'confidence': confidence,
            'timestamp': datetime.now()
        }
    
    def get_entity(self, entity_type: str) -> Optional[Any]:
        """Obtém valor de uma entidade"""
        entity = self._entities.get(entity_type)
        if entity:
            return entity['value']
        return None
    
    def start_flow(self, flow_name: str, data: Dict = None):
        """
        Inicia um fluxo de conversa
        
        Flows são usados para diálogos multi-turno
        Ex: "Enviar mensagem" -> "Para quem?" -> "Qual mensagem?"
        """
        self._active_flows[flow_name] = {
            'started': datetime.now(),
            'step': 0,
            'data': data or {}
        }
        logger.debug(f"Flow iniciado: {flow_name}")
    
    def update_flow(self, flow_name: str, step: int = None, data: Dict = None):
        """Atualiza um fluxo ativo"""
        if flow_name in self._active_flows:
            if step is not None:
                self._active_flows[flow_name]['step'] = step
            if data:
                self._active_flows[flow_name]['data'].update(data)
    
    def end_flow(self, flow_name: str) -> Optional[Dict]:
        """Finaliza um fluxo e retorna seus dados"""
        return self._active_flows.pop(flow_name, None)
    
    def get_flow(self, flow_name: str) -> Optional[Dict]:
        """Obtém dados de um fluxo ativo"""
        return self._active_flows.get(flow_name)
    
    def set_session(self, key: str, value: Any):
        """Define valor no contexto da sessão"""
        self._session_context[key] = value
    
    def get_session(self, key: str, default: Any = None) -> Any:
        """Obtém valor do contexto da sessão"""
        return self._session_context.get(key, default)
    
    def _check_context_expiry(self):
        """Verifica se o contexto expirou e limpa se necessário"""
        now = datetime.now()
        
        # Se passou muito tempo, limpa contexto temporário
        if now - self._last_interaction > self.context_ttl:
            self._entities.clear()
            self._active_flows.clear()
            self._last_intent = None
            self._last_contact = None
            self._last_contact_at = None
            self._monitored_contacts.clear()
            self._last_monitored_jid = None
            self._active_target_jid = None
            self._active_target_name = None
            self._autopilot_alias.clear()
            self._pending_plan = None
            self._save_state()
            # NÃO limpa _last_message_by_contact — ele sobrevive a sessão
            logger.debug("Contexto expirado, limpo")

    def clear(self):
        """Limpa todo o contexto"""
        self.messages.clear()
        self._session_context.clear()
        self._entities.clear()
        self._active_flows.clear()
        self._last_intent = None
        self._last_contact = None
        self._last_contact_at = None
        self._monitored_contacts.clear()
        self._last_monitored_jid = None
        self._active_target_jid = None
        self._active_target_name = None
        self._pending_plan = None
        self._last_message_by_contact.clear()
        self._autopilot_contacts.clear()
        self._autopilot_alias.clear()
        self._save_state()
    
    def get_summary(self) -> str:
        """Retorna resumo do contexto atual"""
        return (
            f"Mensagens: {len(self.messages)} | "
            f"Entidades: {len(self._entities)} | "
            f"Flows ativos: {len(self._active_flows)}"
        )
