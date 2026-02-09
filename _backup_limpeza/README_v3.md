# 🤖 JARVIS - Assistente Virtual Inteligente v3.0

> *"Just A Rather Very Intelligent System"* - Inspirado no assistente do Homem de Ferro

[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 🚀 Início Rápido

### Windows
```batch
# 1. Abra o terminal na pasta do projeto
cd C:\YAmazake\jarvis

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Configure o .env (já feito se você tem as chaves)

# 4. Execute o JARVIS
python jarvis.py
```

### Com Menu Interativo
```batch
start.bat
```

## 📋 Funcionalidades

### ✅ Implementado
- 🗣️ **Voz** - Síntese de voz com pyttsx3
- 🔍 **Pesquisa Web** - DuckDuckGo, Wikipedia
- 🖥️ **Controle do PC** - Executar comandos, abrir apps
- 📁 **Gerenciamento de Arquivos** - Listar, criar, mover
- 💬 **CLI Interativo** - Interface colorida com Rich
- 🤖 **IA** - OpenAI GPT-4 integrado
- 📱 **WhatsApp** - Via Baileys (Node.js)

### 🔜 Em Desenvolvimento
- 🎤 Reconhecimento de voz (PyAudio + Whisper)
- 📅 Calendário e lembretes
- 📱 WhatsApp avançado (smart replies)
- 🧠 Memória de longo prazo

## 🎯 Comandos CLI

| Comando | Descrição |
|---------|-----------|
| `/help` | Lista todos os comandos |
| `/voice` | Ativa/desativa resposta por voz |
| `/search <termo>` | Pesquisa na web |
| `/wiki <termo>` | Pesquisa na Wikipedia |
| `/exec <comando>` | Executa comando no terminal |
| `/sysinfo` | Informações do sistema |
| `/clear` | Limpa a tela |
| `/quit` | Sai do JARVIS |

## 📁 Estrutura

```
jarvis/
├── jarvis.py           # 🚀 Ponto de entrada
├── start.bat           # 🖥️ Menu Windows
├── test_setup.py       # 🧪 Teste de configuração
├── config.json         # ⚙️ Configurações
├── .env                # 🔑 Chaves de API
│
├── core/               # 🧠 Núcleo
│   ├── jarvis.py       # Classe principal
│   ├── orchestrator.py # Orquestrador de módulos
│   ├── intent_classifier.py
│   └── context_manager.py
│
├── modules/            # 🔌 Módulos
│   ├── voice/          # 🗣️ Voz (pyttsx3)
│   ├── search/         # 🔍 Pesquisa (DDG, Wiki)
│   ├── tools/          # 🛠️ Ferramentas (shell, apps)
│   └── ai/             # 🤖 IA (OpenAI)
│
├── interfaces/         # 🖼️ Interfaces
│   └── cli/            # Terminal (Rich)
│
├── services/           # 🌐 Serviços Node.js
│   ├── whatsapp/       # WhatsApp (Baileys)
│   └── api/            # API REST (Fastify)
│
└── src/                # 📦 Código legado v2
    ├── ai/             # Motor de IA original
    └── cache/          # Cache semântico FAISS
```

## ⚙️ Configuração

### Variáveis de Ambiente (.env)

```env
# Obrigatório
OPENAI_API_KEY=sk-...

# Opcional
OPENWEATHER_API_KEY=...
ELEVENLABS_API_KEY=...
```

### Configurações (config.json)

```json
{
  "voice": {
    "enabled": true,
    "engine": "pyttsx3"
  },
  "autonomy": {
    "level": "medium",
    "proactive_suggestions": true
  }
}
```

## 🧪 Teste

```bash
python test_setup.py
```

## 📝 Exemplos de Uso

```
Você: Pesquise sobre inteligência artificial
JARVIS: [Faz pesquisa no DuckDuckGo e retorna resultado]

Você: /exec dir
JARVIS: [Lista arquivos do diretório atual]

Você: Que horas são?
JARVIS: São 14:35 do dia 05/02/2025.

Você: Abra o Chrome
JARVIS: [Abre o Google Chrome]
```

## 🏗️ Arquitetura Híbrida

```
┌─────────────────────────────────────────────────────────────────┐
│                        JARVIS v3.0                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   CLI        │  │   Voice      │  │   WhatsApp           │  │
│  │   (Python)   │  │   (pyttsx3)  │  │   (Node.js+Baileys)  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                      │               │
│         └────────────┬────┴──────────────────────┘               │
│                      ▼                                           │
│              ┌───────────────┐                                   │
│              │  Orchestrator │                                   │
│              └───────┬───────┘                                   │
│                      │                                           │
│    ┌─────────────────┼─────────────────┐                        │
│    ▼                 ▼                 ▼                        │
│ ┌──────┐        ┌──────┐         ┌──────┐                      │
│ │Search│        │Tools │         │  AI  │                      │
│ │Module│        │Module│         │Module│                      │
│ └──────┘        └──────┘         └──────┘                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 📜 Licença

MIT License - veja [LICENSE](LICENSE) para detalhes.

---

**Desenvolvido com ❤️ inspirado em Tony Stark**
