# Como iniciar o JARVIS

## Formas de iniciar

### 1. Pelo menu (recomendado no Windows)

Na pasta do JARVIS, execute:

```bat
start.bat
```

No menu, escolha:

| Opção | O que faz |
|-------|-----------|
| **1** | JARVIS no terminal (CLI) – conversa por texto |
| **2** | JARVIS com voz (reconhecimento + TTS) |
| **3** | Só o **serviço WhatsApp** (porta 3001) – necessário para enviar/receber mensagens |
| **4** | **Tudo**: inicia WhatsApp + API + JARVIS (use este se quiser mandar mensagem pelo JARVIS) |
| **5** | Ver status do sistema |
| **6** | Instalar dependências (Python + Node) |
| **7** | Sair |

### 2. Pela linha de comando

Na pasta `jarvis`:

```bash
# Só JARVIS (terminal, sem WhatsApp)
python jarvis.py

# JARVIS com MCP (ferramentas automáticas, recomendado)
python jarvis.py --mcp

# Com voz
python jarvis.py --voice

# Ver status
python jarvis.py --status

# Um comando e sai
python jarvis.py "qual a previsão do tempo?"
```

---

## Enviar mensagem pelo WhatsApp

Para o JARVIS **conseguir enviar mensagem** no WhatsApp, o **serviço WhatsApp precisa estar rodando** antes.

1. **Opção mais simples (Windows):**  
   Rode `start.bat` e escolha **4 (Iniciar Tudo)**.  
   Isso sobe o serviço WhatsApp, a API e o JARVIS. Depois de escanear o QR Code no serviço WhatsApp, você pode pedir ao JARVIS para enviar mensagens.

2. **Ou em dois passos:**  
   - Abra um terminal e inicie só o WhatsApp:  
     `cd services\whatsapp` e depois `node index.js`  
     (ou use a opção **3** no `start.bat`).  
   - Escaneie o QR Code quando aparecer.  
   - Em outro terminal, inicie o JARVIS:  
     `python jarvis.py --mcp`  
     (ou use a opção **1** no `start.bat`).

Se o serviço WhatsApp **não** estiver rodando e você pedir para enviar uma mensagem, o JARVIS vai avisar que o serviço não está rodando e como iniciá-lo.

---

## Resumo rápido

| O que você quer | O que fazer |
|-----------------|-------------|
| Só conversar no terminal | `python jarvis.py` ou `python jarvis.py --mcp` |
| Conversar e mandar WhatsApp | Iniciar **primeiro** o WhatsApp (opção 3 ou 4 no `start.bat`), depois o JARVIS |
| Usar pelo menu no Windows | Executar `start.bat` e escolher a opção (1, 2, 3 ou 4) |
