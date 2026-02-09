#!/usr/bin/env python3
"""
JARVIS - Processador de Mensagens
Chamado pela API Node.js para processar mensagens via IA

Uso: python3 process_message.py --message "texto" --sender "nome"
"""

import argparse
import json
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ai.engine import AIEngine
from src.cache.semantic import SemanticCache
from src.database.repository import MessageRepository


def main():
    parser = argparse.ArgumentParser(description='JARVIS Message Processor')
    parser.add_argument('--message', '-m', required=True, help='Mensagem a processar')
    parser.add_argument('--sender', '-s', default='user', help='Nome do remetente')
    parser.add_argument('--provider', '-p', default='openai', help='Provider de IA')
    
    args = parser.parse_args()
    
    try:
        # Inicializa componentes
        cache = SemanticCache()
        ai_engine = AIEngine(cache=cache)
        repo = MessageRepository()
        
        # Verifica cache primeiro
        cached = cache.get_cached_answer(args.message)
        
        if cached:
            result = {
                'response': cached,
                'cached': True,
                'sender': args.sender,
                'provider': 'cache'
            }
        else:
            # Gera resposta via IA
            response = ai_engine.generate_response(
                message=args.message,
                sender=args.sender,
                provider=args.provider
            )
            
            # Cacheia a resposta
            cache.cache_answer(args.message, response)
            
            result = {
                'response': response,
                'cached': False,
                'sender': args.sender,
                'provider': args.provider
            }
        
        # Salva no histórico
        repo.save_message(
            sender=args.sender,
            message=args.message,
            response=result['response'],
            cached=result['cached']
        )
        
        # Output JSON para Node.js
        print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
        error_result = {
            'response': f'Erro ao processar: {str(e)}',
            'cached': False,
            'error': True,
            'error_message': str(e)
        }
        print(json.dumps(error_result, ensure_ascii=False))
        sys.exit(1)


if __name__ == '__main__':
    main()
