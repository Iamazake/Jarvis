#!/bin/bash
# ============================================
# JARVIS - Iniciar Todos os Serviços
# Arquitetura de Microserviços
# ============================================

cd "$(dirname "$0")"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     🤖 JARVIS - Sistema de Microserviços                  ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Matar processos antigos nas portas
echo -e "${YELLOW}🧹 Limpando processos antigos...${NC}"
lsof -ti:3001,5000,5002,5003 | xargs kill -9 2>/dev/null
sleep 1

# Criar pasta de logs
mkdir -p logs

# ========================================
# Iniciar Serviços
# ========================================

# 1. WhatsApp (Baileys) - Porta 3001
echo -e "${YELLOW}📱 [1/4] Iniciando WhatsApp Service (porta 3001)...${NC}"
cd services/whatsapp
node index.js > ../../logs/whatsapp.log 2>&1 &
PIDS[0]=$!
cd ../..
sleep 2

# 2. API (IA, Webhooks) - Porta 5000
echo -e "${YELLOW}🤖 [2/4] Iniciando API Service (porta 5000)...${NC}"
cd services/api
node index.js > ../../logs/api.log 2>&1 &
PIDS[1]=$!
cd ../..
sleep 1

# 3. Scheduler (Agendamentos) - Porta 5002
echo -e "${YELLOW}⏰ [3/4] Iniciando Scheduler Service (porta 5002)...${NC}"
cd services/scheduler
if [ ! -d "node_modules" ]; then
  npm install --silent 2>/dev/null
fi
node index.js > ../../logs/scheduler.log 2>&1 &
PIDS[2]=$!
cd ../..
sleep 1

# 4. Monitors (Alertas) - Porta 5003
echo -e "${YELLOW}👁️  [4/4] Iniciando Monitors Service (porta 5003)...${NC}"
cd services/monitors
if [ ! -d "node_modules" ]; then
  npm install --silent 2>/dev/null
fi
node index.js > ../../logs/monitors.log 2>&1 &
PIDS[3]=$!
cd ../..
sleep 1

# ========================================
# Verificar Status
# ========================================
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  📊 Status dos Serviços${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"

sleep 2

# WhatsApp
if curl -s "http://localhost:3001/health" > /dev/null 2>&1; then
  echo -e "  📱 WhatsApp:  ${GREEN}✅ Online${NC} (porta 3001)"
else
  echo -e "  📱 WhatsApp:  ${YELLOW}⏳ Iniciando...${NC} (porta 3001)"
fi

# API
if curl -s "http://localhost:5000/health" > /dev/null 2>&1; then
  echo -e "  🤖 API:       ${GREEN}✅ Online${NC} (porta 5000)"
else
  echo -e "  🤖 API:       ${YELLOW}⏳ Iniciando...${NC} (porta 5000)"
fi

# Scheduler
if curl -s "http://localhost:5002/health" > /dev/null 2>&1; then
  echo -e "  ⏰ Scheduler: ${GREEN}✅ Online${NC} (porta 5002)"
else
  echo -e "  ⏰ Scheduler: ${YELLOW}⏳ Iniciando...${NC} (porta 5002)"
fi

# Monitors
if curl -s "http://localhost:5003/health" > /dev/null 2>&1; then
  echo -e "  👁️  Monitors:  ${GREEN}✅ Online${NC} (porta 5003)"
else
  echo -e "  👁️  Monitors:  ${YELLOW}⏳ Iniciando...${NC} (porta 5003)"
fi

echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${GREEN}📁 Logs:${NC} logs/*.log"
echo -e "  ${GREEN}🛑 Parar:${NC} pkill -f 'node.*index.js'"
echo ""

# Menu
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "  ${BOLD}O que deseja fazer?${NC}"
echo ""
echo -e "  1. 🖥️  Abrir CLI interativo"
echo -e "  2. 📊 Ver logs em tempo real"
echo -e "  3. 🚪 Manter serviços e sair"
echo ""
read -p "👉 Escolha (1/2/3): " escolha

case $escolha in
  1)
    python3 cli.py
    ;;
  2)
    tail -f logs/*.log
    ;;
  *)
    echo -e "\n${GREEN}✅ Serviços rodando em background!${NC}\n"
    ;;
esac
