# 📱 JARVIS WhatsApp Integration

Integração completa do JARVIS com WhatsApp para enviar e receber mensagens!

## 🎯 Funcionalidades

- ✅ Enviar mensagens para contatos
- ✅ Ler mensagens recebidas
- ✅ Monitorar conversas em tempo real
- ✅ Responder automaticamente quando mencionarem "Jarvis"
- ✅ Histórico de mensagens salvo no MySQL
- ✅ Integrado como plugin do JARVIS

## 📋 Pré-requisitos

1. **Google Chrome** instalado
2. **WhatsApp** no celular
3. **MySQL** rodando com o database `jarvis_db`
4. **Python 3.8+**

## 🚀 Instalação

### 1. Instale as dependências

```bash
cd /Users/sarah/YAmazake/jarvis
pip install -r requirements_whatsapp.txt
```

### 2. Configure o banco de dados

Abra o **MySQL Workbench**, conecte no `jarvis_db` e execute o arquivo `jarvis_whatsapp_db.sql`:

```bash
# Ou via terminal:
mysql -u root -p jarvis_db < jarvis_whatsapp_db.sql
```

### 3. Verifique as credenciais no `.env`

O sistema usa as mesmas credenciais MySQL do JARVIS:

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=sua_senha
MYSQL_DATABASE=jarvis_db
```

## ▶️ Como Usar

### Opção 1: Script Standalone (Independente)

```bash
python jarvis_whatsapp.py
```

Isso abre um menu interativo para:
- Enviar mensagens
- Ler mensagens
- Monitorar conversas

### Opção 2: Via JARVIS (Comandos de Voz/Texto)

Inicie o JARVIS normalmente:

```bash
python3 jarvis.py --no-voice
```

Depois use comandos como:

```
Conectar WhatsApp
Enviar mensagem para João: Olá!
Ler mensagens do João
Status WhatsApp
Monitorar WhatsApp de João, Maria
Desconectar WhatsApp
```

## 🔐 Primeira Execução

1. O Chrome abre automaticamente
2. Escaneie o **QR Code** com seu celular:
   - WhatsApp → Configurações → Aparelhos Conectados → Conectar Aparelho
3. **IMPORTANTE:** Marque "Mantenha-me conectado" para não precisar escanear toda vez!

A sessão fica salva em `data/whatsapp_session/`

## 🤖 Comandos Via WhatsApp

Envie mensagens mencionando "Jarvis":

```
Jarvis, que horas são?
→ ⏰ Agora são 14:30

Jarvis, que dia é hoje?
→ 📅 Hoje é 27/01/2026

Jarvis, ajuda
→ Lista de comandos disponíveis
```

## 📊 Consultar Histórico no MySQL

```sql
-- Ver todas as mensagens
SELECT * FROM whatsapp_messages 
ORDER BY timestamp DESC 
LIMIT 50;

-- Ver mensagens de um contato
SELECT * FROM whatsapp_messages 
WHERE contact_name = 'João Silva' 
ORDER BY timestamp DESC;

-- Ver comandos executados
SELECT * FROM whatsapp_commands 
ORDER BY executed_at DESC;
```

## ⚠️ Troubleshooting

### Chrome não abre
- Verifique se o Google Chrome está instalado
- Tente: `pip install --upgrade webdriver-manager`

### Não encontra o contato
- Digite o nome **exatamente** como aparece no WhatsApp
- Para grupos, use o nome completo do grupo

### Desconecta frequentemente
- Marque "Mantenha-me conectado" no login
- Não use o WhatsApp Web em outro navegador

## 🔒 Segurança

- As credenciais ficam no `.env` (nunca commite esse arquivo!)
- A sessão do WhatsApp fica salva localmente em `data/whatsapp_session/`
- Não deixe o monitoramento rodando em computadores públicos

## 📁 Arquivos Criados

```
jarvis/
├── plugins/whatsapp.py        # Plugin integrado ao JARVIS
├── jarvis_whatsapp.py         # Script standalone
├── jarvis_whatsapp_db.sql     # SQL para criar tabelas
├── requirements_whatsapp.txt  # Dependências extras
└── data/whatsapp_session/     # Sessão salva do Chrome
```

---

**Desenvolvido para o projeto JARVIS** 🤖
