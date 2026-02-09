# -*- coding: utf-8 -*-
"""
WhatsApp Module - Envio e leitura via API Baileys (localhost:3001)
Usado pelo Orchestrator quando o usuário pede para mandar/ver mensagens.
Resolução de contatos por similaridade (fuzzy) e confirmação inteligente.
"""

import os
import re
import asyncio
import aiohttp
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)

try:
    from core.contact_resolver import resolve_contact, DEFAULT_ACCEPT_THRESHOLD
except ImportError:
    resolve_contact = None
    DEFAULT_ACCEPT_THRESHOLD = 0.75


def _load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent.parent / '.env')
    except Exception:
        pass
    return os.getenv('WHATSAPP_API_URL', 'http://localhost:3001')


class WhatsAppModule:
    """
    Módulo WhatsApp para o Orchestrator.
    Chama a API do serviço Node (Baileys) em localhost:3001.
    """

    def __init__(self, config):
        self.config = config
        self.api_url = _load_env()
        self._contacts_cache: Dict[str, str] = {}
        self._running = False
        self.status = '🔴'

    async def start(self):
        logger.info("📱 Iniciando módulo WhatsApp...")
        self._running = True
        self.status = '🟢'
        logger.info("✅ Módulo WhatsApp pronto (API: %s)", self.api_url)

    async def stop(self):
        self._running = False
        self.status = '🔴'

    async def _api_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        url = f"{self.api_url}{endpoint}"
        try:
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        return await resp.json()
                else:
                    async with session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        return await resp.json()
        except aiohttp.ClientConnectorError as e:
            logger.error("API WhatsApp inacessível: %s", e)
            return {"error": _service_not_running_msg(), "service_down": True}
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            err = str(e).lower()
            if "connection refused" in err or "cannot connect" in err or "timeout" in err:
                return {"error": _service_not_running_msg(), "service_down": True}
            return {"error": str(e)}
        except Exception as e:
            logger.error("Erro API WhatsApp: %s", e)
            return {"error": str(e)}

    async def is_service_available(self) -> bool:
        """Verifica se o serviço WhatsApp está rodando (GET /status com timeout curto)."""
        url = f"{self.api_url}/status"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                    if resp.status != 200:
                        return False
                    data = await resp.json()
                    return data.get("connected", False) or "error" not in data
        except Exception:
            return False

    def _format_phone(self, number: str) -> str:
        phone = ''.join(filter(str.isdigit, number))
        if len(phone) == 11:
            phone = '55' + phone
        elif len(phone) == 9:
            phone = '5511' + phone
        return phone + '@s.whatsapp.net'

    def _contacts_to_list(self, contacts: Any) -> List[Tuple[str, str]]:
        """Converte resposta da API de contatos para lista (jid, nome)."""
        out: List[Tuple[str, str]] = []
        if isinstance(contacts, dict):
            for number, info in contacts.items():
                if isinstance(info, dict):
                    name = (info.get('name') or info.get('pushName') or '').strip()
                    jid = info.get('jid', f'{number}@s.whatsapp.net')
                else:
                    name = str(info).strip()
                    jid = f'{number}@s.whatsapp.net'
                out.append((jid, name or number))
        elif isinstance(contacts, list):
            for c in contacts:
                if isinstance(c, dict):
                    jid = (c.get('id') or c.get('jid') or '').strip()
                    name = (c.get('name') or c.get('pushName') or '').strip()
                    if jid:
                        out.append((jid, name or jid))
        return out

    async def _find_contact(self, name: str) -> Optional[str]:
        """Encontra JID do contato. Usa fuzzy matching quando disponível."""
        jid, _, _ = await self._find_contact_with_meta(name)
        return jid

    async def _find_contact_with_meta(
        self, name: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Retorna (jid, nome_resolvido, mensagem_confirmacao).
        Se houver empate ou sugestão, mensagem_confirmacao contém texto para o usuário.
        """
        # Número entre parênteses ou só número
        num_match = re.search(r'\((\d{10,15})\)', name)
        if num_match:
            return self._format_phone(num_match.group(1)), name.strip(), None
        digits = ''.join(filter(str.isdigit, name))
        if len(digits) >= 10:
            return self._format_phone(digits), name.strip(), None

        result = await self._api_request("GET", "/contacts")
        if "error" in result:
            return None, None, None

        raw = result.get("contacts", {})
        if isinstance(raw, list):
            contact_list = self._contacts_to_list(raw)
        else:
            contact_list = self._contacts_to_list(raw) if isinstance(raw, dict) else []

        if not contact_list:
            return None, None, None

        # Resolução por similaridade (fuzzy)
        if resolve_contact:
            jid, resolved_name, score, ties = resolve_contact(
                name, contact_list, accept_threshold=DEFAULT_ACCEPT_THRESHOLD
            )
            if ties and len(ties) > 1:
                names = " ou ".join(n for _, n in ties[:3])
                return None, None, f"Não encontrei exatamente '{name}'. Você quis dizer {names}?"
            if jid and resolved_name:
                self._contacts_cache[jid] = resolved_name
                if score < DEFAULT_ACCEPT_THRESHOLD and score >= 0.5:
                    return jid, resolved_name, f"Usei o contato **{resolved_name}**."
                return jid, resolved_name, None
            if ties and len(ties) == 1:
                jid, resolved_name = ties[0][0], ties[0][1]
                self._contacts_cache[jid] = resolved_name
                return jid, resolved_name, f"Não encontrei '{name}'. Usei **{resolved_name}**."
            if not jid and not resolved_name and ties:
                names = ", ".join(n for _, n in ties[:3])
                return None, None, f"Não encontrei '{name}'. Você quis dizer: {names}?"
            if not jid:
                return None, None, None

        # Fallback: match exato/substring (comportamento antigo)
        search = name.lower().strip()
        for jid, display_name in contact_list:
            cn = (display_name or '').lower()
            if search in cn or cn in search:
                self._contacts_cache[jid] = display_name or jid
                return jid, (display_name or jid), None
        return None, None, None

    def _extract_contact_after_para(self, contact: str) -> str:
        """Se o 'contato' capturado contém ' para Nome', usa Nome como contato (evita 'sua própria')."""
        if not contact or " para " not in contact:
            return contact.strip()
        # Última ocorrência de " para " → contato real está depois
        idx = contact.lower().rfind(" para ")
        if idx >= 0:
            return contact[idx + 6:].strip()  # 6 = len(" para ")
        return contact.strip()

    def _parse_contact_and_message(self, message: str, entities: Dict) -> tuple:
        """Extrai contato e texto da mensagem a partir da frase do usuário."""
        contact = (entities.get('contact') or '').strip()
        contact = self._extract_contact_after_para(contact)
        msg_text = (entities.get('message') or '').strip()

        if contact and msg_text:
            return contact, msg_text

        # Quando o regex capturou só um grupo: "Juliana falando que não perguntei..."
        if contact:
            # Separadores em ordem de prioridade (mais específicos primeiro)
            separators = [
                ' falando que ', ' dizendo que ',
                ' e no final ', ' e acrescen', ' e no final acrescen',
                ' e fala que ', ' e diz que ', ' e fale ',
                ' com a mensagem ', ' com o texto ',
                ' falando ', ' dizendo ',
                ' que ',
            ]
            contact_lower = contact.lower()
            for sep in separators:
                idx = contact_lower.find(sep.lower().rstrip())
                if idx > 0:
                    nome = contact[:idx].strip()
                    rest = contact[idx + len(sep.rstrip()):].strip().lstrip(': ')
                    if nome and rest:
                        return nome, rest
            # Nome com muitas palavras (>4) provavelmente tem mensagem embutida — tenta na frase original
            if len(contact.split()) > 4:
                m_sep = re.search(
                    r'(?:para|pro|a)\s+(.+?)\s+(?:e\s+(?:no\s+final\s+)?(?:acrescen?t|fal|dig|diz|avis)|falando|dizendo|que|com\s+(?:a\s+mensagem|o\s+texto))(.+)',
                    message, re.IGNORECASE
                )
                if m_sep:
                    return m_sep.group(1).strip(), m_sep.group(2).strip().lstrip(': ')
            # Nome único sem "que" — mensagem pode estar no resto do texto
            if not msg_text and len(contact.split()) <= 3:
                for sep in [' falando que ', ' dizendo que ', ' que ']:
                    if sep in message:
                        idx = message.lower().find(sep.strip())
                        if idx > 0:
                            nome = message[:idx].strip()
                            if contact.lower() in nome.lower() or nome.lower() in contact.lower():
                                rest = message[idx + len(sep):].strip().lstrip(': ')
                                if rest:
                                    return contact.split()[0] if contact else nome, rest
                        break

        # Padrões na mensagem completa
        m = re.search(
            r'(?:para|pro)\s+([^,]+?)\s*(?:,|\s)+(?:dizendo|falando|que)\s*:?\s*(.+)',
            message,
            re.IGNORECASE | re.DOTALL
        )
        if m:
            return m.group(1).strip(), m.group(2).strip()

        if contact:
            contact = self._extract_contact_after_para(contact)
            return contact, msg_text or "Olá! O Jarvis está à disposição."
        # Tenta extrair "para X" da mensagem inteira quando o contato veio errado
        m = re.search(r'\bpara\s+([^,.\s]+(?:\s+[^,.\s]+){0,2})\s*$', message, re.IGNORECASE)
        if m:
            return m.group(1).strip(), msg_text or "Olá! O Jarvis está à disposição."
        return '', msg_text or message

    def _trim_contact_for_send(self, contact: str) -> str:
        """Remove do contato trechos que são pedido de conteúdo (se apresentando, falando funções)."""
        if not contact:
            return contact
        c = contact.strip()
        for suffix in [
            " se apresentando", " e se apresentando", " se apresentadno",
            " falando suas funções", " e falando suas funções", " e falando suas funcoes",
            " sobre você", " sobre voce", " e tudo que consegue fazer",
        ]:
            if c.lower().endswith(suffix.lower()):
                c = c[: -len(suffix)].strip()
        return c

    async def process(self, message: str, intent, context: Dict, metadata: Dict) -> str:
        intent_type = getattr(intent, 'type', str(intent))
        entities = getattr(intent, 'entities', {}) or {}

        # Validação de serviço: antes de qualquer ação WhatsApp, verificar se está rodando
        if intent_type in ('whatsapp_send', 'whatsapp_check', 'whatsapp_read', 'whatsapp_monitor', 'whatsapp_reply'):
            if not await self.is_service_available():
                return (
                    "O serviço WhatsApp não está rodando. Para usar essas funções, inicie com opção 3 ou 4 no start.bat.",
                    {},
                )

        if intent_type == 'whatsapp_send':
            # Mensagem pré-gerada (plano/apresentação): contato JÁ vem resolvido em entities — não interpretar texto
            composed = (metadata or {}).get('composed_message', '').strip()
            if composed:
                msg_text = composed
                contact = (entities.get('contact') or '').strip()
                if not contact and message:
                    m_para = re.search(r'\bpara\s+([^,.\s]+(?:\s+[^,.\s]+){0,2})\s*$', message, re.IGNORECASE)
                    contact = m_para.group(1).strip() if m_para else (self._parse_contact_and_message(message, entities)[0] or '')
            else:
                contact, msg_text = self._parse_contact_and_message(message, entities)
            contact = self._trim_contact_for_send(contact or "")
            if not contact:
                return "❌ Para quem devo enviar? Diga: manda mensagem para [nome] dizendo que [texto].", {}
            if not msg_text or len(msg_text) < 2:
                msg_text = "Olá! O Jarvis está à disposição."
            resp, meta = await self.send_message(contact, msg_text)
            return resp, meta or {}

        if intent_type == 'whatsapp_check':
            return await self.get_unread_messages(), {}

        if intent_type == 'whatsapp_read':
            contact = entities.get('contact', '').strip()
            if not contact:
                return "❌ De quem você quer ver as mensagens? Ex: ler mensagens da Juliana.", {}
            if '(' in contact and ')' in contact:
                name_part, _, num_part = contact.partition('(')
                num_part = num_part.rstrip(')').strip()
                if num_part and num_part.replace('+', '').replace(' ', '').isdigit():
                    contact = num_part
                else:
                    contact = name_part.strip()
            resp, meta = await self.get_chat_history_with_meta(contact)
            return resp, meta or {}

        if intent_type == 'whatsapp_monitor':
            contact = entities.get('contact', '').strip()
            if not contact:
                return (
                    "❌ De quem você quer monitorar a conversa? Ex: monitore a conversa do Douglas.",
                    {},
                )
            return await self.start_monitor(contact)

        if intent_type == 'whatsapp_reply':
            contact = entities.get('contact', '').strip()
            contact = self._extract_contact_after_para(contact)
            if not contact:
                last = (context or {}).get('last_contact') or (context or {}).get('last_monitored_contact')
                if last:
                    contact = last
            if not contact:
                return "❌ Para quem devo responder? Diga o contato ou 'responda a mensagem dele' após falar com alguém.", {}
            composed = (metadata or {}).get('composed_message', '').strip()
            msg_text = composed or "Olá! O Jarvis está à disposição."
            resp, meta = await self.send_message(contact, msg_text)
            return resp, meta or {}

        return "Comando WhatsApp não reconhecido.", {}

    async def send_message(
        self, to: str, message: str
    ) -> Tuple[str, Optional[Dict]]:
        """
        Envia mensagem. Retorna (resposta_para_usuário, metadata).
        metadata pode conter last_contact para o contexto.
        """
        meta: Optional[Dict] = None
        display_name = to
        num_match = re.search(r'\((\d{10,15})\)', to)
        if num_match:
            jid = self._format_phone(num_match.group(1))
        elif to.replace('+', '').replace(' ', '').isdigit() or to.startswith('+'):
            jid = self._format_phone(to)
        else:
            jid, resolved_name, confirm_msg = await self._find_contact_with_meta(to)
            if not jid:
                if confirm_msg:
                    return f"❌ {confirm_msg}", None
                return f"❌ Não encontrei o contato '{to}'. Você quis dizer algum nome parecido?", None
            if resolved_name:
                display_name = resolved_name
                meta = {"last_contact": resolved_name}
            if confirm_msg:
                # Resposta com confirmação + resultado
                result = await self._api_request("POST", "/send", {"to": jid, "message": message})
                if "error" in result:
                    err = result["error"]
                    if result.get("service_down"):
                        return f"❌ **WhatsApp não está rodando**\n\n{err}", None
                    return f"❌ Erro ao enviar: {err}", None
                return f"{confirm_msg}\n✅ Mensagem enviada para {display_name}", meta
        result = await self._api_request("POST", "/send", {"to": jid, "message": message})
        if "error" in result:
            err = result["error"]
            if result.get("service_down"):
                return f"❌ **WhatsApp não está rodando**\n\n{err}", None
            return f"❌ Erro ao enviar: {err}", None
        if meta is None:
            meta = {"last_contact": display_name}
        return f"✅ Mensagem enviada para {display_name}", meta

    async def get_unread_messages(self, limit: int = 20) -> str:
        result = await self._api_request("GET", "/messages/unread")
        if "error" in result:
            result = await self._api_request("GET", "/chats")
            if "error" in result:
                return f"❌ {_friendly_api_error(result['error'])}\n\n💡 Inicie o serviço WhatsApp (opção 3 ou 4 no start.bat)."
        messages = result.get("messages", result.get("chats", []))
        if not messages:
            return "📭 Nenhuma mensagem não lida"
        lines = ["📬 **Mensagens não lidas**\n"]
        for msg in messages[:limit]:
            sender = msg.get('pushName') or msg.get('from', 'Desconhecido')
            text = msg.get('message') or msg.get('body', '')
            lines.append(f"👤 **{sender}**: {text[:100]}{'...' if len(text) > 100 else ''}")
        return "\n".join(lines)

    async def get_chat_history(self, contact: str, limit: int = 20) -> str:
        resp, _ = await self.get_chat_history_with_meta(contact, limit)
        return resp

    async def get_chat_history_with_meta(
        self, contact: str, limit: int = 20
    ) -> Tuple[str, Optional[Dict]]:
        """Retorna (texto do chat, metadata com last_contact se resolvido)."""
        meta: Optional[Dict] = None
        display_name = contact
        if contact.isdigit() or contact.startswith('+'):
            jid = self._format_phone(contact)
        else:
            jid, resolved_name, confirm_msg = await self._find_contact_with_meta(contact)
            if not jid:
                if confirm_msg:
                    return f"❌ {confirm_msg}", None
                return f"❌ Não encontrei o contato '{contact}'. Você quis dizer algum nome parecido?", None
            if resolved_name:
                display_name = resolved_name
                meta = {"last_contact": resolved_name}
            if confirm_msg:
                result = await self._api_request("GET", f"/chat/{jid}?limit={limit}")
                if "error" in result:
                    return f"❌ {_friendly_api_error(result['error'], for_read=True)}", None
                messages = result.get("messages", [])
                if not messages:
                    return f"{confirm_msg}\n📭 Nenhuma mensagem com {display_name}", meta
                lines = [f"{confirm_msg}\n💬 **Chat com {display_name}**\n"]
                for msg in messages:
                    prefix = "🔵 Eu:" if msg.get('fromMe') else "⚪ Ele:"
                    text = msg.get('message') or msg.get('body', '')
                    lines.append(f"{prefix} {text[:150]}")
                return "\n".join(lines), meta
        if not jid:
            jid = contact
        result = await self._api_request("GET", f"/chat/{jid}?limit={limit}")
        if "error" in result:
            return f"❌ {_friendly_api_error(result['error'], for_read=True)}", None
        messages = result.get("messages", [])
        if not messages:
            return f"📭 Nenhuma mensagem com {display_name}", meta
        lines = [f"💬 **Chat com {display_name}**\n"]
        for msg in messages:
            prefix = "🔵 Eu:" if msg.get('fromMe') else "⚪ Ele:"
            text = msg.get('message') or msg.get('body', '')
            lines.append(f"{prefix} {text[:150]}")
        return "\n".join(lines), meta

    async def start_monitor(self, contact: str) -> Tuple[str, Dict]:
        """
        Ativa monitoramento da conversa do contato (tarefa persistente).
        Por enquanto registra a intenção; a reação a novas mensagens depende do serviço WhatsApp.
        """
        jid, resolved_name, confirm_msg = await self._find_contact_with_meta(contact)
        if not jid:
            if confirm_msg:
                return f"❌ {confirm_msg}", {}
            return f"❌ Contato não encontrado: {contact}", {}
        name = resolved_name or contact
        # Persistir em config/monitors.json se existir (formato: contacts.jids)
        try:
            monitors_path = Path(__file__).parent.parent.parent / "config" / "monitors.json"
            if monitors_path.exists():
                import json
                data = json.loads(monitors_path.read_text(encoding="utf-8"))
                contacts_block = data.get("contacts") or {}
                if isinstance(contacts_block, dict):
                    jids = list(contacts_block.get("jids") or [])
                    if jid not in jids:
                        jids.append(jid)
                        data.setdefault("contacts", {})["jids"] = jids
                        monitors_path.write_text(
                            json.dumps(data, ensure_ascii=False, indent=2),
                            encoding="utf-8",
                        )
        except Exception as e:
            logger.debug("Não foi possível salvar monitor: %s", e)
        msg = f"✅ Vou monitorar a conversa de **{name}**."
        if confirm_msg:
            msg = f"{confirm_msg}\n{msg}"
        return msg, {"last_contact": name, "monitored_contact": name}


def _service_not_running_msg() -> str:
    return (
        "O serviço do WhatsApp não está rodando. "
        "Para enviar mensagens: use opção 3 ou 4 no start.bat, ou execute: cd services/whatsapp && node index.js"
    )


def _friendly_api_error(err: str, for_read: bool = False) -> str:
    """Traduz erros da API para mensagem amigável."""
    if not err:
        return "Ocorreu um erro ao comunicar com o WhatsApp."
    err_lower = err.lower()
    if "not found" in err_lower or "404" in err_lower:
        if for_read:
            return "Nenhuma conversa encontrada com esse contato ou o serviço não retornou dados. Verifique se o WhatsApp está conectado (opção 3 ou 4 no start.bat)."
        return "O serviço WhatsApp não retornou dados. Verifique se está conectado (opção 3 ou 4 no start.bat)."
    return err
