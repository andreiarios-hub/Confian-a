# Confiança Depósito e Armazenamento — Backend

API REST em **FastAPI** para o painel de operações (`confianca-ops-app_3.html`). Persiste as ordens de
serviço em banco de dados (SQLite em dev, PostgreSQL/Supabase em produção) e gera o relatório mensal
QuintoAndar em `.xlsx`.

## Stack

- **FastAPI** — API REST, validação automática (Pydantic) e docs interativas em `/docs`.
- **SQLAlchemy** — ORM, com `DATABASE_URL` trocável entre SQLite (dev) e PostgreSQL/Supabase (produção).
- **openpyxl** — geração do `.xlsx` do relatório, com cabeçalho estilizado e formatação de data/hora/moeda.

## Como rodar

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
copy .env.example .env          # Windows (cp no macOS/Linux)

uvicorn app.main:app --reload --port 8000
```

A API sobe em `http://localhost:8000` — documentação interativa em `http://localhost:8000/docs`.
As tabelas são criadas automaticamente no primeiro start (`confianca.db` fica em `backend/`).

Para produção, basta trocar `DATABASE_URL` no `.env` para uma URL PostgreSQL/Supabase — o código não muda.

## Modelo de dados — `ordens_servico`

| Campo                  | Tipo                                             |
|-------------------------|--------------------------------------------------|
| `id`                    | UUID (string), chave primária                    |
| `nome_cliente`          | String                                            |
| `e_quinto_andar`        | Boolean                                           |
| `numero_contrato`       | String (opcional, obrigatório se `e_quinto_andar`)|
| `data_horario`          | DateTime (API expõe `data` + `horario` separados) |
| `endereco`              | Text                                              |
| `valor_cobrado`         | Numeric(12,2)                                     |
| `custo_operacional`     | Numeric(12,2)                                     |
| `custos_adicionais`     | JSON — `[{descricao, valor}]` (guincho, munck...) |
| `quantidade_ajudantes`  | Integer                                           |
| `viagens_caminhao`      | Integer                                           |
| `efetivos_nomes`        | Text                                              |
| `status`                | Enum: AGENDADO / EM_ANDAMENTO / CONCLUIDO / CANCELADO |
| `observacoes`           | Text                                              |
| `data_finalizacao`      | Date (preenchida automaticamente ao concluir/cancelar) |
| `created_at`, `updated_at` | DateTime                                       |

`custo_total` e `lucro` são calculados na resposta da API (não armazenados), na mesma lógica do frontend.

## Endpoints

### `POST /api/servicos`
Cria um agendamento (nasce como `AGENDADO`).

```bash
curl -X POST http://localhost:8000/api/servicos \
  -H "Content-Type: application/json" \
  -d '{
    "nome_cliente": "QuintoAndar",
    "e_quinto_andar": true,
    "numero_contrato": "278354",
    "data": "2026-08-10",
    "horario": "09:00",
    "endereco": "Av. José Galante, 30 - Vila Suzana - São Paulo - SP",
    "valor_cobrado": 2400,
    "custo_operacional": 980,
    "quantidade_ajudantes": 3,
    "viagens_caminhao": 2,
    "custos_adicionais": [{"descricao": "Guincho", "valor": 250}]
  }'
```

### `GET /api/servicos`
Lista serviços. Filtros opcionais: `data_inicio`, `data_fim`, `status`, `cliente` (busca parcial),
`somente_quinto_andar`, `skip`, `limit`.

```bash
curl "http://localhost:8000/api/servicos?status=CONCLUIDO&somente_quinto_andar=true"
```

### `PATCH /api/servicos/{id}`
Atualização parcial — usada na **baixa do serviço** (efetivos, viagens, custo final, status) e também
serve para edição geral.

```bash
curl -X PATCH http://localhost:8000/api/servicos/<id> \
  -H "Content-Type: application/json" \
  -d '{
    "status": "CONCLUIDO",
    "efetivos_nomes": "Marcos Silva, João Pereira",
    "quantidade_ajudantes": 3,
    "viagens_caminhao": 2,
    "custo_operacional": 950
  }'
```

