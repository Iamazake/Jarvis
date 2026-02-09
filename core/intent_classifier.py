# -*- coding: utf-8 -*-
"""
Intent Classifier - Classificador de Intenções
Usa IA para entender o que o usuário quer

Autor: JARVIS Team
Versão: 3.0.0
"""

import re
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Intent:
    """Representa uma intenção classificada"""
    type: str
    confidence: float
    entities: Dict = None
    raw_match: str = None
    
    def __post_init__(self):
        if self.entities is None:
            self.entities = {}


class IntentClassifier:
    """
    Classificador de intenções do usuário
    
    Usa padrões regex para classificação rápida
    e IA para casos ambíguos
    """
    
    def __init__(self):
        # Padrões de intenção (regex)
        self.patterns = {
            # === PESQUISA ===
            'search': [
                r'(?:pesquis[ae]|busca|procur[ae]|search)\s+(?:sobre\s+)?(.+)',
                r'(?:o que (?:é|são)|quem (?:é|são)|quando (?:foi|será))\s+(.+)',
                r'(?:me )?(?:fal[ae]|cont[ae]|explic[ae])\s+(?:sobre\s+)?(.+)',
            ],
            'weather': [
                r'(?:como está|qual|previsão d[eo])\s*(?:o\s+)?tempo',
                r'(?:vai|está|tá)\s+(?:chover|chovendo|faz(?:er)?\s+(?:frio|calor))',
                r'temperatura\s+(?:em|de|hoje)',
            ],
            'news': [
                r'(?:notícias?|news)\s*(?:sobre\s+)?(.+)?',
                r'(?:o que (?:está|tá) acontecendo|novidades)\s*(?:sobre\s+)?(.+)?',
            ],
            
            # === WHATSAPP (verificar antes de search/app_control) ===
            'whatsapp_send': [
                r'(?:avis[ae]|avise)\s+(?:a\s+)?([^\s,]+?)\s+que\s+(.+)',
                # Com separador explícito (2 grupos: contato + mensagem)
                r'(?:mandar?|enviar?|mand[ae]|envi[ae])\s+(?:uma\s+|essa\s+)?(?:mensagem|msg|mensagm)\s+(?:para?|pro?|a)\s+([^,]+?)\s*(?:,|\s)+(?:dizendo|falando|que|e\s+(?:fal[ae]|dig[ae]|avis[ae]|acrescen?t[ae]))\s*:?\s*(.+)',
                # Sem separador (1 grupo: só contato) — evita capturar "sua própria" (negative lookahead)
                r'(?:mandar?|enviar?|mand[ae]|envi[ae])\s+(?:uma\s+|essa\s+)?(?:mensagem|msg|mensagm)\s+(?:para?|pro?|a)\s+(?!sua\s)(.+)',
                r'(?:mand[ae]|envi[ae])\s+(?:para?|pro?|a)\s+([^,]+?)\s+(?:dizendo|falando|que|e\s+(?:fal[ae]|dig[ae]))\s*:?\s*(.+)',
                r'(?:respond[ae]|responde)\s+(?:para?|pro?)\s+(.+)',
                r'(?:dig[ae]|fal[ae])\s+(?:para?|pro?|a)\s+(.+?)\s+(?:que\s+)?(.+)',
                r'(?:mandar?|enviar?)\s+(?:para?|pro?|a)\s+(.+)',
                # Monte/crie/faça mensagem (sua própria, se apresentando) para X — evita app_control
                r'(?:quero\s+que\s+(?:vc\s+|você\s+)?)(?:monte|mont[ae]|crie|cri[ae]|faç[ae]|faça|envie|envi[ae])\s+(?:a\s+|uma\s+)?(?:sua\s+própria\s+)?(?:mensagem\s+)?(?:para\s+)?(.+?)(?=\s+se\s+apresentando|\s+e\s+se\s+|\s*,|$)',
                r'(?:quero\s+que\s+(?:vc\s+|você\s+)?)(?:monte|mont[ae]|crie|cri[ae]|faç[ae]|faça|envie|envi[ae])\s+(?:a\s+|uma\s+)?(?:sua\s+própria\s+)?(?:mensagem\s+)?(?:para\s+)?(.+)',
                r'(?:monte|mont[ae]|crie|cri[ae]|faç[ae]|faça)\s+(?:uma\s+)?(?:sua\s+)?mensagem\s+(?:se\s+apresentando\s+)?(?:para\s+)?(.+?)(?=\s+se\s+|\s+e\s+|\s*,|$)',
                r'(?:monte|mont[ae]|crie|cri[ae]|faç[ae]|faça)\s+(?:uma\s+)?(?:sua\s+)?mensagem\s+(?:para\s+)?(.+)',
                r'(?:envie|envi[ae])\s+(?:uma\s+)?(?:sua\s+)?(?:própria\s+)?mensagem\s+(?:sua\s+própria\s+)?(?:se\s+apresentando|falando\s+suas\s+funções)\s+(?:para\s+)?(.+?)(?=\s+e\s+|\s*,|$)',
                r'(?:envie|envi[ae])\s+(?:uma\s+)?(?:sua\s+)?(?:própria\s+)?mensagem\s+(?:sua\s+própria\s+)?(?:se\s+apresentando|falando\s+suas\s+funções)\s+(?:para\s+)?(.+)',
                r'(?:faç[ae]|faça)\s+(?:uma\s+)?mensagem\s+.+?(?:depois\s+)?(?:envie|envia)\s+(?:essa\s+)?(?:mensagem\s+)?para\s+([^,]+?)(?:\s*\.|$|\s+e\s+)',
                r'(?:faç[ae]|faça)\s+(?:uma\s+)?mensagem\s+.+?\s+para\s+([^,]+?)(?:\s*\.|$|\s+,)',
            ],
            'whatsapp_check': [
                r'(?:verific[ae]|confir[ae]|chec[ae])\s+(?:as\s+|minhas?\s+)?mensagens?(?:\s+que\s+.*)?',
                r'(?:verific[ae]|confir[ae]|chec[ae])\s+(?:minhas?\s+)?mensagens?',
                r'(?:tem|tenho)\s+(?:alguma\s+)?mensagem\s+(?:nova)?',
                r'(?:quem|algu[eé]m)\s+(?:me\s+)?(?:mandou|enviou)\s+mensagem',
            ],
            'whatsapp_read': [
                r'(?:consegue\s+)?resumir\s+(?:a\s+)?conversa\s+(?:d[eo]|da)?\s*(?:contato\s+)?(.+?)(?=\s*\?|\s*\.|$)',
                r'resumo\s+(?:da\s+)?conversa\s+(?:d[eo]|da|com)?\s*(?:contato\s+)?(.+?)(?=\s*\?|\s*\.|$)',
                r'(?:olh[ae]r?|v[eê]r|ler|mostr[ae])\s+(?:as?\s+)?(?:mensagens?|conversa)\s+(?:d[eo]|da)?\s*(?:contato\s+)?(.+?)(?=\s+caso\s+|\s+e\s+(?:quando\s+)?|\s+quando\s+|,|$)',
                r'(?:l[eê]|ler|mostr[ae])\s+(?:as?\s+)?(?:última[s]?\s+)?mensagens?\s+(?:d[eo]|da)\s+(.+?)(?=\s+caso\s+|\s+e\s+(?:quando\s+)?|\s+quando\s+|,|$)',
                r'(?:monitor[ae]r?|monitore)\s+(?:a\s+)?conversa\s+(?:d[eo]|da)?\s*(?:contato\s+)?(.+?)(?=\s+caso\s+|\s+e\s+(?:quando\s+)?|\s+quando\s+|,|$)',
                r'(?:o que|qual)\s+(?:o\s+)?(.+?)\s+(?:disse|falou|mandou)',
                r'(?:olh[ae]r?|v[eê]r|ler|mostr[ae])\s+(?:as?\s+)?(?:mensagens?|conversa)\s+(?:d[eo]|da)?\s*(?:contato\s+)?(.+)',
                r'(?:monitor[ae]r?|monitore)\s+(?:a\s+)?conversa\s+(?:d[eo]|da)?\s*(?:contato\s+)?(.+)',
            ],
            'whatsapp_monitor': [
                r'(?:monitor[ae]r?|monitore)\s+(?:o\s+)?contato\s+(.+?)(?=\s+e\s+|\s+caso\s+|\s+quando\s+|,|$)',
                r'(?:monitor[ae]r?|monitore)\s+(?:o\s+)?contato\s+(.+)',
                r'(?:monitor[ae]r?|monitore)\s+(?:a\s+)?conversa\s+(?:d[eo]|da)?\s*(?:contato\s+)?(.+?)(?=\s+caso\s+|\s+e\s+|\s+quando\s+|,|$)',
                r'(?:fic[ae]r?|ficar)\s+monitorando\s+(?:a\s+)?conversa\s+(?:d[eo]|da)?\s*(.+?)(?=\s+caso\s+|\s+e\s+|\s+quando\s+|,|$)',
                r'(?:monitor[ae]r?|monitore)\s+(?:a\s+)?conversa\s+(?:d[eo]|da)?\s*(?:contato\s+)?(.+)',
            ],
            'whatsapp_reply': [
                r'(?:respond[ae]|responde)\s+(?:à|a)\s+(?:última\s+)?mensagem\s+(?:dele|dela|dele\.|dela\.)?',
                r'(?:respond[ae]|responde)\s+(?:à|a)\s+(?:última\s+)?mensagem\s+(?:d[eo]|da)\s+(.+?)(?:\s+(?:de\s+)?maneira\s+|\s*\.|$|\s+dizendo)',
                r'(?:respond[ae]|responde)\s+(?:para?|pro?)\s+(?:ele|ela|dele|dela)',
                r'(?:respond[ae]|responde)\s+(?:à|a)\s+(?:última\s+)?mensagem\s+(?:d[eo]|da)\s+(.+)',
                r'responder\s+(?:à|a)\s+(?:última\s+)?mensagem\s+(?:de\s+)?(.+?)(?:\s+de\s+maneira|\s*\.|$|\s+dizendo)',
            ],
            
            # === AGENDA/LEMBRETES ===
            'reminder': [
                r'(?:me\s+)?(?:lembr[ae]|lembra-me|avisa-me)\s+(?:de\s+)?(.+?)(?:\s+(?:em|daqui|às?|as)\s+(.+))?$',
                r'(?:cri[ae]|adiciona)\s+(?:um\s+)?lembrete\s+(?:para\s+)?(.+)',
            ],
            'alarm': [
                r'(?:coloc[ae]|configur[ae]|bot[ae])\s+(?:um\s+)?(?:alarme|despertador)\s+(?:para\s+)?(.+)',
                r'(?:me\s+)?(?:acord[ae]|desperta)\s+(?:às?\s+)?(.+)',
            ],
            'schedule': [
                r'(?:o que|qual)\s+(?:tenho|minha)\s+(?:agenda|compromissos?)\s+(?:para\s+)?(.+)?',
                r'(?:meus?|minhas?)\s+(?:compromissos?|eventos?|agenda)\s+(?:de\s+)?(.+)?',
            ],
            
            # === FERRAMENTAS/SISTEMA ===
            'file_operation': [
                r'(?:cri[ae]|faz|abr[ae])\s+(?:um[a]?\s+)?(?:pasta|arquivo|diretório)\s+(.+)',
                r'(?:organiz[ae]|mov[ae]|copi[ae]|delet[ae]|apag[ae])\s+(?:os?\s+)?(?:arquivos?|pastas?)\s+(.+)',
                r'(?:list[ae]|mostr[ae])\s+(?:os?\s+)?(?:arquivos?|pastas?)\s+(?:em\s+)?(.+)?',
            ],
            'system_command': [
                r'(?:execut[ae]|rod[ae]|run)\s+(?:o\s+)?(?:comando\s+)?(.+)',
                r'(?:qual|quanto)\s+(?:o\s+)?(?:uso\s+de\s+)?(?:cpu|memória|ram|disco)',
                r'(?:status|info)\s+(?:do\s+)?sistema',
            ],
            'app_control': [
                r'(?:abr[ae]|inici[ae]|execut[ae]|rod[ae])\s+(?:o\s+)?(.+)',
                r'(?:fech[ae]|par[ae]|encerr[ae]|mat[ae])\s+(?:o\s+)?(.+)',
            ],
            
            # === CONVERSA / PERGUNTAS (evitar app_control em "como assim", "por que") ===
            'greeting': [
                r'^(?:oi|olá|e aí|eai|hey|hello|bom dia|boa tarde|boa noite|fala)\s*,?\s*(?:jarvis)?[!?]*$',
                r'(?:(?:jarvis|oi)\s+,?\s*)?como\s+(?:você|vc)\s+está\??\s*$',
                r'quantas?\s+versões?\s+(?:eu\s+)?(?:já\s+)?fiz',
            ],
            'capabilities': [
                r'(?:o\s+que\s+(?:você|vc)\s+consegue\s+(?:fazer)?|quais?\s+(?:suas?\s+)?(?:fun[cç][oõ]es|capacidades)|liste?\s+(?:suas?\s+)?(?:fun[cç][oõ]es|capacidades)|(?:suas?\s+)?capacidades\s+e\s+modos|tudo\s+que\s+(?:nossa\s+)?(?:ia\s+)?consegue\s+fazer)',
                r'(?:o\s+que\s+o\s+jarvis\s+consegue|apresent[ae]r?\s+(?:essa\s+)?(?:ia\s+)?(?:pro\s+)?time)',
            ],
            'conversation_question': [
                r'^(?:como\s+assim|por\s+que|porque|como\s+(?:você|vc)\s+(?:consegue|pode|faz)|o\s+que\s+(?:você|vc)\s+(?:pode|consegue)|por\s+que\s+(?:você|vc))',
                r'(?:você|vc)\s+consegue\s+acessar',
                r'(?:eu\s+)?(?:não\s+)?te\s+programei',
            ],
            'thanks': [
                r'^(?:obrigad[oa]|valeu|thanks|vlw|brigad[oa])[!?]*$',
            ],
            'farewell': [
                r'^(?:tchau|até|adeus|bye|falou|flw)[!?]*$',
            ],
            
            # === SENTIMENTO ===
            'sentiment': [
                r'(?:estatísticas?|estatisticas?)\s+(?:de\s+)?(?:humor|sentimento)',
                r'analisar\s+sentimento',
                r'(?:qual\s+)?(?:o\s+)?humor',
                r'(?:como\s+)?(?:estou\s+me\s+)?sentindo\s*(?:pelas?\s+palavras?)?',
                r'(?:sabe\s+)?(?:me\s+)?diz(?:er)?\s+(?:como\s+)?(?:estou\s+me\s+)?sentindo',
            ],
            # === PRODUTIVIDADE ===
            'productivity': [
                r'relat[oó]rio\s+(?:do\s+)?dia',
                r'relat[oó]rio\s+(?:da\s+)?semana',
                r'(?:iniciar|come[cç]ar)\s+(?:sess[aã]o|foco)',
                r'(?:encerrar|parar)\s+(?:sess[aã]o|foco)',
                r'sugest[oõ]es\s+(?:de\s+)?(?:produtividade)?',
                r'status\s+produtividade',
            ],
            # === BACKUP ===
            'backup': [
                r'(?:fazer|criar)\s+backup',
                r'listar\s+backups?',
                r'restaurar\s+(?:config)?',
            ],
            # === SEGURANÇA ===
            'security': [
                r'configurar\s+pin',
                r'(?:últimas?|ultimas?)\s+a[cç][oõ]es',
                r'auditoria',
            ],
            # === TRADUÇÃO ===
            'translation': [
                r'detectar\s+idioma',
                r'traduzir\s+(.+)',
                r'traduza\s+(.+)',
                r'qual\s+idioma',
            ],
            # === AUTOMAÇÃO ===
            'automation': [
                r'(?:criar|listar|executar)\s+workflow',
                r'workflows?\s+(?:configurados?)?',
            ],
        }
        
        # Compilar regex para performance
        self.compiled_patterns = {}
        for intent, patterns in self.patterns.items():
            self.compiled_patterns[intent] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
    
    async def classify(self, message: str, context: Dict = None) -> Intent:
        """
        Classifica a intenção de uma mensagem
        
        Args:
            message: Texto do usuário
            context: Contexto da conversa
        
        Returns:
            Intent com tipo e confiança
        """
        message = message.strip()
        context = context or {}
        
        # 0. Envio de mensagem domina: verbo de envio + "mensagem"/"msg"/"texto" → whatsapp_send (antes de app_control)
        # Exceto se usuário nega ou quer conversar: "não quero enviar", "quero conversar contigo"
        if self._has_send_message_intent(message) and not self._has_negation_or_want_chat(message):
            entities = {}
            contact = self._quick_extract_contact_for_send(message, context)
            if contact:
                entities['contact'] = contact
            self._apply_context_to_entities(entities, 'whatsapp_send', context)
            return Intent(type='whatsapp_send', confidence=0.85, entities=entities)

        # 1. Tenta match por padrão (rápido) — WhatsApp primeiro para não cair em search/app_control
        priority_order = [
            'whatsapp_send', 'whatsapp_check', 'whatsapp_read', 'whatsapp_monitor', 'whatsapp_reply',
            'capabilities',
            'reminder', 'alarm', 'schedule', 'sentiment', 'productivity',
            'backup', 'security', 'translation', 'automation',
            'conversation_question',
            'search', 'weather', 'news', 'file_operation', 'system_command', 'app_control',
            'greeting', 'thanks', 'farewell',
        ]
        for intent_type in priority_order:
            # Perguntas como "como posso melhorar..." não devem virar app_control
            if intent_type == 'app_control' and self._is_question_not_command(message):
                continue
            patterns = self.compiled_patterns.get(intent_type, [])
            for pattern in patterns:
                match = pattern.search(message)
                if match:
                    entities = self._extract_entities(match, intent_type)
                    self._apply_context_to_entities(entities, intent_type, context)
                    return Intent(
                        type=intent_type,
                        confidence=0.9,
                        entities=entities,
                        raw_match=match.group(0)
                    )
        # Fallback: restante dos padrões (qualquer outro não listado acima)
        for intent_type, patterns in self.compiled_patterns.items():
            if intent_type in priority_order:
                continue
            for pattern in patterns:
                if intent_type == 'app_control' and self._is_question_not_command(message):
                    continue
                match = pattern.search(message)
                if match:
                    entities = self._extract_entities(match, intent_type)
                    self._apply_context_to_entities(entities, intent_type, context)
                    return Intent(
                        type=intent_type,
                        confidence=0.9,
                        entities=entities,
                        raw_match=match.group(0)
                    )
        
        # 2. Analisa contexto
        if context.get('last_intent'):
            # Se estava em um fluxo, pode ser continuação
            last = context['last_intent']
            if last in ['whatsapp_send', 'reminder', 'search']:
                # Pode ser o conteúdo da mensagem/lembrete/pesquisa
                return Intent(
                    type=f"{last}_content",
                    confidence=0.7,
                    entities={'content': message}
                )
        
        # 3. Classificação por palavras-chave (fallback)
        intent = self._keyword_classification(message)
        if intent:
            return intent
        
        # 4. Default: conversa geral
        return Intent(
            type='conversation',
            confidence=0.5,
            entities={}
        )
    
    def _extract_entities(self, match: re.Match, intent_type: str) -> Dict:
        """Extrai entidades do match de regex"""
        entities = {}
        groups = match.groups()
        
        if not groups:
            return entities
        
        # Mapeia grupos para entidades baseado na intenção
        entity_maps = {
            'search': ['query'],
            'whatsapp_send': ['contact', 'message'],
            'whatsapp_read': ['contact'],
            'whatsapp_monitor': ['contact'],
            'whatsapp_reply': ['contact'],
            'reminder': ['task', 'time'],
            'alarm': ['time'],
            'file_operation': ['target'],
            'app_control': ['app'],
        }
        
        names = entity_maps.get(intent_type, ['value'])
        
        for i, group in enumerate(groups):
            if group and i < len(names):
                entities[names[i]] = group.strip()
        
        # Para WhatsApp: limpa contato (cláusulas, conteúdo/tom, stop-phrases)
        if intent_type in ('whatsapp_send', 'whatsapp_read', 'whatsapp_monitor', 'whatsapp_reply') and entities.get('contact'):
            c = self._trim_contact_entity(entities['contact'])
            c = self._trim_contact_content(c)
            c = c.rstrip('?.,;')
            entities['contact'] = c
        if intent_type in ('whatsapp_send', 'whatsapp_read', 'whatsapp_monitor') and entities.get('contact'):
            entities['contact'] = self._strip_contact_stop_phrases(entities['contact'])
        if intent_type == 'whatsapp_reply' and entities.get('contact'):
            entities['contact'] = self._strip_contact_stop_phrases(entities['contact'])
        
        return entities

    def _trim_contact_entity(self, contact: str) -> str:
        """Remove do contato trechos que são cláusulas (caso X, e quando, quando, vírgula)."""
        if not contact:
            return contact
        # Corta no primeiro separador que indica continuação da frase
        for sep in [' caso ', ' e quando ', ' quando ', ' e monitore', ' e monitorar', ' e ler', ' e ver', ',']:
            idx = contact.lower().find(sep.lower())
            if idx > 0:
                contact = contact[:idx].strip()
        return contact.strip()

    # Trechos que são CONTEÚDO/TOM, não nome; contato é truncado antes deles
    CONTACT_CONTENT_MARKERS = (
        ' fazendo ', ' declaração ', ' declaracao ', ' se apresentando ', ' pode usar ', ' linguagem ', ' linguame ',
        ' mensagem ', ' mensagnem ', ' modo ', ' mais formal ', ' mais informal ', ' e mande ', ' falando ', ' dizendo ',
        ' amorosa ', ' profissional ', ' amor ',
        ' zoando ', ' zoando com ', ' com a cara ', ' com a cara del', ' com a cara dele', ' com a cara dela',
    )

    def _trim_contact_content(self, contact: str) -> str:
        """Corta o contato no primeiro marcador de conteúdo (nunca usar 'declaração de amor' etc. como nome)."""
        if not contact:
            return contact
        c_lower = contact.lower()
        best = len(contact)
        for sep in self.CONTACT_CONTENT_MARKERS:
            idx = c_lower.find(sep)
            if 0 <= idx < best:
                best = idx
        if best < len(contact):
            contact = contact[:best].strip()
        return contact.strip()

    # Frases que NUNCA são nome de contato; se contact for uma delas ou começar com uma, considerar vazio
    CONTACT_STOP_PHRASES = (
        'sua própria', 'sua propria', 'se apresentando', 'se apresentadno',
        'ela fazendo', 'ele fazendo', 'fazendo declaração', 'fazendo declaracao', 'declaração de amor', 'declaracao de amor',
        'mensagem', 'mensagnem',
        'que eu pedi pra você monitorar', 'que eu pedi pra vc monitorar',
        'que você está monitorando', 'que vc está monitorando', 'que vc esta monitorando',
        'do contato monitorado', 'que você está monitorando', 'que pedi pra monitorar',
    )

    def _strip_contact_stop_phrases(self, contact: str) -> str:
        """Se contact for ou começar com uma stop-phrase, retorna vazio para usar contexto ou ' para X'."""
        if not contact:
            return contact
        c = contact.strip().lower()
        for phrase in self.CONTACT_STOP_PHRASES:
            if c == phrase or c.startswith(phrase + ' ') or c.startswith(phrase + ','):
                return ''
        return contact.strip()

    def _is_question_not_command(self, message: str) -> bool:
        """True se a mensagem é pergunta (como/o que/por que/quais) sem verbo de comando explícito."""
        msg = (message or '').strip().lower()
        question_starts = ('como ', 'o que ', 'o que ', 'por que ', 'porque ', 'quais ', 'qual ')
        if not any(msg.startswith(s) for s in question_starts):
            return False
        command_verbs = ('abre ', 'abra ', 'fecha ', 'feche ', 'executa ', 'execute ', 'roda ', 'rode ', 'inicia ', 'inicie ')
        return not any(v in msg for v in command_verbs)

    SEND_VERBS = (
        'envie', 'enviar', 'envia', 'mande', 'mandar', 'manda', 'responda', 'responde',
        'fala', 'fale', 'diz', 'diga', 'manda pra', 'envia pra',
    )
    MESSAGE_WORDS = (
        'mensagem', 'mensagm', 'mensagme', 'menagem', 'menasgem', 'msg', 'texto', 'recado',
    )

    def _has_send_message_intent(self, message: str) -> bool:
        """Verbo de envio + (palavra de mensagem OU 'para' + nome) → whatsapp_send (ex.: 'sim envie para tchuchuca')."""
        msg = (message or '').lower()
        has_send = any(v in msg for v in self.SEND_VERBS)
        if not has_send:
            return False
        if any(m in msg for m in self.MESSAGE_WORDS):
            return True
        # "envie para X" / "mande para tchuchuca" mesmo sem a palavra "mensagem"
        return bool(re.search(r'\bpara\s+\w+', msg))

    def _has_negation_or_want_chat(self, message: str) -> bool:
        """True se usuário nega envio ou quer conversar: não forçar whatsapp_send."""
        msg = (message or '').lower()
        phrases = (
            'não quero que envie', 'não quero enviar', 'não quero que mande', 'não quero mandar',
            'quero conversar', 'vamos conversar', 'esqueça o whatsapp', 'esqueça whatsapp',
            'quero falar contigo', 'conversar aqui', 'conversar com você', 'conversar com vc',
        )
        return any(p in msg for p in phrases)

    def _quick_extract_contact_for_send(self, message: str, context: Dict) -> str:
        """Extrai contato de 'para X' / 'pra X' para o early whatsapp_send. Retorna vazio ou nome."""
        m = re.search(
            r'(?:para|pra)\s+(?:a\s+)?(.+?)(?=\s+fazendo|\s+perguntando|\s+fofinha|\s+fofinho|\s+com\s+|\s*$)',
            message, re.I | re.DOTALL
        )
        if not m:
            m = re.search(r'(?:para|pra)\s+(?:a\s+)?(.+)', message, re.I)
        if not m:
            return ''
        contact = m.group(1).strip()
        contact = self._trim_contact_content(contact)
        if contact.lower() in ('ela', 'ele', 'dele', 'dela'):
            return contact  # _apply_context_to_entities vai substituir por last_contact
        for prefix in ('a ', 'o '):
            if contact.lower().startswith(prefix):
                contact = contact[len(prefix):].strip()
                break
        return contact.strip() if contact else ''

    # Referências que indicam "contato que pedi pra monitorar" → last_monitored_contact
    MONITORED_REF_PHRASES = (
        'que eu pedi pra você monitorar', 'que eu pedi pra vc monitorar',
        'que você está monitorando', 'que vc está monitorando', 'que vc esta monitorando',
        'que você está monitorando', 'do contato monitorado', 'que pedi pra monitorar',
        'do contato que eu pedi pra você monitorar', 'do contato que eu pedi pra vc monitorar',
    )

    def _apply_context_to_entities(self, entities: Dict, intent_type: str, context: Dict):
        """Preenche contato a partir do contexto (last_contact, last_monitored_contact)."""
        if intent_type not in ('whatsapp_read', 'whatsapp_monitor', 'whatsapp_send', 'whatsapp_reply'):
            return
        contact = (entities.get('contact') or '').strip().lower()
        # Referências a contato monitorado
        for phrase in self.MONITORED_REF_PHRASES:
            if contact == phrase or contact.startswith(phrase + ' ') or contact.startswith(phrase + ','):
                monitored = (context.get('last_monitored_contact') or '').strip()
                if monitored:
                    entities['contact'] = monitored
                return
        # Pronomes (ela/ele) → last_monitored_contact ou last_contact
        refs = ('dele', 'dela', 'ele', 'ela', 'dele.', 'dela.', 'nele', 'nela')
        if not contact or contact in refs:
            last = (context.get('last_monitored_contact') or context.get('last_contact') or '').strip()
            if last:
                entities['contact'] = last
    
    def _keyword_classification(self, message: str) -> Optional[Intent]:
        """Classificação simples por palavras-chave"""
        message_lower = message.lower()
        
        # Keywords por categoria
        keywords = {
            'search': ['pesquisa', 'busca', 'procura', 'google', 'o que é', 'quem é'],
            'weather': ['tempo', 'clima', 'chuva', 'sol', 'temperatura', 'previsão'],
            'whatsapp_check': ['mensagem', 'whatsapp', 'zap', 'msg'],
            'reminder': ['lembrete', 'lembra', 'avisa', 'não esquece'],
            'file_operation': ['arquivo', 'pasta', 'diretório', 'criar', 'deletar'],
            'app_control': ['abre', 'fecha', 'inicia', 'executa', 'roda'],
        }
        
        for intent_type, words in keywords.items():
            # "esqueça o whatsapp" / "vamos conversar" → conversation, não whatsapp_check
            if intent_type == 'whatsapp_check' and self._has_negation_or_want_chat(message):
                continue
            for word in words:
                if word in message_lower:
                    return Intent(
                        type=intent_type,
                        confidence=0.6,
                        entities={'raw': message}
                    )
        
        return None
    
    def split_compound(self, message: str) -> List[str]:
        """
        Se a mensagem for um comando composto (ex: "mande mensagem para X e monitore a conversa"),
        retorna lista com as duas partes; caso contrário retorna [message].
        Não divide quando " e envie " é continuação da mesma tarefa (montar mensagem e enviar).
        """
        msg = message.strip()
        if not msg or ' e ' not in msg:
            return [msg]
        msg_lower = msg.lower()
        # Não dividir: "monte uma mensagem ... e envie para X" é um único comando
        if re.search(r'mensagem\s+', msg_lower) and re.search(r'\b(apresentando|fun[cç]oes|consegue|pr[oó]pria)\b', msg_lower):
            if re.search(r'\s+e\s+envi[ae]r?\s+', msg_lower) or re.search(r'\s+e\s+mand[ae]r?\s+', msg_lower):
                return [msg]
        # Segundos comandos conhecidos (verbo após " e ")
        second_starts = [
            r'e\s+monitore\s+', r'e\s+monitorar\s+', r'e\s+monitora\s+',
            r'e\s+ler\s+', r'e\s+ver\s+', r'e\s+olhar\s+', r'e\s+mostr[ae]r?\s+',
            r'e\s+enviar\s+', r'e\s+mandar\s+', r'e\s+mand[ae]\s+', r'e\s+envi[ae]\s+',
        ]
        for pat in second_starts:
            m = re.search(pat, msg, re.IGNORECASE)
            if m:
                idx = m.start()
                first = msg[:idx].strip()
                second = msg[idx + 2:].strip()
                if first and second:
                    return [first, second]
        return [msg]

    def add_pattern(self, intent_type: str, pattern: str):
        """Adiciona novo padrão de intenção"""
        if intent_type not in self.patterns:
            self.patterns[intent_type] = []
            self.compiled_patterns[intent_type] = []
        
        self.patterns[intent_type].append(pattern)
        self.compiled_patterns[intent_type].append(
            re.compile(pattern, re.IGNORECASE)
        )
