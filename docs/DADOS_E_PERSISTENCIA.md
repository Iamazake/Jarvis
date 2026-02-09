# Dados e persistência nos módulos

## Banco de dados

**Nenhum dos módulos exige banco de dados externo** (PostgreSQL, MySQL, etc.) para funcionar.

- Os módulos (sentimento, produtividade, backup, segurança, tradução, automação) **não se conectam a BD** para salvar dados.
- Memória/convos podem usar SQLite ou arquivo onde já estiver configurado.

## Onde cada módulo guarda dados

| Módulo        | Onde guarda                    |
|---------------|--------------------------------|
| **Sentimento**| Memória (RAM), sessão          |
| **Produtividade** | Memória (sessões de foco)  |
| **Backup**    | Arquivos em `data/backups/`    |
| **Segurança** | Arquivos em `data/audit/` (JSONL) |
| **Tradução**  | Nada persistente               |
| **WhatsApp**  | Usa API do serviço Node        |
| **Memória**   | Conforme repositório configurado |

**Conclusão:** não é necessário configurar banco de dados para as funções implantadas.
