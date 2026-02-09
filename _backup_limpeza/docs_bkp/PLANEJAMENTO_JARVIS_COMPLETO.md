# 🤖 JARVIS - Planejamento Completo do Assistente Virtual

> *"Às suas ordens, senhor."* - J.A.R.V.I.S.

## 📊 Diagnóstico Atual

### ✅ O que já está feito:
1. **WhatsApp Service (Baileys)** - Conexão estável, envio/recebimento de mensagens
2. **API REST (Fastify)** - Bridge entre Node.js e Python
3. **AI Engine** - Integração com OpenAI, Claude, Ollama
4. **Cache Semântico (FAISS)** - Respostas instantâneas para perguntas similares
5. **Database (SQLite)** - Histórico de conversas
6. **CLI Interface** - Menu interativo básico

### ❌ O que falta para ser um Jarvis completo:
- Autonomia (ações proativas)
- Conversação natural (não só WhatsApp)
- Pesquisa na web
- Controle de sistema/apps
- Memória de longo prazo contextual
- Integração com calendário/tarefas
- Interface de voz
- Orquestrador central

---

## 🎯 Visão do Projeto JARVIS

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          🤖 JARVIS - O Assistente Completo                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│                            ┌──────────────────────┐                             │
│                            │    🧠 JARVIS CORE    │                             │
│                            │    (Orquestrador)    │                             │
│                            │  • Decision Engine   │                             │
│                            │  • Task Scheduler    │                             │
│                            │  • Context Manager   │                             │
│                            └──────────┬───────────┘                             │
│                                       │                                          │
│     ┌─────────────────────────────────┼─────────────────────────────────┐       │
│     │                                 │                                  │       │
│     ▼                                 ▼                                  ▼       │
│ ┌─────────┐  ┌─────────┐  ┌─────────────────┐  ┌──────────┐  ┌─────────────┐   │
│ │   🗣️   │  │   📱    │  │      🔧        │  │    🔍    │  │     📅      │   │
│ │  VOICE  │  │ WHATSAPP│  │     TOOLS      │  │  SEARCH  │  │  CALENDAR   │   │
│ │ MODULE  │  │ MODULE  │  │    MODULE      │  │  MODULE  │  │   MODULE    │   │
│ │         │  │         │  │                │  │          │  │             │   │
│ │• STT    │  │• Baileys│  │• Shell cmds    │  │• Google  │  │• Lembretes  │   │
│ │• TTS    │  │• Send   │  │• File ops      │  │• Brave   │  │• Eventos    │   │
│ │• Whisper│  │• Monitor│  │• Apps control  │  │• Perplx  │  │• Rotinas    │   │
│ │• Wake   │  │• Auto   │  │• Web scraping  │  │• WikiAPI │  │• Alarmes    │   │
│ └─────────┘  └─────────┘  └─────────────────┘  └──────────┘  └─────────────┘   │
│                                                                                  │
│     ┌─────────────────────────────────────────────────────────────────────┐     │
│     │                        💾 MEMÓRIA & CONTEXTO                         │     │
│     │  • Perfil do usuário   • Histórico de conversas   • Preferências   │     │
│     │  • Relacionamentos     • Padrões de uso           • Aprendizado    │     │
│     └─────────────────────────────────────────────────────────────────────┘     │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Módulos do Sistema

### 1. 🧠 JARVIS CORE (Orquestrador Central)
**Objetivo:** Cérebro do Jarvis - decide o que fazer e quando fazer

**Funcionalidades:**
- **Intent Recognition** - Entende o que você quer (comando vs conversa vs pergunta)
- **Task Router** - Direciona para o módulo correto
- **Context Manager** - Mantém contexto da conversa
- **Autonomy Engine** - Ações proativas baseadas em padrões
- **Priority Queue** - Gerencia múltiplas tarefas

**Tecnologias:**
- Python AsyncIO para concorrência
- State Machine para gerenciamento de estados
- Event-Driven Architecture

