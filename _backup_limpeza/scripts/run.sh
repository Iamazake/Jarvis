#!/bin/bash
# JARVIS WhatsApp - Script de Inicialização

cd "$(dirname "$0")"

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 não encontrado"
    exit 1
fi

# Ativar venv se existir
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Executar
python3 main.py "$@"
