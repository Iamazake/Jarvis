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
import json
import asyncio
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except ImportError:
    pass


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--message', required=True, help='Mensagem do usuário')
    p.add_argument('--jid', default='', help='JID do remetente (ex.: 5511...@s.whatsapp.net) para autopilot')
    p.add_argument('--sender', default='user', help='Nome do remetente (display) ou user para CLI')
    args = p.parse_args()

    def output(obj):
        print(json.dumps(obj, ensure_ascii=False))

    async def run():
        from core.config import Config
        from core.context_manager import ContextManager
        from core.jarvis import Jarvis

        # Mensagem vinda do WhatsApp: decidir reply/ignore por JID (ou por nome se jid não veio)
        identifier = (args.jid or '').strip() or (args.sender or '').strip()
        is_whatsapp = identifier.lower() not in ('', 'user', 'test')
        if is_whatsapp:
            ctx = ContextManager()
            # Regra de ouro: ao receber mensagem, atualizar nome -> JID real para autopilot usar o mesmo JID
            if args.jid and "@" in args.jid and args.sender:
                ctx.update_contact_seen(args.jid, args.sender)
            if not ctx.is_autopilot_enabled_for(identifier):
                output({'action': 'ignore', 'response': '', 'reason': 'not_in_autopilot'})
                return None

        # JID normalizado (LID -> @s.whatsapp.net) para histórico e contexto consistentes
        jid_for_context = (ctx.normalize_jid(args.jid) or args.jid or "").strip() if is_whatsapp else (args.jid or "")

        jarvis = Jarvis()
        try:
            await jarvis.start()
            # Usa últimas 8 mensagens desse contato como contexto (histórico por JID)
            if jid_for_context and "@" in jid_for_context:
                jarvis.context.set_current_whatsapp_jid(jid_for_context)
            response = await jarvis.process(
                args.message,
                source='whatsapp',
                metadata={'pushName': args.sender, 'jid': jid_for_context or None}
            )
            return response
        finally:
            await jarvis.stop()

    try:
        response = asyncio.run(run())
        if response is not None:
            output({'action': 'reply', 'response': response, 'cached': False})
    except Exception as e:
        output({
            'action': 'ignore',
            'response': '',
            'reason': 'error',
            'error': str(e)
        })
        sys.exit(0)


if __name__ == '__main__':
    main()