```
jarvis/
├── core/
│   ├── orchestrator.py      # Cérebro principal
│   ├── intent_classifier.py # Classifica intenções
│   ├── task_router.py       # Roteia para módulos
│   ├── context_manager.py   # Gerencia contexto
│   └── autonomy_engine.py   # Motor de autonomia
```

---

### 2. 🗣️ VOICE MODULE (Interação por Voz)
**Objetivo:** Conversar naturalmente como o Jarvis do filme

**Funcionalidades:**
- **Wake Word Detection** - "Hey Jarvis" / "Jarvis"
- **Speech-to-Text** - OpenAI Whisper (local ou API)
- **Text-to-Speech** - ElevenLabs / Azure TTS / pyttsx3
- **Continuous Listening** - Modo sempre ativo (opcional)

**Tecnologias:**
- pvporcupine (wake word)
- openai-whisper / whisper.cpp
- pygame / sounddevice (áudio)

```
jarvis/
├── modules/
│   └── voice/
│       ├── listener.py      # Captura áudio
│       ├── transcriber.py   # STT (Whisper)
│       ├── synthesizer.py   # TTS 
│       └── wake_word.py     # Detecção de wake word
```

---

### 3. 📱 WHATSAPP MODULE (já existente - melhorar)
**Objetivo:** Gerenciar suas mensagens de forma inteligente

**Melhorias propostas:**
- **Smart Replies** - Sugerir respostas baseadas em contexto
- **Message Prioritization** - Destacar mensagens importantes
- **Auto-responses** - Responder quando ausente (com contexto)
- **Summarization** - Resumir conversas longas
- **Action Items** - Extrair tarefas de mensagens

```
jarvis/
├── modules/
│   └── whatsapp/
│       ├── smart_reply.py   # Sugestões de resposta
│       ├── prioritizer.py   # Priorização
│       ├── summarizer.py    # Resumo de conversas
│       └── action_extractor.py # Extração de tarefas
```

---

### 4. 🔧 TOOLS MODULE (Ações no Sistema)
**Objetivo:** Controlar seu computador e executar tarefas

**Funcionalidades:**
- **Shell Commands** - Executar comandos no terminal
- **File Operations** - Criar, editar, organizar arquivos
- **App Control** - Abrir/fechar programas
- **Web Automation** - Automatizar tarefas na web
- **Screenshot/Recording** - Capturar tela

**Exemplos de uso:**
```
"Jarvis, abre o VS Code no projeto X"
"Jarvis, organiza meus downloads por tipo"
"Jarvis, cria uma pasta para o projeto Y"
"Jarvis, qual o uso de CPU agora?"
```

```
jarvis/
├── modules/
│   └── tools/
│       ├── shell.py         # Comandos de terminal
│       ├── file_manager.py  # Operações em arquivos
│       ├── app_launcher.py  # Controle de apps
│       ├── system_info.py   # Info do sistema
│       └── web_automation.py# Automação web
```

---

### 5. 🔍 SEARCH MODULE (Pesquisa Inteligente)
**Objetivo:** Buscar informações na internet para você

**Funcionalidades:**
- **Web Search** - Google, Brave, DuckDuckGo
- **Deep Research** - Perplexity AI / Tavily
- **Wikipedia** - Busca rápida de fatos
- **News** - Notícias recentes
- **YouTube** - Buscar vídeos
- **Academic** - Google Scholar, arXiv

**Exemplos de uso:**
```
"Jarvis, pesquisa sobre as novidades do Python 3.12"
"Jarvis, qual a previsão do tempo para amanhã?"
"Jarvis, me dá um resumo das notícias de tecnologia"
```

```
jarvis/
├── modules/
│   └── search/
│       ├── web_search.py    # Buscas gerais
│       ├── perplexity.py    # Pesquisa profunda
│       ├── wikipedia.py     # Fatos rápidos
│       ├── news.py          # Notícias
│       └── aggregator.py    # Combina fontes
```

---

### 6. 📅 CALENDAR MODULE (Agenda & Lembretes)
**Objetivo:** Gerenciar sua rotina e compromissos

