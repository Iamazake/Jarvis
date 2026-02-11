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

import faulthandler
import sys
import os
import json
import asyncio
import threading
import time
from pathlib import Path

JARVIS_DIAG = os.getenv("JARVIS_DIAG", "").strip().lower() in ("1", "true", "yes")

if JARVIS_DIAG:
    faulthandler.enable(file=sys.stderr)
    # Se travar (ex.: após jarvis_stop_end), ele vai printar stacks automaticamente
    faulthandler.dump_traceback_later(10, repeat=True, file=sys.stderr)


BASE_DIR = Path(__file__).parent
# Log de diagnóstico do agente (mesmo path que context_manager para rodar com cwd=jarvis)
DEBUG_AGENT_LOG = BASE_DIR / "debug_agent.log"
sys.path.insert(0, str(BASE_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    pass

TIMING_ENABLED = os.getenv('JARVIS_TIMING_LOG', '1').strip().lower() not in ('0', 'false', 'no', 'off')
# JARVIS_DIAG já definido no topo do módulo (reutiliza)
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
        # D) Priorizar JID com "@" para identificar contato; fallback para sender
        identifier = ((args.jid or "").strip() if (args.jid and "@" in args.jid)
                      else (args.sender or "").strip())
        is_whatsapp = identifier.lower() not in ('', 'user', 'test')

        # C) ctx inicializado fora do if para evitar NameError no normalize_jid abaixo
        ctx = None
        if is_whatsapp:
            log_timing('autopilot_check_begin')
            ctx = ContextManager()
            # Regra de ouro: ao receber mensagem, atualizar nome -> JID real para autopilot usar o mesmo JID
            if args.jid and "@" in args.jid and args.sender:
                ctx.update_contact_seen(args.jid, args.sender)
            # Renova TTL do autopilot ao receber mensagem (evita expirar no meio da conversa)
            if args.jid and "@" in args.jid:
                ctx.refresh_autopilot_ttl(args.jid)
            autopilot_enabled = ctx.is_autopilot_enabled_for(identifier)
            # Diagnóstico: registrar SEMPRE cwd + storage_path + resultado
            _diag_data = {
                "identifier": identifier[:80],
                "has_jid": bool(args.jid and str(args.jid).strip()),
                "jid_preview": (str(args.jid)[:50] if args.jid else ""),
                "sender": (str(args.sender)[:50] if args.sender else ""),
                "autopilot_enabled": autopilot_enabled,
                "cwd": os.getcwd(),
                "storage_path": ctx.storage_path,
            }
            try:
                with open(DEBUG_AGENT_LOG, 'a', encoding='utf-8') as _dbg:
                    _dbg.write(
                        json.dumps({"location": "run_jarvis_message.py:autopilot_check",
                                    "message": "autopilot_check",
                                    "data": _diag_data,
                                    "timestamp": int(time.time() * 1000),
                                    "hypothesisId": "H1_H2"}) + "\n"
                    )
            except Exception:
                pass
            if JARVIS_DIAG:
                print(f"[DIAG] autopilot_check cwd={os.getcwd()} storage={ctx.storage_path} "
                      f"identifier={identifier[:60]} enabled={autopilot_enabled}",
                      file=sys.stderr, flush=True)
            log_timing('autopilot_check_end', enabled=str(bool(autopilot_enabled)).lower())
            # A) NÃO imprimir JSON aqui — devolver dict para o main() emitir 1 JSON
            if not autopilot_enabled:
                return {'action': 'ignore', 'response': '', 'reason': 'not_in_autopilot'}

        # C) JID normalizado — só chamar ctx.normalize_jid se ctx existir
        jid_for_context = ((ctx.normalize_jid(args.jid) or args.jid or "").strip()
                           if (is_whatsapp and ctx) else (args.jid or ""))
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
            if JARVIS_DIAG:
                for th in threading.enumerate():
                    print(
                        f"[DIAG] thread name={th.name!r} daemon={th.daemon} alive={th.is_alive()}",
                        file=sys.stderr,
                        flush=True,
                    )
            # Se o pipeline retornou None ou string vazia, logar motivo detalhado
            if response is None or (isinstance(response, str) and not response.strip()):
                detail = 'pipeline_returned_none' if response is None else 'pipeline_returned_empty'
                log_timing('pipeline_no_output', detail=detail)
                if JARVIS_DIAG:
                    print(f"[DIAG] {detail}: response={response!r}", file=sys.stderr, flush=True)
                try:
                    with open(DEBUG_AGENT_LOG, 'a', encoding='utf-8') as _dbg:
                        _dbg.write(
                            json.dumps({"location": "run_jarvis_message.py:pipeline_result",
                                        "message": detail,
                                        "data": {"response_type": type(response).__name__,
                                                 "response_repr": repr(response)[:200],
                                                 "jid": (args.jid or "")[:50]},
                                        "timestamp": int(time.time() * 1000)}) + "\n"
                        )
                except Exception:
                    pass
            if is_whatsapp and response is not None and (not isinstance(response, str) or response.strip()):
                return {'action': 'reply', 'response': response, 'mode': 'autopilot'}
            return response
        finally:
            log_timing('jarvis_stop_begin')
            await jarvis.stop()
            log_timing('jarvis_stop_end')

    try:
        result = asyncio.run(asyncio.wait_for(run(), timeout=SCRIPT_TIMEOUT_MS / 1000))
        # B) Se run() devolveu dict com "action" (ex.: autopilot off), emitir direto
        if isinstance(result, dict) and 'action' in result:
            output(result)
            log_timing('response_emitted', action=result.get('action', '?'),
                       reason=result.get('reason', ''))
        elif result is not None and (not isinstance(result, str) or result.strip()):
            if isinstance(result, dict) and result.get('action') == 'reply':
                output(result)
            else:
                output({'action': 'reply', 'response': result, 'cached': False})
            log_timing('response_emitted', action='reply')
        else:
            # Pipeline retornou None ou string vazia — autopilot estava ON mas IA não gerou texto
            reason = 'no_response'
            if isinstance(result, str) and not result.strip():
                reason = 'empty_response'
            output({'action': 'ignore', 'response': '', 'reason': reason})
            log_timing('response_emitted', action='ignore', reason=reason)
        log_timing('script_end', exit_code=0)
        hard_exit(0)
    except asyncio.TimeoutError:
        log_timing('timeout', timeout_ms=SCRIPT_TIMEOUT_MS)
        if JARVIS_DIAG:
            for th in threading.enumerate():
                print(
                    f"[DIAG] thread name={th.name!r} daemon={th.daemon} alive={th.is_alive()}",
                    file=sys.stderr,
                    flush=True,
                )
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
