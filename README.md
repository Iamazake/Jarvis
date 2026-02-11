# 🤖 JARVIS - WhatsApp AI Assistant

Assistente virtual inteligente para WhatsApp com arquitetura híbrida **Node.js + Python**.

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                        JARVIS v2.0                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐     ┌─────────────────┐     ┌────────────┐ │
│  │   WhatsApp      │     │   JARVIS API    │     │  Python    │ │
│  │   (Baileys)     │────▶│   (Fastify)     │────▶│  AI Engine │ │
│  │   Port: 3001    │     │   Port: 5000    │     │            │ │
│  └─────────────────┘     └─────────────────┘     └────────────┘ │
│         │                        │                      │        │
│         │                        │                      ▼        │
│         ▼                        ▼               ┌────────────┐ │
│   ┌──────────┐            ┌──────────┐          │   FAISS    │ │
│   │ QR Code  │            │  SQLite  │          │   Cache    │ │
│   │ Terminal │            │   DB     │          │ Semântico  │ │
│   └──────────┘            └──────────┘          └────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## ✨ Características

- **🔌 Baileys**: Conexão WhatsApp estável (sem Chrome/Selenium)
- **🧠 IA Avançada**: OpenAI GPT-4, Claude, Ollama
- **⚡ Cache Semântico**: FAISS + embeddings para respostas instantâneas
- **📊 Multi-Perfil**: Diferentes personalidades por contato
- **🔄 Reconexão Automática**: Mantém a sessão ativa

## 🚀 Como iniciar

- **Windows:** execute `start.bat` e escolha a opção (1=CLI, 2=Voz, 3=WhatsApp, 4=Tudo).
- **Linha de comando:** `python jarvis.py` (CLI) ou `python jarvis.py --mcp` (com ferramentas).
- **Para enviar mensagem pelo WhatsApp:** o serviço WhatsApp precisa estar rodando antes (opção 3 ou 4 no `start.bat`, ou `cd services/whatsapp && node index.js`).

Guia completo: **[COMO_INICIAR.md](COMO_INICIAR.md)**.

**Dados e banco de dados:** os módulos novos (sentimento, produtividade, backup, segurança, tradução) **não usam banco de dados**; usam arquivos em `data/` ou memória. Ver [docs/DADOS_E_PERSISTENCIA.md](docs/DADOS_E_PERSISTENCIA.md).

## 📁 Estrutura do Projeto

```
jarvis/
├── start.sh              # 🚀 Script principal de inicialização
├── whatsapp.sh           # 📱 Iniciar só WhatsApp
├── main.py               # 🐍 Entry point Python (modo Selenium)
├── process_message.py    # 🔧 Processador de mensagens (chamado pela API)
│
├── services/             # Node.js Services
│   ├── whatsapp/         # Baileys WhatsApp Client
│   │   ├── index.js
│   │   └── package.json
│   └── api/              # Fastify REST API
│       ├── index.js
│       └── package.json
│
├── src/                  # Python Modules (Design Patterns)
│   ├── ai/               # AI Engine + Providers
│   │   ├── engine.py     # (Facade Pattern)
│   │   └── providers.py  # (Strategy Pattern)
│   ├── cache/            # Semantic Cache
│   │   └── semantic.py   # (Singleton + FAISS)
│   ├── database/         # Data Layer
│   │   └── repository.py # (Repository Pattern)
│   └── whatsapp/         # Legacy Selenium Client
│       ├── client.py
│       └── handlers.py
│
├── config/               # Configurações
│   └── settings.py
│
├── data/                 # Dados persistentes
│   ├── jarvis.db         # SQLite Database
│   └── faiss_cache/      # Cache embeddings
│
├── docs/                 # Documentação
└── logs/                 # Logs do sistema
```

## 🚀 Instalação

### 1. Dependências Python
```bash
cd jarvis
pip install -r requirements.txt
```

### 2. Dependências Node.js
```bash
cd services/whatsapp && npm install
cd ../api && npm install
```

### 3. Configurar API Keys
```bash
export OPENAI_API_KEY="sk-..."
# ou crie um arquivo .env
```