**Funcionalidades:**
- **Reminders** - Lembretes com notificação
- **Events** - Criar eventos no Google Calendar
- **Routines** - Rotinas automáticas (manhã, noite)
- **Alarms** - Alarmes inteligentes
- **Pomodoro** - Timer para produtividade

**Exemplos de uso:**
```
"Jarvis, me lembra de ligar para o médico em 2 horas"
"Jarvis, o que tenho para amanhã?"
"Jarvis, inicia um pomodoro de 25 minutos"
"Jarvis, toda segunda às 9h me avisa para fazer backup"
```

```
jarvis/
├── modules/
│   └── calendar/
│       ├── reminders.py     # Lembretes
│       ├── events.py        # Eventos/calendário
│       ├── routines.py      # Rotinas automáticas
│       └── pomodoro.py      # Timer produtividade
```

---

### 7. 💾 MEMORY MODULE (Memória de Longo Prazo)
**Objetivo:** Lembrar de tudo sobre você e suas preferências

**Funcionalidades:**
- **User Profile** - Seus dados, preferências, estilo
- **Relationship Memory** - Informações sobre contatos
- **Episodic Memory** - Conversas passadas importantes
- **Learning** - Aprende com suas correções
- **Preferences** - Tom, formalidade, interesses

**Exemplos de memória:**
```
"O senhor prefere café sem açúcar"
"Sua mãe se chama Maria e faz aniversário em março"
"Você está trabalhando no projeto Jarvis desde janeiro"
```

```
jarvis/
├── modules/
│   └── memory/
│       ├── user_profile.py   # Perfil do usuário
│       ├── relationships.py  # Memória de contatos
│       ├── episodic.py       # Memória episódica
│       └── learner.py        # Sistema de aprendizado
```

---

## 🎨 Interfaces de Interação

### 1. **CLI Avançado** (Terminal)
Interface rica com cores, formatação e autocomplete

```
╔════════════════════════════════════════════════════════════╗
║                    🤖 JARVIS v3.0                          ║
╠════════════════════════════════════════════════════════════╣
║  Status: 🟢 Online  |  Módulos: 7/7  |  Uptime: 2h 34m     ║
╚════════════════════════════════════════════════════════════╝

[14:32] Você: Jarvis, verifica minhas mensagens do WhatsApp

[14:32] 🤖 Jarvis: Verificando suas mensagens, senhor...
        
        📱 WhatsApp - 3 novas mensagens:
        
        ⚡ Alta prioridade:
        • Mãe (há 5 min): "Você vem almoçar domingo?"
        
        📋 Normal:
        • João (há 15 min): Link do artigo
        • Grupo Dev (há 1h): 12 mensagens não lidas
        
        Deseja que eu responda alguma?

> _
```

### 2. **Web Dashboard** (Futuro)
Interface web para visualização e configuração

### 3. **Voice Interface** (Sempre ativo)
Conversa natural por voz

### 4. **WhatsApp** (Via mensagens para si mesmo)
Comandos enviados para seu próprio número

---

## 🚀 Roadmap de Implementação

### 📍 Fase 1: Fundação (2 semanas) ✅ CONCLUÍDO
- [x] Refatorar estrutura de pastas para módulos
- [x] Implementar JARVIS CORE (Orquestrador)
- [x] Criar sistema de Intent Classification
- [x] Criar CLI com interface mais rica
- [x] Criar entry point principal (jarvis.py)

### 📍 Fase 2: Inteligência (2 semanas) ✅ CONCLUÍDO
- [x] Implementar Search Module (web search)
- [x] DuckDuckGo, Wikipedia, Tavily
- [x] Criar Tools Module (comandos básicos)
- [x] Sistema de contexto persistente
- [x] Módulo de IA wrapper

### 📍 Fase 3: Voz (em andamento)
- [x] Estrutura do módulo de voz criada
- [ ] Testar STT (Whisper)
- [ ] Testar TTS (pyttsx3/ElevenLabs)
- [ ] Wake word detection

