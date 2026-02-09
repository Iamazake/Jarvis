# 🤖 JARVIS - Comandos e Uso

## Iniciar Tudo
```bash
cd ~/YAmazake/jarvis
./iniciar.sh
```

## 🎯 Funcionalidades Autônomas

### Enviar Mensagens por Voz/Texto
O JARVIS entende linguagem natural! Experimente:

```
"manda mensagem para sarah dizendo bom dia"
"fala para joão que estou atrasado"
"envia para maria que a reunião foi cancelada"
"avisa o pedro que chego em 10 minutos"
"pergunta para ana se ela vai na festa"
```

### Busca Inteligente de Contatos
O JARVIS busca contatos pelo nome, mesmo com variações:
- "sarah" encontra "Sarah Dona"
- "joao" encontra "João Silva"
- Suporta busca parcial e fuzzy matching

## 📱 API Endpoints

### Status
```bash
curl http://localhost:3001/status
curl http://localhost:5000/health
```

### Contatos
```bash
# Listar todos
curl http://localhost:3001/contacts

# Buscar por nome
curl "http://localhost:3001/contacts/search?q=sarah"

# Adicionar contato
curl -X POST http://localhost:3001/contacts/add \
  -H "Content-Type: application/json" \
  -d '{"number": "5511999999999", "name": "Nome da Pessoa"}'
```

### Enviar Mensagens
```bash
# Por número
curl -X POST http://localhost:3001/send \
  -H "Content-Type: application/json" \
  -d '{"to": "5511999999999", "message": "Olá!"}'

# Por nome (busca automática)
curl -X POST http://localhost:3001/send-by-name \
  -H "Content-Type: application/json" \
  -d '{"name": "sarah", "message": "Oi!"}'
```

### Processar com IA (Autônomo)
```bash
curl -X POST http://localhost:5000/process \
  -H "Content-Type: application/json" \
  -d '{"message": "manda mensagem para sarah dizendo bom dia"}'
```

## 🔧 CLI Interativo
```bash
python3 cli.py
```

### Menu Principal
1. 📤 Enviar mensagem (com IA)
2. 💬 Enviar mensagem direta
3. 📊 Status do sistema
4. 👁️ Configurar monitoramento
5. 👤 Configurar perfil de contato
6. 🔑 Gerenciar keywords
7. 📱 Ver contatos monitorados
8. 🔄 Verificar conexão
9. 📒 Gerenciar contatos
0. 🚪 Sair

## 📁 Estrutura de Arquivos

```
jarvis/
├── iniciar.sh           # Script para iniciar tudo
├── cli.py               # Interface interativa
├── .env                  # Configurações (OpenAI key, etc)
├── services/
│   ├── whatsapp/        # Baileys (porta 3001)
│   │   ├── index.js
│   │   ├── auth_info/   # Credenciais WhatsApp
│   │   └── contacts_cache.json
│   └── api/             # API (porta 5000)
│       └── index.js
├── config/
│   ├── contacts.json    # Contatos locais
│   ├── profiles.json    # Perfis de contatos
│   └── monitors.json    # Config de monitoramento
└── logs/
    ├── whatsapp.log
    └── api.log
```

## 🔄 Modo Autônomo

O JARVIS responde automaticamente a mensagens recebidas!

### Ativar/Desativar
```bash
# Verificar status
curl http://localhost:3001/status

# Ativar
curl -X POST http://localhost:3001/auto-reply \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'

# Desativar
curl -X POST http://localhost:3001/auto-reply \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

## 🛑 Parar Tudo
```bash
pkill -f 'node.*index.js'
```

## 🔑 Configurar OpenAI

Edite o arquivo `.env`:
```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo
```

---
*JARVIS v4.1 - Assistente Virtual Autônomo*
