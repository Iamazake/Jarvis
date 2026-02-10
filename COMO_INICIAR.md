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

## Autopilot (resposta automática por contato)

Com o WhatsApp e a API rodando (opção 4 no start.bat):

1. **Ativar:** "Monitore o contato [nome]" e depois "Quando ela mandar mensagem, entretenha ela" (ou "converse com o contato [nome]").
2. O JARVIS ativa o autopilot para esse contato por 2 horas. Mensagens recebidas desse contato passam a ser respondidas automaticamente.
3. **Desativar:** "Pare de responder a [nome]" ou "Desative autopilot para [nome]".
4. **Status:** "Status do autopilot" para ver quais contatos estão com auto-resposta ativa.

Só contatos com autopilot ativado recebem resposta automática; os demais são ignorados (evita responder a todos).

---

## Resumo

| O que você quer | O que fazer |
|-----------------|-------------|
| Só conversar | `python jarvis.py` ou `python jarvis.py --mcp` |
| Enviar WhatsApp | Iniciar WhatsApp antes (opção 3 ou 4 no start.bat), depois JARVIS |
| Menu Windows | Executar `start.bat` |
