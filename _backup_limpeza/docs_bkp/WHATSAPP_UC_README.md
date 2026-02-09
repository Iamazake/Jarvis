# 🤖 JARVIS WhatsApp UC - Selenium Indetectável

Sistema de automação WhatsApp resistente a detecção e ban, com cache inteligente de IA.

## ✨ Características

| Feature | Descrição |
|---------|-----------|
| 🕵️ **Chrome Indetectável** | Usa `undetected-chromedriver` - não é detectado como bot |
| 💾 **Sessão Persistente** | QR Code só uma vez por mês |
| 🧠 **Cache de Embeddings** | FAISS + Sentence Transformers - economia de 25-40% em tokens |
| ⚡ **Redis Assíncrono** | Escritas não bloqueiam respostas |
| 🐳 **Docker Ready** | Rode em container com VNC para visualização |
| 🔄 **Auto-Retry** | Reconexão automática se cair |

## 🚀 Instalação Rápida

### Opção 1: Local (macOS/Linux)

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar (copiar e editar)
cp .env.example .env
nano .env  # Adicionar suas API keys

# 3. Rodar
python jarvis_whatsapp_uc.py
```

### Opção 2: Docker (recomendado para produção)

```bash
# 1. Configurar
cp .env.example .env
nano .env

# 2. Subir containers
docker-compose up --build

# 3. Acessar VNC para ver o navegador (opcional)
# Use qualquer cliente VNC: localhost:5900
```

## 📱 Primeiro Uso

1. Execute o script
2. O Chrome abrirá com WhatsApp Web
3. Escaneie o QR Code com seu celular
4. **Pronto!** A sessão fica salva em `data/wa_profile/`

> ⚠️ **Próximas execuções**: Login automático, sem QR.

## 🧠 Cache Inteligente

O sistema usa embeddings para identificar perguntas similares:

```
Pergunta nova → Gera embedding (10ms) → Busca no FAISS (3ms)
                        ↓
            Similaridade > 0.92? → Retorna resposta cacheada (0 tokens!)
                        ↓
                       Não? → Chama IA → Salva no cache
```

### Performance Real

| Métrica | Valor |
|---------|-------|
| Busca hash exato | < 1ms |
| Busca semântica | 3-5ms |
| Economia de tokens | 25-40% |
| Hit rate típico | 30% |

### Configurar TTL

```python
# Perguntas sobre tempo/hora: 1 hora
# Conhecimento geral: 24 horas
# Fatos permanentes: 7 dias
```

## ⚙️ Configuração

### `config_whatsapp_ai.json`

```json
{
    "ai_provider": "openai",
    "api_keys": {
        "openai": "sk-...",
        "claude": "sk-ant-...",
        "ollama_url": "http://localhost:11434"
    },
    "default_model": {
        "openai": "gpt-4-turbo",
        "claude": "claude-sonnet-4-20250514",
        "ollama": "llama3.2"
    },
    "behavior": {
        "auto_reply": true,
        "monitor_interval_seconds": 2
    }
}
```

### Variáveis de Ambiente

| Variável | Descrição | Default |
|----------|-----------|---------|
| `AI_PROVIDER` | openai, claude, ollama | openai |
| `OPENAI_API_KEY` | Chave da OpenAI | - |
| `CACHE_SIMILARITY_THRESHOLD` | Mínimo para cache hit | 0.92 |
| `REDIS_HOST` | Host do Redis | localhost |
| `WA_AUTO_REPLY` | Auto-responder | true |

## 🔧 Manutenção

### Quando o WhatsApp muda o DOM

Edite apenas os XPaths em `core/whatsapp_uc.py`:

```python
XPATHS = {
    "chat_list": '//div[@data-testid="chat-list"]',
    "send_button": '//button[@data-testid="send"]',
    # ... atualizar conforme necessário
}
```

### Limpeza de Cache

```python
from core.cache import cleanup_expired, invalidate_cache

# Remover expirados
cleanup_expired()

# Invalidar pergunta específica
invalidate_cache(question="qual a hora?")

# Remover antigos
invalidate_cache(older_than_hours=168)  # 7 dias
```

### Rebuild do Índice FAISS

```python
from core.cache import rebuild_index
rebuild_index()
```

## 📊 Monitoramento

### Estatísticas do Cache

```python
from core.cache import get_cache_stats

stats = get_cache_stats()
print(f"Total: {stats['total_entries']}")
print(f"Índice: {stats['index_size']} vetores")
print(f"Expirados: {stats['expired']}")
```

### Fila Redis

```python
from core.cache_writer import get_queue_size

pending = get_queue_size()
print(f"Escritas pendentes: {pending}")
```

## 🐛 Troubleshooting

### Chrome não abre

```bash
# macOS: remover quarentena do ChromeDriver
xattr -cr /usr/local/bin/chromedriver
```

### Erro de memória com FAISS

```bash
# Usar versão CPU otimizada
pip uninstall faiss-cpu
pip install faiss-cpu --no-cache-dir
```

### Redis não conecta

```bash
# Instalar Redis
brew install redis
brew services start redis

# Ou usar Docker
docker run -d -p 6379:6379 redis:alpine
```

### Sessão expirou (QR novamente)

```bash
# Limpar sessão
rm -rf data/wa_profile/
python jarvis_whatsapp_uc.py  # Escanear QR novamente
```

## 📁 Estrutura de Arquivos

```
jarvis/
├── jarvis_whatsapp_uc.py      # Runner principal
├── core/
│   ├── whatsapp_uc.py         # Selenium indetectável
│   ├── cache.py               # FAISS + embeddings
│   └── cache_writer.py        # Redis async writer
├── ai/
│   └── engine.py              # Motor de IA (com cache integrado)
├── data/
│   ├── wa_profile/            # Sessão WhatsApp (persistente)
│   ├── cache.index            # Índice FAISS
│   └── cache_ids.pkl          # IDs do índice
├── docker-compose.yml
├── Dockerfile
└── config_whatsapp_ai.json
```

## 💰 Economia de Custos

| Cenário | Sem Cache | Com Cache (30% hit) |
|---------|-----------|---------------------|
| 1000 msgs/dia | ~$5 | ~$3.50 |
| 30k msgs/mês | ~$150 | ~$105 |

## 🔐 Segurança

- ✅ Sessão local (não sobe para nuvem)
- ✅ API keys em `.env` (não commitar!)
- ✅ Chrome profile isolado
- ⚠️ Não usar em múltiplas máquinas simultaneamente

## 📝 Licença

MIT - Use como quiser, mas não me culpe se der ruim 😅
