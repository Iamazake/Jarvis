# Dados e persistência nos módulos

## Banco de dados

**Nenhum dos módulos implementados exige um banco de dados externo** (PostgreSQL, MySQL, SQLite etc.) para funcionar.

- O JARVIS pode usar **SQLite** ou outros repositórios apenas onde já estiver configurado (ex.: memória/convos antigos, se existir).
- Os **novos módulos** (sentimento, produtividade, backup, segurança, tradução, dashboard) **não se conectam a BD** para salvar ou gravar dados.

## Onde cada módulo guarda dados

| Módulo        | Onde guarda                         | Observação                          |
|---------------|-------------------------------------|-------------------------------------|
| **Sentimento**| Memória (RAM), fila limitada        | Estatísticas de humor na sessão     |
| **Produtividade** | Memória (lista de sessões)     | Sessões de foco na sessão atual     |
| **Backup**    | Arquivos em `data/backups/`          | JSON (config e memórias)            |
| **Segurança** | Arquivos em `data/audit/`           | JSONL (log de auditoria)            |
| **Tradução**  | Nada persistente                     | Só traduz na hora                    |
| **Dashboard** | Nada próprio                         | Lê status/histórico do JARVIS       |
| **WhatsApp**  | Nada próprio                         | Usa a API do serviço Node (Baileys) |
| **Memória**   | Depende do repositório configurado   | Pode usar arquivo ou BD se existir  |

Conclusão: **não é necessário configurar banco de dados** para as funções implantadas; arquivos em disco e memória são suficientes.
