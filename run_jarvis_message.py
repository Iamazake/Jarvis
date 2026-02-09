#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para processar uma mensagem via JARVIS (usado pela API Node).
Uso: python run_jarvis_message.py --message "texto" [--sender "nome"]
Saída: JSON com { "response": "...", "cached": false } no stdout.
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
    p.add_argument('--sender', default='user', help='Nome do remetente')
    args = p.parse_args()

    async def run():
        from core.config import Config
        from core.jarvis import Jarvis
        jarvis = Jarvis()
        try:
            await jarvis.start()
            response = await jarvis.process(args.message, source='whatsapp', metadata={'pushName': args.sender})
            return response
        finally:
            await jarvis.stop()

    try:
        response = asyncio.run(run())
        print(json.dumps({'response': response, 'cached': False}, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({
            'response': f'Desculpe, ocorreu um erro ao processar: {str(e)}',
            'cached': False,
            'error': str(e)
        }, ensure_ascii=False))
        sys.exit(1)


if __name__ == '__main__':
    main()
