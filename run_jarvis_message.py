#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para processar uma mensagem via JARVIS (usado pela API Node / webhook WhatsApp).
Uso: python run_jarvis_message.py --message "texto" [--jid "5511...@s.whatsapp.net"] [--sender "display name"]
Saída: JSON no stdout com:
  - action: "reply" | "ignore"  (ignore = não responder, ex.: autopilot desativado para esse contato)
  - response: texto da resposta (quando action=reply)
Identidade do remetente é por JID (--jid); --sender é só display. Se --jid não for passado, usa --sender (retrocompat).
"""

import sys
import os
import json
import asyncio
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    pass

TIMING_ENABLED = os.getenv('JARVIS_TIMING_LOG', '1').strip().lower() not in ('0', 'false', 'no', 'off')
TIMING_T0 = time.perf_counter()
SCRIPT_TIMEOUT_MS = int(os.getenv('RUN_JARVIS_MESSAGE_TIMEOUT_MS', '30000'))


def log_timing(stage: str, **extra):
    if not TIMING_ENABLED:
        return
    elapsed_ms = int((time.perf_counter() - TIMING_T0) * 1000)
    suffix = ""
    if extra:
        suffix = " " + " ".join(f"{k}={v}" for k, v in extra.items())
    print(f"[timing] {stage} +{elapsed_ms}ms{suffix}", file=sys.stderr, flush=True)


def hard_exit(code: int = 0):
    try:
        sys.stdout.flush()
    except Exception:
        pass
    try:
        sys.stderr.flush()
    except Exception:
        pass
    os._exit(code)


def main():
    import argparse
    log_timing('start')
    p = argparse.ArgumentParser()
    p.add_argument('--message', required=True, help='Mensagem do usuário')
    p.add_argument('--jid', default='', help='JID do remetente (ex.: 5511...@s.whatsapp.net) para autopilot')
    p.add_argument('--sender', default='user', help='Nome do remetente (display) ou user para CLI')
    args = p.parse_args()
    log_timing('args_parsed')

    def output(obj):
        print(json.dumps(obj, ensure_ascii=False))

    async def run():
        from core.config import Config
        from core.context_manager import ContextManager
        from core.jarvis import Jarvis
        log_timing('context_loaded')

        # Mensagem vinda do WhatsApp: decidir reply/ignore por JID (ou por nome se jid não veio)
        identifier = (args.jid or '').strip() or (args.sender or '').strip()
        is_whatsapp = identifier.lower() not in ('', 'user', 'test')
        if is_whatsapp:
            log_timing('autopilot_check_begin')
            ctx = ContextManager()
            # Regra de ouro: ao receber mensagem, atualizar nome -> JID real para autopilot usar o mesmo JID
            if args.jid and "@" in args.jid and args.sender:
                ctx.update_contact_seen(args.jid, args.sender)
            autopilot_enabled = ctx.is_autopilot_enabled_for(identifier)
            log_timing('autopilot_check_end', enabled=str(bool(autopilot_enabled)).lower())
            if not autopilot_enabled:
                output({'action': 'ignore', 'response': '', 'reason': 'not_in_autopilot'})
                log_timing('response_emitted', action='ignore', reason='not_in_autopilot')
                return None

        # JID normalizado (LID -> @s.whatsapp.net) para histórico e contexto consistentes
        jid_for_context = (ctx.normalize_jid(args.jid) or args.jid or "").strip() if is_whatsapp else (args.jid or "")
        log_timing('jid_normalized', has_context_jid=str(bool(jid_for_context)).lower())

        jarvis = Jarvis()
        try:
            log_timing('jarvis_start_begin')
            await jarvis.start()
            log_timing('jarvis_start_end')
            # Usa últimas 8 mensagens desse contato como contexto (histórico por JID)
            if jid_for_context and "@" in jid_for_context:
                jarvis.context.set_current_whatsapp_jid(jid_for_context)
            log_timing('jarvis_process_begin')
            response = await jarvis.process(
                args.message,
                source='whatsapp',
                metadata={'pushName': args.sender, 'jid': jid_for_context or None}
            )
            log_timing('jarvis_process_end')
            return response
        finally:
            log_timing('jarvis_stop_begin')
            await jarvis.stop()
            log_timing('jarvis_stop_end')

    try:
        response = asyncio.run(asyncio.wait_for(run(), timeout=SCRIPT_TIMEOUT_MS / 1000))
        if response is not None:
            output({'action': 'reply', 'response': response, 'cached': False})
            log_timing('response_emitted', action='reply')
        else:
            # Garante contrato consistente quando o pipeline não gerar texto final.
            output({'action': 'ignore', 'response': '', 'reason': 'no_response'})
            log_timing('response_emitted', action='ignore', reason='no_response')
        log_timing('script_end', exit_code=0)
        hard_exit(0)
    except asyncio.TimeoutError:
        log_timing('timeout', timeout_ms=SCRIPT_TIMEOUT_MS)
        output({
            'action': 'ignore',
            'response': '',
            'reason': 'timeout',
            'error': f'run_jarvis_message timeout após {SCRIPT_TIMEOUT_MS}ms'
        })
        log_timing('response_emitted', action='ignore', reason='timeout')
        log_timing('script_end', exit_code=0)
        hard_exit(0)
    except Exception as e:
        log_timing('exception', error=str(e)[:120])
        output({
            'action': 'ignore',
            'response': '',
            'reason': 'error',
            'error': str(e)
        })
        log_timing('response_emitted', action='ignore', reason='error')
        log_timing('script_end', exit_code=0)
        hard_exit(0)


if __name__ == '__main__':
    main()
