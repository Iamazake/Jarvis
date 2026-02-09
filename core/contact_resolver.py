# -*- coding: utf-8 -*-
"""
Contact Resolver - Resolução de contatos por similaridade (fuzzy matching)
Permite encontrar "Douglas Moretti" quando o usuário diz "douglas" ou "douglas morett".

Autor: JARVIS Team
Versão: 3.0.0
"""

import re
import unicodedata
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

# Score mínimo para aceitar um contato sem perguntar (0-1)
DEFAULT_ACCEPT_THRESHOLD = 0.75
# Score mínimo para sugerir "Você quis dizer X?"
DEFAULT_SUGGEST_THRESHOLD = 0.5


def normalize_for_match(text: str) -> str:
    """Normaliza texto para comparação: lowercase, sem acentos, colapsa espaços."""
    if not text:
        return ""
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"\s+", " ", text)
    return text


def _token_set_ratio(a: str, b: str) -> float:
    """
    Similaridade baseada em tokens: quantos tokens de A estão em B e vice-versa.
    Retorna valor entre 0 e 1.
    """
    if not a or not b:
        return 0.0
    ta = set(a.split())
    tb = set(b.split())
    if not ta:
        return 1.0 if not tb else 0.0
    inter = len(ta & tb)
    # Score: média de (cobertura em A) e (cobertura em B)
    in_a = inter / len(ta)
    in_b = inter / len(tb)
    return (in_a + in_b) / 2


def _substring_score(search: str, full_name: str) -> float:
    """
    Se search é substring de full_name ou todos os tokens de search estão em full_name.
    Retorna 0-1 (1 se match exato ou substring forte).
    """
    if not search or not full_name:
        return 0.0
    sn = normalize_for_match(search)
    fn = normalize_for_match(full_name)
    if sn == fn:
        return 1.0
    if sn in fn:
        # Quanto maior a proporção do nome encontrada, melhor
        return 0.7 + 0.3 * (len(sn) / max(len(fn), 1))
    # Todos os tokens de search estão em full_name?
    st = set(sn.split())
    ft = set(fn.split())
    if st <= ft:
        return 0.75 * (len(st) / max(len(ft), 1)) + 0.25
    return 0.0


def similarity_score(search: str, candidate_name: str) -> float:
    """
    Calcula score de similaridade entre o que o usuário digitou e um nome de contato.
    Combina substring e token overlap. Retorna valor entre 0 e 1.
    """
    sn = normalize_for_match(search)
    cn = normalize_for_match(candidate_name)
    if not sn:
        return 0.0
    if sn == cn:
        return 1.0
    sub = _substring_score(search, candidate_name)
    token = _token_set_ratio(sn, cn)
    # Se search é substring do nome (ex: "douglas" em "douglas moretti"), prioriza
    if sub >= 0.7:
        return max(sub, token)
    return max(sub, token * 0.9)


def resolve_contact(
    user_input: str,
    contact_list: List[Tuple[str, str]],
    accept_threshold: float = DEFAULT_ACCEPT_THRESHOLD,
    suggest_threshold: float = DEFAULT_SUGGEST_THRESHOLD,
) -> Tuple[Optional[str], Optional[str], float, Optional[List[Tuple[str, str]]]]:
    """
    Encontra o melhor contato por similaridade.

    Args:
        user_input: O que o usuário digitou (ex: "douglas", "douglas morett")
        contact_list: Lista de (jid, nome_exibicao) ou (identificador, nome)
        accept_threshold: Score mínimo para aceitar direto
        suggest_threshold: Score mínimo para sugerir "Você quis dizer X?"

    Returns:
        (jid_ou_identificador, nome_resolvido, score, candidatos_empatados)
        - Se um único match acima de accept_threshold: (jid, nome, score, None)
        - Se vários acima de suggest_threshold: (None, None, 0, [(jid, nome), ...])
        - Se um único entre suggest e accept: (jid, nome, score, None)  # aceita mas pode avisar
        - Se nenhum: (None, None, 0, lista dos top 2 por score para sugerir)
    """
    user_input = (user_input or "").strip()
    if not user_input:
        return None, None, 0.0, None

    scored: List[Tuple[str, str, float]] = []
    for jid, display_name in contact_list:
        name = (display_name or "").strip() or jid
        score = similarity_score(user_input, name)
        if score > 0:
            scored.append((jid, name, score))

    scored.sort(key=lambda x: x[2], reverse=True)

    if not scored:
        return None, None, 0.0, None

    best_jid, best_name, best_score = scored[0]

    if best_score >= accept_threshold:
        # Um claro vencedor
        return best_jid, best_name, best_score, None

    # Verifica empate: vários com score próximo do melhor
    ties = [(j, n) for j, n, s in scored if s >= suggest_threshold and s >= best_score * 0.95]
    if len(ties) > 1:
        return None, None, best_score, ties[:5]

    if len(ties) == 1 and best_score >= suggest_threshold:
        return best_jid, best_name, best_score, None

    # Nenhum bom: retorna melhores para sugerir
    if best_score >= 0.3:
        return None, None, best_score, [(j, n) for j, n, s in scored[:3]]
    return None, None, 0.0, None
