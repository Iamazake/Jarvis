# 📡 Sistema de Monitors - JARVIS

Sistema de monitoramento avançado para WhatsApp usando **Observer Pattern**.

## 🎯 Funcionalidades

| Monitor | Descrição |
|---------|-----------|
| **KeywordMonitor** | Detecta palavras-chave em mensagens (trabalho, grana, urgente...) |
| **ContactMonitor** | Alerta quando contatos específicos enviam mensagem ou ficam online |
| **MediaMonitor** | Salva e notifica mídias (fotos, vídeos, áudios) de contatos |
| **PresenceMonitor** | Rastreia status online/offline com histórico e estatísticas |

## ⚙️ Configuração

Edite `config/monitors.json`:

```json
{
  "notifier": "5511999999999@s.whatsapp.net",
  "keywords": {
    "enabled": true,
    "words": ["trabalho", "grana", "urgente"],
    "case_sensitive": false,
    "whole_word": true
  },
  "contacts": {
    "enabled": true,
    "jids": ["5511888888888@s.whatsapp.net"],
    "notify_on_message": true,
    "notify_on_online": true
  },
  "media": {
    "enabled": true,
    "contacts": null,
    "save_path": "data/media",
    "save_media": true
  },
  "presence": {
    "enabled": false,
    "notify_on_online": false,
    "cooldown_seconds": 300
  }
}
```

## 🚀 Uso Programático

```python
from src.monitors import (
    KeywordMonitor,
    ContactMonitor,
    MediaMonitor,
    PresenceMonitor,
    MonitorManager,
    load_monitors_from_config
)

# Carregar de config
manager = load_monitors_from_config()

# Ou criar manualmente
kw_monitor = KeywordMonitor(
    notifier_jid="5511999999999@s.whatsapp.net",
    keywords=["reunião", "projeto", "deadline"]
)
kw_monitor.add_keyword("entrega")

# Adicionar ao manager
manager.add(kw_monitor)

# Dispatch de eventos (chamado pelo handlers.py)
event = {
    'type': 'message',
    'sender': '5511888888888@s.whatsapp.net',
    'push_name': 'João',
    'data': {'text': 'Oi, temos reunião amanhã!'}
}
manager.dispatch(event)  # Notifica se detectar keyword
```

## 📁 Estrutura

```
src/monitors/
├── __init__.py     # Exports e factory function
├── base.py         # AbstractMonitor (classe base)
├── keyword.py      # KeywordMonitor
├── contact.py      # ContactMonitor
├── media.py        # MediaMonitor
├── presence.py     # PresenceMonitor
└── manager.py      # MonitorManager (Singleton)
```

## 🔔 Notificações

Todas as notificações são enviadas via WhatsApp para o número configurado em `notifier`:

```
🔔 [KeywordMonitor] ⚠️ Palavra detectada!
👤 De: João
🔑 Keywords: reunião, projeto
💬 Mensagem: Oi, temos reunião sobre o projeto...
```

## 🧪 Testes

```bash
cd jarvis
python3 tests/test_monitors.py
```

## 📝 Design Patterns

- **Observer**: Monitors observam eventos do WhatsApp
- **Facade**: MonitorManager simplifica interação
- **Singleton**: MonitorManager é singleton
- **Strategy**: Cada monitor tem sua estratégia de processamento