### 📍 Fase 4: WhatsApp Inteligente (1 semana)
- [ ] Smart Replies (sugestões de resposta)
- [ ] Message Prioritization
- [ ] Auto-resposta contextual
- [ ] Extração de tarefas de mensagens

### 📍 Fase 5: Produtividade (1 semana)
- [ ] Calendar Module (lembretes, eventos)
- [ ] Integração Google Calendar
- [ ] Rotinas automáticas
- [ ] Pomodoro timer

### 📍 Fase 6: Autonomia Avançada (2 semanas)
- [ ] Padrões de comportamento
- [ ] Sugestões proativas baseadas em contexto
- [ ] Execução automática de tarefas rotineiras
- [ ] Aprendizado com feedback

---

## 🏗️ Nova Estrutura de Pastas Proposta

```
jarvis/
├── 🧠 core/                      # Núcleo do sistema
│   ├── __init__.py
│   ├── jarvis.py                 # Classe principal JARVIS
│   ├── orchestrator.py           # Orquestrador de módulos
│   ├── intent_classifier.py      # Classificação de intenções
│   ├── context_manager.py        # Gerenciamento de contexto
│   └── config.py                 # Configurações centrais
│
├── 📦 modules/                   # Módulos funcionais
│   ├── __init__.py
│   │
│   ├── voice/                    # 🗣️ Interface de voz
│   │   ├── __init__.py
│   │   ├── listener.py
│   │   ├── transcriber.py
│   │   ├── synthesizer.py
│   │   └── wake_word.py
│   │
│   ├── whatsapp/                 # 📱 Integração WhatsApp
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── smart_reply.py
│   │   ├── prioritizer.py
│   │   └── summarizer.py
│   │
│   ├── search/                   # 🔍 Pesquisa web
│   │   ├── __init__.py
│   │   ├── web_search.py
│   │   ├── perplexity.py
│   │   ├── wikipedia.py
│   │   └── news.py
│   │
│   ├── tools/                    # 🔧 Ferramentas do sistema
│   │   ├── __init__.py
│   │   ├── shell.py
│   │   ├── file_manager.py
│   │   ├── app_launcher.py
│   │   └── system_info.py
│   │
│   ├── calendar/                 # 📅 Agenda e lembretes
│   │   ├── __init__.py
│   │   ├── reminders.py
│   │   ├── events.py
│   │   ├── routines.py
│   │   └── pomodoro.py
│   │
│   └── memory/                   # 💾 Memória de longo prazo
│       ├── __init__.py
│       ├── user_profile.py
│       ├── relationships.py
│       ├── episodic.py
│       └── learner.py
│
├── 🤖 ai/                        # Motor de IA (já existe, expandir)
│   ├── __init__.py
│   ├── engine.py
│   ├── providers.py
│   └── prompts/                  # Templates de prompts
│       ├── system.py
│       ├── whatsapp.py
│       └── search.py
│
├── 💾 storage/                   # Persistência de dados
│   ├── __init__.py
│   ├── database.py               # SQLite/PostgreSQL
│   ├── cache.py                  # Redis/FAISS
│   └── vector_store.py           # Embeddings
│
├── 🌐 services/                  # Serviços externos (Node.js)
│   ├── whatsapp/                 # Baileys (já existe)
│   └── api/                      # API REST (já existe)
│
├── 🖥️ interfaces/                # Interfaces de usuário
│   ├── cli/                      # Terminal
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── components.py
│   └── web/                      # Dashboard (futuro)
│       └── ...
│
├── ⚙️ config/                    # Configurações
│   ├── settings.yaml             # Config principal
│   ├── prompts.yaml              # Prompts customizáveis
│   └── modules.yaml              # Módulos ativos
│
├── 📊 data/                      # Dados persistentes
│   ├── jarvis.db                 # Banco de dados
│   ├── memory/                   # Memória de longo prazo
│   ├── cache/                    # Cache FAISS
│   └── logs/                     # Logs do sistema
│
├── 🧪 tests/                     # Testes
│   └── ...
│
├── 📖 docs/                      # Documentação
│   └── ...
│
├── jarvis.py                     # 🚀 Entry point principal
├── requirements.txt              # Dependências Python
├── docker-compose.yml            # Deploy com Docker
└── README.md                     # Documentação
```

