# 🏗️ JARVIS - Arquitetura de Microserviços

## 📊 Visão Geral

```
┌─────────────────────────────────────────────────────────────────┐
│                        VOCÊ (CLI / Web)                         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   WhatsApp    │◄───│     API       │◄───│   Scheduler   │
│   Service     │    │   Service     │    │   Service     │
│   :3001       │    │   :5000       │    │   :5002       │
│               │    │               │    │               │
│ • Baileys     │    │ • OpenAI      │    │ • Cron jobs   │
│ • Sessão      │    │ • Webhooks    │    │ • Lembretes   │
│ • Send/Recv   │    │ • Generate    │    │ • Agendados   │
└───────┬───────┘    └───────────────┘    └───────────────┘
        │
        │ Eventos
        ▼
┌───────────────┐
│   Monitors    │
│   Service     │
│   :5003       │
│               │
│ • Keywords    │
│ • VIP alerts  │
│ • Anti-spam   │
│ • Presença    │
└───────────────┘
```

## 🔌 Portas

| Serviço | Porta | Responsabilidade |
|---------|-------|------------------|
| WhatsApp | 3001 | Conexão Baileys, enviar/receber |
| API | 5000 | IA (OpenAI), processamento |
| Scheduler | 5002 | Agendamentos, lembretes |
| Monitors | 5003 | Alertas, keywords, VIP |

## 📁 Estrutura de Pastas

```
jarvis/
├── services/                    ← Node.js (processos leves)
│   ├── whatsapp/               # Baileys, sessão WhatsApp
│   │   ├── index.js
│   │   ├── package.json
│   │   └── auth_info/          # Credenciais
│   │
│   ├── api/                    # REST API, IA
│   │   ├── index.js
│   │   └── package.json
│   │
│   ├── scheduler/              # Agendamentos
│   │   ├── index.js
│   │   ├── package.json
│   │   └── schedules.json
│   │
│   └── monitors/               # Alertas
│       ├── index.js
│       ├── package.json
│       └── monitors_config.json
│
├── src/                         ← Python (lógica pesada)
│   ├── ai/                     # Engine de IA
│   ├── cache/                  # FAISS
│   ├── database/               # SQLite
│   └── monitors/               # Regras de negócio
│
├── shared/                      ← Contratos compartilhados
│   ├── config/                 # .env, portas
│   └── events/                 # Tipos de eventos
│
├── config/                      ← Configurações de usuário
│   ├── contacts.json
│   ├── profiles.json
│   └── monitors.json
│
├── logs/                        ← Logs de cada serviço
│   ├── whatsapp.log
│   ├── api.log
│   ├── scheduler.log
│   └── monitors.log
│
├── cli.py                       ← Interface interativa
└── iniciar.sh                   ← Script para iniciar tudo
```

## 🔄 Fluxos de Comunicação

### 1️⃣ Envio Direto (sem IA)
```
Você → POST :3001/send → WhatsApp → ✅
```

### 2️⃣ Envio com IA
```
Você → POST :5000/process → OpenAI → POST :3001/send → WhatsApp → ✅
```

### 3️⃣ Receber Mensagem + Monitoramento
```
WhatsApp → :3001 recebe → POST :5003/webhook/message → Monitors verifica
                       → POST :5000/webhook → API processa
                       → POST :3001/send → Resposta automática
```

### 4️⃣ Agendamento
```
Você → POST :5002/schedules → Scheduler salva
                           → (no horário) POST :3001/send → WhatsApp → ✅
```

### 5️⃣ Alerta de Keyword
```
Mensagem chega → :3001 → :5003 Monitors detecta "keyword"
                       → POST :3001/send (para você) → 🚨 Alerta
```

## 🚀 Como Iniciar

```bash
cd ~/YAmazake/jarvis
./iniciar.sh
```

## 🛑 Como Parar

```bash
pkill -f 'node.*index.js'
```

## 📡 Endpoints Principais

### WhatsApp (:3001)
- `GET /health` - Status
- `GET /status` - Status detalhado
- `GET /contacts` - Listar contatos
- `POST /send` - Enviar por número
- `POST /send-by-name` - Enviar por nome

### API (:5000)
- `GET /health` - Status
- `POST /process` - Processar com IA (executa ações)
- `POST /generate` - Apenas gerar texto

### Scheduler (:5002)
- `GET /schedules` - Listar agendamentos
- `POST /schedules` - Criar recorrente (cron)
- `POST /reminders` - Criar único (datetime)

### Monitors (:5003)
- `GET /health` - Status + config
- `PUT /config` - Atualizar configuração
- `POST /keywords` - Adicionar keyword
- `POST /vip` - Adicionar contato VIP
- `POST /notifier` - Seu número para alertas

## ✨ Vantagens

1. **Escala independente**: Cada serviço pode rodar em máquinas diferentes
2. **Fallback**: Se um serviço cair, os outros continuam
3. **Testes isolados**: Cada pasta tem seus próprios testes
4. **Deploy simples**: Docker por serviço
5. **Fácil extensão**: Novo monitor = novo arquivo, sem reiniciar WhatsApp
