# Como iniciar o JARVIS

## Formas de iniciar

### 1. Pelo menu (Windows)

Na pasta do JARVIS, execute:

```bat
start.bat
```

| Opção | O que faz |
|-------|-----------|
| **1** | JARVIS no terminal (CLI) |
| **2** | JARVIS com voz |
| **3** | Só o serviço WhatsApp (porta 3001) |
| **4** | Tudo (WhatsApp + API + JARVIS) — use para enviar mensagem |
| **5** | Status do sistema |
| **6** | Instalar dependências |
| **7** | Sair |

### 2. Linha de comando

```bash
python jarvis.py              # CLI
python jarvis.py --mcp        # Com ferramentas MCP (recomendado)
python jarvis.py --voice      # Com voz
python jarvis.py --status     # Ver status
python jarvis.py "comando"    # Um comando e sai
```

---

## Enviar mensagem pelo WhatsApp

O **serviço WhatsApp** precisa estar rodando antes (porta 3001).

- **Simples:** `start.bat` → opção **4 (Iniciar Tudo)**. Escaneie o QR Code e depois use o JARVIS.
- **Ou:** Terminal 1: `cd services\whatsapp` e `node index.js`. Terminal 2: `python jarvis.py --mcp`.

Se o serviço não estiver rodando, o JARVIS avisa e diz como iniciar.

---

## Resumo

| O que você quer | O que fazer |
|-----------------|-------------|
| Só conversar | `python jarvis.py` ou `python jarvis.py --mcp` |
| Enviar WhatsApp | Iniciar WhatsApp antes (opção 3 ou 4 no start.bat), depois JARVIS |
| Menu Windows | Executar `start.bat` |
