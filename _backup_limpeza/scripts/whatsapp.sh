#!/bin/bash
#
# Inicia apenas o WhatsApp (Baileys) - modo interativo
#
cd "$(dirname "$0")/services/whatsapp"

echo "🤖 Iniciando JARVIS WhatsApp..."
echo "   Aguarde o QR Code aparecer (pode levar ~10 segundos)"
echo ""

exec node index.js
