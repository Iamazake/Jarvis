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

## Fluxo de mensagens (fila + worker)

Com `API_QUEUE_ENABLED=1` e `WA_USE_QUEUE=1` (padrão):

1. WhatsApp recebe mensagem → chama API **POST /queue** com o payload.
2. API responde **ACK em menos de ~300 ms** (enqueued ou duplicate).
3. Worker na API processa em background (Python + POST /send do WhatsApp).
4. O handler do WhatsApp **não** espera resposta nem chama `sendMessage`; o envio é feito pelo worker.

Para voltar ao modo síncrono (útil para debug): `WA_USE_QUEUE=0`. O WhatsApp passará a chamar **POST /webhook** e enviar a resposta no mesmo fluxo.

---

## Variáveis recomendadas (WhatsApp e API)

No arquivo `.env`:

```env
WA_WEBHOOK_TIMEOUT_MS=25000
WEBHOOK_PROCESS_TIMEOUT_MS=22000
WEBHOOK_IDEMPOTENCY_TTL_MS=300000
JARVIS_TIMING_LOG=1

API_QUEUE_ENABLED=1
API_QUEUE_CONCURRENCY=3
API_QUEUE_MAX_SIZE=1000
API_QUEUE_DEDUPE_TTL_MS=600000
API_WHATSAPP_SERVICE_URL=http://127.0.0.1:3001
WA_USE_QUEUE=1
WA_QUEUE_TIMEOUT_MS=2000
```

O `start.bat` já aplica `WA_WEBHOOK_TIMEOUT_MS=25000` por padrão.
Recomendação: mantenha `WEBHOOK_PROCESS_TIMEOUT_MS` menor que `WA_WEBHOOK_TIMEOUT_MS`.

---

## Autopilot (resposta automática por contato)

Com o WhatsApp e a API rodando (opção 4 no start.bat):

1. **Ativar:** "Monitore o contato [nome]" e depois "Quando ela mandar mensagem, entretenha ela" (ou "converse com o contato [nome]").
2. O JARVIS ativa o autopilot para esse contato por 2 horas. Mensagens recebidas desse contato passam a ser respondidas automaticamente.
3. **Desativar:** "Pare de responder a [nome]" ou "Desative autopilot para [nome]".
4. **Status:** "Status do autopilot" para ver quais contatos estão com auto-resposta ativa.

Só contatos com autopilot ativado recebem resposta automática; os demais são ignorados (evita responder a todos).

---

## Subir API e WhatsApp (mini guia)

1. **API (porta 5000):** `cd jarvis/services/api` e `node index.js`.
2. **WhatsApp (porta 3001):** `cd jarvis/services/whatsapp` e `node index.js`.

Testar:

- **Health:** `curl http://localhost:5000/health`
- **Status / fila:** `curl http://localhost:5000/stats` (mostra jobQueueLength, queueActiveGlobal, apiQueueEnabled)
- **Enfileirar (teste):** `curl -X POST http://localhost:5000/queue -H "Content-Type: application/json" -d "{\"message\":\"oi\",\"from_jid\":\"5511999999999@s.whatsapp.net\",\"pushName\":\"Teste\",\"message_id\":\"test-1\"}"`

Resposta esperada do /queue: `{"success":true,"status":"enqueued","message_id":"test-1"}`.

---

## Resumo

| O que você quer | O que fazer |
|-----------------|-------------|
| Só conversar | `python jarvis.py` ou `python jarvis.py --mcp` |
| Enviar WhatsApp | Iniciar WhatsApp antes (opção 3 ou 4 no start.bat), depois JARVIS |
| Menu Windows | Executar `start.bat` |