### `DELETE /api/servicos/{id}`
Exclui definitivamente um atendimento (sem confirmação — o frontend ainda não tem botão para isso).

```bash
curl -X DELETE http://localhost:8000/api/servicos/<id>
```

### `GET /api/servicos/{id}/whatsapp-link`
Retorna a mensagem formatada (apenas data/horário/endereço) e a URL pronta para `wa.me`.

```bash
curl http://localhost:8000/api/servicos/<id>/whatsapp-link
```

### `GET /api/relatorios/quinto-andar/exportar?mes=8&ano=2026`
Baixa o `.xlsx` com os serviços QuintoAndar **CONCLUIDOS** no mês/ano informado, no layout exigido pelo
contrato (Data, Endereço, Horário, Contrato, Custo, Obs.).

```bash
curl -OJ "http://localhost:8000/api/relatorios/quinto-andar/exportar?mes=8&ano=2026"
```

### `GET /api/relatorios/geral/exportar` (bônus — espelha a aba "Relatório Geral" do painel)
Parâmetros opcionais: `mes`, `ano` (se omitidos, todos os períodos), `tipo` (`Todos`/`QuintoAndar`/`Particular`),
`status`.

```bash
curl -OJ "http://localhost:8000/api/relatorios/geral/exportar?mes=8&ano=2026&tipo=QuintoAndar"
```

## Erros e CORS

- Erros de validação (`ValueError`, ex.: contrato QuintoAndar ausente) retornam `422` com `detail`.
- Erros de banco retornam `500` com mensagem genérica (sem vazar detalhes internos).
- Recursos não encontrados retornam `404`.
- CORS é controlado por `CORS_ORIGINS` no `.env` (lista separada por vírgula, ou `*` em dev).

## ⚠️ Persistência em produção (Render)

**SQLite (`sqlite:///./confianca.db`, o padrão quando `DATABASE_URL` não está definida) não persiste em
serviços web do Render.** O filesystem de um Web Service do Render é efêmero: a cada deploy, restart, ou
"cold start" depois do serviço hibernar por inatividade (plano free), o container volta para o estado da
imagem original — qualquer arquivo `.db` escrito em runtime é perdido. Foi exatamente isso que causou o
sumiço dos atendimentos: os dados eram gravados normalmente enquanto a instância ficava de pé, mas
desapareciam no primeiro restart/deploy/hibernação seguinte. Discos persistentes ("Disks") do Render
tampouco resolvem no plano free — exigem instância paga e só funcionam com 1 réplica.

**Correção: usar um banco PostgreSQL externo** (o código já suporta isso — só trocar `DATABASE_URL`, sem
mudar uma linha sequer de código). Passos:

1. Provisione um Postgres — qualquer uma das opções funciona com o código atual:
   - **Render Postgres** (New → PostgreSQL no dashboard do Render, tem plano free).
   - **Supabase** (Database → Connection string, no dashboard do projeto).
2. Copie a *connection string* (formato `postgresql://usuario:senha@host:porta/banco`) e ajuste o prefixo
   para `postgresql+psycopg2://...` (o driver usado pelo SQLAlchemy neste projeto).
3. No Web Service do backend, no Render: **Environment** → adicione/edite a variável `DATABASE_URL` com
   essa connection string → salve (isso já dispara um redeploy).
4. No primeiro boot com a nova `DATABASE_URL`, `Base.metadata.create_all()` (em `app/main.py`) cria a
   tabela `ordens_servico` automaticamente no Postgres — não precisa rodar migração manual.
5. Confirme que os dados sobrevivem a um restart manual do serviço no Render (Manual Deploy → redeploy).

`psycopg2-binary` (driver do Postgres) já está no `requirements.txt` — nenhuma mudança de código é
necessária além de configurar a variável de ambiente.

## Próximos passos sugeridos

- Trocar `Base.metadata.create_all` por **Alembic** quando o schema começar a evoluir com frequência.
- Adicionar autenticação (a API atualmente não tem controle de acesso).
