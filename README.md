# Confiança Depósito e Armazenamento — Painel de Operações

Sistema de gestão para a Confiança Depósito e Armazenamento (serviço de depósito judiciário):
agendamento e baixa de atendimentos, controle de custo/lucro por serviço, envio de ordem de
serviço pro WhatsApp da equipe de campo, e relatório mensal em `.xlsx` para o cliente QuintoAndar.

## Estrutura do repositório

```
.
├── confianca-ops-app_3.html   # Frontend — painel de operações (HTML/JS/Tailwind, sem build)
├── logo_confiança.jpg         # Logo usada no cabeçalho do painel
└── backend/                   # API FastAPI + persistência (SQLite em dev)
    ├── app/                   # Código da API (models, schemas, rotas, exportação de Excel)
    ├── requirements.txt
    ├── .env.example
    └── README.md              # Detalhes da API: endpoints, schema do banco, exemplos de curl
```

## Como rodar

**1. Backend** (veja detalhes em [`backend/README.md`](backend/README.md)):

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env

uvicorn app.main:app --reload --reload-dir app --port 8000
```

A API sobe em `http://localhost:8000` (docs interativas em `/docs`) e cria o banco SQLite
(`backend/confianca.db`) automaticamente no primeiro start.

**2. Frontend**: abra `confianca-ops-app_3.html` direto no navegador (ou sirva a pasta com
qualquer servidor estático). Ele busca os dados em `http://localhost:8000` por padrão — para
apontar para outro host, defina `window.CONFIANCA_API_BASE_URL` antes do script no HTML.

## Principais funcionalidades

- Cadastro, edição e baixa de atendimentos (QuintoAndar ou cliente particular), com custos
  adicionais (guincho, munck etc.) e cálculo automático de custo total e lucro.
- Envio da ordem de serviço formatada pro WhatsApp da equipe (`wa.me`).
- Relatório mensal QuintoAndar e relatório geral, exportados em `.xlsx` pelo backend
  (colunas, formatação de data/hora/moeda e cabeçalho estilizado).
- Interface mobile-first: navegação inferior, cards no lugar de tabelas e alvos de toque
  grandes no celular.

## Stack

Frontend: HTML + Tailwind (CDN) + JavaScript puro, sem build.
Backend: FastAPI, SQLAlchemy, SQLite (dev) — troca simples para PostgreSQL/Supabase em produção
via `DATABASE_URL` — e openpyxl para os relatórios.
