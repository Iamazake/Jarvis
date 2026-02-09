#!/bin/bash
#
# JARVIS - Script de Inicialização
# Inicia todos os serviços: WhatsApp (Baileys) + API + Python
#

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Diretório base
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Banner
echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                                                               ║"
echo "║       ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗               ║"
echo "║       ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝               ║"
echo "║       ██║███████║██████╔╝██║   ██║██║███████╗               ║"
echo "║  ██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║               ║"
echo "║  ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║               ║"
echo "║   ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝               ║"
echo "║                                                               ║"
echo "║              WhatsApp AI Assistant v2.0                       ║"
echo "║              Node.js (Baileys) + Python (AI)                  ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Função para limpar processos ao sair
cleanup() {
    echo -e "\n${YELLOW}Encerrando serviços...${NC}"
    
    if [ ! -z "$PID_API" ]; then
        kill $PID_API 2>/dev/null || true
    fi
    
    if [ ! -z "$PID_WHATSAPP" ]; then
        kill $PID_WHATSAPP 2>/dev/null || true
    fi
    
    echo -e "${GREEN}✓ Serviços encerrados${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Verifica Node.js
check_node() {
    if ! command -v node &> /dev/null; then
        echo -e "${RED}✗ Node.js não encontrado!${NC}"
        echo "  Instale: brew install node"
        exit 1
    fi
    NODE_VERSION=$(node -v)
    echo -e "${GREEN}✓ Node.js: $NODE_VERSION${NC}"
}

# Verifica Python
check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}✗ Python3 não encontrado!${NC}"
        exit 1
    fi
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓ $PYTHON_VERSION${NC}"
}

# Instala dependências Node.js
install_node_deps() {
    echo -e "\n${BLUE}📦 Verificando dependências Node.js...${NC}"
    
    # API
    if [ ! -d "services/api/node_modules" ]; then
        echo -e "${YELLOW}  Instalando dependências da API...${NC}"
        cd services/api && npm install --silent && cd ../..
    fi
    echo -e "${GREEN}  ✓ API: dependências OK${NC}"
    
    # WhatsApp
    if [ ! -d "services/whatsapp/node_modules" ]; then
        echo -e "${YELLOW}  Instalando dependências do WhatsApp...${NC}"
        cd services/whatsapp && npm install --silent && cd ../..
    fi
    echo -e "${GREEN}  ✓ WhatsApp: dependências OK${NC}"
}

# Inicia serviço API
start_api() {
    echo -e "\n${BLUE}🚀 Iniciando API...${NC}"
    cd services/api
    node index.js &
    PID_API=$!
    cd ../..
    sleep 2
    
    if kill -0 $PID_API 2>/dev/null; then
        echo -e "${GREEN}  ✓ API rodando (PID: $PID_API)${NC}"
    else
        echo -e "${RED}  ✗ Falha ao iniciar API${NC}"
        exit 1
    fi
}

# Inicia serviço WhatsApp
start_whatsapp() {
    echo -e "\n${BLUE}📱 Iniciando WhatsApp...${NC}"
    cd services/whatsapp
    node index.js &
    PID_WHATSAPP=$!
    cd ../..
    sleep 3
    
    if kill -0 $PID_WHATSAPP 2>/dev/null; then
        echo -e "${GREEN}  ✓ WhatsApp rodando (PID: $PID_WHATSAPP)${NC}"
    else
        echo -e "${RED}  ✗ Falha ao iniciar WhatsApp${NC}"
        exit 1
    fi
}

# Menu principal
show_menu() {
    echo -e "\n${CYAN}═══════════════════════════════════════════${NC}"
    echo -e "${CYAN}  Escolha uma opção:${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════${NC}"
    echo "  1) Iniciar todos os serviços"
    echo "  2) Apenas WhatsApp (Baileys)"
    echo "  3) Apenas API"
    echo "  4) Modo Python (Selenium - fallback)"
    echo "  5) Instalar dependências"
    echo "  6) Status dos serviços"
    echo "  0) Sair"
    echo ""
    read -p "  Opção: " choice
    
    case $choice in
        1)
            check_node
            check_python
            install_node_deps
            start_api
            start_whatsapp
            echo -e "\n${GREEN}═══════════════════════════════════════════${NC}"
            echo -e "${GREEN}  ✅ JARVIS está online!${NC}"
            echo -e "${GREEN}═══════════════════════════════════════════${NC}"
            echo -e "  📡 API: http://localhost:5000"
            echo -e "  📱 WhatsApp: http://localhost:3001"
            echo -e "\n${YELLOW}  Pressione Ctrl+C para encerrar${NC}"
            
            # Mantém o script rodando
            wait
            ;;
        2)
            check_node
            install_node_deps
            cd services/whatsapp && node index.js
            ;;
        3)
            check_node
            install_node_deps
            cd services/api && node index.js
            ;;
        4)
            check_python
            echo -e "\n${BLUE}🐍 Iniciando modo Python (Selenium)...${NC}"
            python3 main.py
            ;;
        5)
            check_node
            check_python
            install_node_deps
            echo -e "\n${BLUE}📦 Instalando dependências Python...${NC}"
            pip3 install -r requirements.txt
            echo -e "${GREEN}✅ Dependências instaladas!${NC}"
            show_menu
            ;;
        6)
            echo -e "\n${BLUE}📊 Status dos serviços:${NC}"
            
            # Verifica API
            if curl -s http://localhost:5000/health > /dev/null 2>&1; then
                echo -e "  ${GREEN}✓ API: Online${NC}"
            else
                echo -e "  ${RED}✗ API: Offline${NC}"
            fi
            
            # Verifica WhatsApp
            if curl -s http://localhost:3001/status > /dev/null 2>&1; then
                echo -e "  ${GREEN}✓ WhatsApp: Online${NC}"
            else
                echo -e "  ${RED}✗ WhatsApp: Offline${NC}"
            fi
            
            show_menu
            ;;
        0)
            echo -e "${GREEN}Até logo! 👋${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Opção inválida!${NC}"
            show_menu
            ;;
    esac
}

# Execução
echo -e "${BLUE}Verificando ambiente...${NC}"
check_node
check_python

# Se passou argumentos, executa direto
if [ "$1" == "--all" ] || [ "$1" == "-a" ]; then
    install_node_deps
    start_api
    start_whatsapp
    echo -e "\n${GREEN}✅ JARVIS está online!${NC}"
    wait
elif [ "$1" == "--whatsapp" ] || [ "$1" == "-w" ]; then
    install_node_deps
    cd services/whatsapp && node index.js
elif [ "$1" == "--api" ]; then
    install_node_deps
    cd services/api && node index.js
elif [ "$1" == "--python" ] || [ "$1" == "-p" ]; then
    python3 main.py
else
    show_menu
fi