## ▶️ Execução

### Modo Recomendado (Node.js + Python)
```bash
./start.sh
# Selecione opção 1 para iniciar todos os serviços
```

### Apenas WhatsApp
```bash
./whatsapp.sh
# Escaneie o QR code que aparecerá no terminal
```

### Modo Python Legado (Selenium)
```bash
python3 main.py
```

## 📡 API Endpoints

### WhatsApp Service (Port 3001)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/status` | Status da conexão |
| POST | `/send` | Enviar mensagem |

### JARVIS API (Port 5000)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/health` | Health check |
| GET | `/stats` | Estatísticas |
| POST | `/webhook` | Receber mensagens do WhatsApp |
| POST | `/queue` | Enfileirar mensagem (autopilot) |
| POST | `/process` | Processar mensagem via IA |
| POST | `/send` | Enviar via WhatsApp (proxy) |

## Autopilot, histórico e resumos

### Habilitar autopilot
- Pelo WhatsApp: diga **"autopilot para [nome do contato]"** ou **"quando [nome] mandar mensagem, responda"**. O JARVIS ativa a auto-resposta para esse contato por 2h (renovável ao receber mensagem).
- **Grupos (@g.us):** autopilot **OFF por padrão** e **só o admin** pode ativar. Ex.: "ative autopilot para o grupo X" — se quem pedir não for o `JARVIS_ADMIN_JID`, a resposta será "Só o administrador pode ativar o autopilot em grupos."

### Pedir resumo
- **"resumo autopilot do [contato] hoje"** — resumo do dia.
- **"resumo autopilot do [contato] 24h"** — últimas 24 horas.
- **"resumo autopilot do [contato] 50 mensagens"** — últimas N mensagens (até 500).
- **Privacidade:** só o **admin** pode pedir resumo de qualquer chat; um contato só pode pedir resumo do **próprio** chat. O requester é identificado pelo header `X-Jarvis-Requester-Jid` (não pelo body).

### Migrations (MySQL)
Para persistir histórico (`conversation_events`) e resumos (`autopilot_summaries`):

```bash
mysql -u root -p jarvis_db < jarvis/migrations/001_conversation_events.sql
mysql -u root -p jarvis_db < jarvis/migrations/002_autopilot_summaries.sql
```

### .env (autopilot e API interna)
- **MySQL:** `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`.
- **Admin (resumo de terceiros):** `JARVIS_ADMIN_JID=5511985751247@s.whatsapp.net` (seu número).
- **Chamadas internas API ↔ WhatsApp:** `JARVIS_INTERNAL_SECRET` (valor compartilhado para headers `X-Jarvis-Internal`).
- **Dados (context_state.json):** `JARVIS_DATA_DIR` opcional; padrão `data/` na raiz do projeto.

### Testes
- **API (Node):** `cd jarvis/services/api && node --test tests/autopilot-summary.test.js` (privacidade: requester via header, 403/200).
- **Python (autopilot storage):** `cd jarvis && python tests/test_autopilot_storage.py`.

## 🔧 Configuração

### Variáveis de Ambiente
```env
# IA
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
OLLAMA_URL=http://localhost:11434

# Database
DATABASE_URL=sqlite:///data/jarvis.db

# Serviços
WHATSAPP_PORT=3001
API_PORT=5000
```

## 🛠️ Tecnologias

- **Node.js 18+**: Baileys, Fastify
- **Python 3.10+**: OpenAI, FAISS, sentence-transformers
- **SQLite**: Armazenamento de mensagens
- **FAISS**: Cache semântico de alta performance

## 📝 Design Patterns Utilizados

- **Facade**: AI Engine simplifica providers
- **Strategy**: Múltiplos providers de IA
- **Singleton**: Cache semântico compartilhado
- **Repository**: Abstração de banco de dados
- **Observer**: Event handlers para mensagens

## 🤝 Contribuindo

1. Fork o projeto
2. Crie sua branch (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'Add nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## 📄 Licença

MIT License - veja [LICENSE](LICENSE) para detalhes.

---

**JARVIS** - *Just A Rather Very Intelligent System* 🤖