---

## 💡 Exemplos de Uso Completo

### Cenário 1: Manhã produtiva
```
[07:00] 🤖 Jarvis: Bom dia, senhor. São 7 da manhã.
        
        📅 Sua agenda para hoje:
        • 09:00 - Reunião com equipe
        • 14:00 - Call com cliente X
        
        📱 WhatsApp (2 novas):
        • Mãe: "Bom dia filho!"
        • Chefe: "Confirma a reunião de amanhã?"
        
        ☁️ Tempo: 24°C, parcialmente nublado
        
        Posso ajudar com algo?

Você: Responde pro chefe confirmando

🤖 Jarvis: Enviando resposta para Chefe:
        "Bom dia! Sim, confirmado. Até amanhã!"
        ✅ Enviado
```

### Cenário 2: Pesquisa rápida
```
Você: Jarvis, pesquisa sobre as novidades do React 19

🤖 Jarvis: Pesquisando... 🔍

        📰 React 19 - Principais Novidades:
        
        1. **React Compiler** - Otimização automática
        2. **Server Components** - Nativos no React
        3. **Actions** - Nova forma de lidar com forms
        4. **use() hook** - Carregamento de recursos
        
        📎 Fontes:
        • react.dev/blog/react-19
        • dev.to/react-19-whats-new
        
        Quer que eu aprofunde em algum tópico?
```

### Cenário 3: Automação
```
Você: Jarvis, toda sexta às 18h me lembra de fazer backup

🤖 Jarvis: ✅ Lembrete criado:
        • Quando: Toda sexta-feira às 18:00
        • Mensagem: "Fazer backup semanal"
        • Notificação: Push + WhatsApp
        
        Deseja que eu também execute o backup automaticamente?

Você: Sim, backup da pasta Documentos pro Google Drive

🤖 Jarvis: ✅ Automação configurada:
        • Sexta 18:00 → Backup Documentos → Google Drive
        • Vou te notificar quando completar
```

---

## 🔐 Segurança & Privacidade

1. **Dados Locais** - Tudo armazenado localmente por padrão
2. **Criptografia** - Dados sensíveis criptografados
3. **Permissões** - Ações perigosas pedem confirmação
4. **Logs Auditáveis** - Histórico de todas as ações
5. **Modo Offline** - Funciona sem internet (IA local com Ollama)

---

## 📝 Próximos Passos Imediatos

1. **[ ] Aprovar este planejamento**
2. **[ ] Criar estrutura de pastas base**
3. **[ ] Implementar JARVIS CORE (orchestrator)**
4. **[ ] Migrar código existente para nova estrutura**
5. **[ ] Criar Intent Classifier básico**

---

## 🤔 Perguntas para Definir

1. **Prioridade de módulos:** Qual módulo além do WhatsApp você mais quer usar primeiro?
   - [ ] Voz (conversar falando)
   - [ ] Pesquisa (buscar na web)
   - [ ] Tools (controlar PC)
   - [ ] Calendar (lembretes)

2. **Interface principal:** Como você mais vai interagir?
   - [ ] Terminal (CLI)
   - [ ] Voz (sempre ouvindo)
   - [ ] WhatsApp (comandos por mensagem)

3. **Nível de autonomia:** Quanto você quer que ele faça sozinho?
   - [ ] Baixo: Só quando eu pedir
   - [ ] Médio: Sugestões proativas
   - [ ] Alto: Executa rotinas automaticamente

4. **Hardware disponível:** Para módulo de voz
   - [ ] Tem microfone bom?
   - [ ] GPU para Whisper local?

---

*Documento criado em: Fevereiro 2026*
*Versão: 3.0-planning*
