# Capacidades do JARVIS

Documento para apresentação do assistente ao time. Lista o que o JARVIS consegue fazer e como acionar.

---

## Visão geral

O **JARVIS** (Just A Rather Very Intelligent System) é um assistente virtual que integra **WhatsApp**, **IA generativa**, **pesquisa**, **agenda** e **ferramentas**. Ele entende comandos em português e pode executar várias tarefas em sequência.

---

## Funções e modos

### 1. WhatsApp

| Função | Exemplo de comando |
|--------|--------------------|
| **Enviar mensagem** | "Mande uma mensagem para Douglas Moretti dizendo que amanhã temos reunião" |
| **Montar e enviar mensagem** | "Monte uma mensagem se apresentando e falando suas funções e envie para Douglas Moretti" |
| **Ver conversa** | "Ler as mensagens da Juliana" / "Mostre a conversa do contato Tchuchuca" |
| **Resumir conversa** | "Consegue resumir a conversa do contato Tchuchuca?" |
| **Monitorar contato** | "Monitore o contato Douglas Moretti" / "Monitore a conversa da Juliana" |
| **Ver não lidas** | "Tem mensagem nova?" / "Verificar minhas mensagens" |

- O JARVIS usa **resolução de contatos por similaridade**: "douglas" pode ser reconhecido como "Douglas Moretti".
- Se você disser "envie para **ele**" ou "monitore **dele**", ele usa o **último contato** da conversa.
- Comandos compostos: "Mande mensagem para X **e** monitore a conversa" executa as duas ações.

### 2. Pesquisa e informação

| Função | Exemplo |
|--------|---------|
| **Pesquisar** | "Pesquise sobre inteligência artificial" / "O que é machine learning?" |
| **Clima** | "Como está o tempo em São Paulo?" / "Previsão do tempo amanhã" |
| **Notícias** | "Notícias sobre tecnologia" / "O que está acontecendo no mundo?" |

### 3. Agenda e lembretes

| Função | Exemplo |
|--------|---------|
| **Lembrete** | "Me lembre de ligar para o João às 15h" |
| **Alarme** | "Coloque um alarme para 7h" |
| **Agenda** | "O que tenho na agenda amanhã?" |

### 4. Produtividade e relatórios

| Função | Exemplo |
|--------|---------|
| **Relatório do dia/semana** | "Relatório do dia" / "Relatório da semana" |
| **Sessão de foco** | "Iniciar sessão de foco" / "Encerrar sessão" |
| **Status** | "Status produtividade" |

### 5. Sentimento e análise

| Função | Exemplo |
|--------|---------|
| **Análise de humor** | "Como estou me sentindo pelas palavras?" / "Estatísticas de humor" |

### 6. Backup e segurança

| Função | Exemplo |
|--------|---------|
| **Backup** | "Fazer backup" / "Listar backups" |
| **Segurança** | "Configurar PIN" / "Últimas ações" / "Auditoria" |

### 7. Tradução

| Função | Exemplo |
|--------|---------|
| **Traduzir** | "Traduza 'hello' para português" / "Detectar idioma" |

### 8. Automação

| Função | Exemplo |
|--------|---------|
| **Workflows** | "Criar workflow" / "Listar workflows" |

### 9. Sistema e arquivos

| Função | Exemplo |
|--------|---------|
| **Arquivos** | "Criar pasta documentos" / "Listar arquivos em X" |
| **Sistema** | "Status do sistema" / "Uso de CPU" |

### 10. Conversa e IA

- O JARVIS responde a perguntas gerais, explicações e diálogo livre usando **IA (OpenAI/Claude/Ollama)**.
- Perguntas como "O que você consegue fazer?", "Quais suas funções?", "Liste suas capacidades" retornam esta lista de capacidades.

---

## Como iniciar

- **Windows:** `start.bat` → opção 1 (CLI), 2 (Voz), 3 (WhatsApp), 4 (Tudo).
- **Envio por WhatsApp:** o serviço WhatsApp (opção 3 ou 4) precisa estar rodando.

---

## Resumo para apresentação

- **Nome:** JARVIS (Just A Rather Very Intelligent System)  
- **Funções principais:** WhatsApp (enviar, ler, monitorar, resumir conversas), pesquisa, clima, notícias, lembretes, agenda, produtividade, sentimento, backup, segurança, tradução, automação, sistema/arquivos e conversa com IA.  
- **Diferenciais:** comandos em português, reconhecimento de contato por similaridade, memória de último contato, comandos compostos ("faça X e Y"), mensagem de apresentação gerada por IA.
