# Gerenciador de Finanças Pessoais — Backend

API REST para gerenciamento de finanças pessoais, construída com Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL 16 e autenticação JWT. Sem frontend — apenas JSON.

## Tecnologias

- Python 3.12
- FastAPI
- SQLAlchemy 2.0 (estilo moderno com `Mapped`/`mapped_column`)
- Alembic (migrações)
- PostgreSQL 16
- Pydantic v2 e pydantic-settings
- PyJWT + bcrypt (hash de senha direto)
- pytest, httpx, pytest-cov (testes)
- ruff (lint e formatação)
- Docker e Docker Compose
- GitHub Actions (CI)

## Funcionalidades

- Cadastro, login e consulta do usuário autenticado (`/api/v1/users/me`)
- CRUD de contas (com saldo calculado)
- CRUD de categorias (INCOME / EXPENSE, filtro por tipo)
- CRUD de transações (filtros, paginação, ordenação)
- CRUD de orçamentos mensais por categoria (apenas EXPENSE)
- Status do orçamento (OK, WARNING, EXCEEDED)
- Relatórios: resumo mensal, por categoria e evolução mensal
- Isolamento de dados por usuário (404 para recursos de outro usuário)
- `/health` sem autenticação

## Como rodar com Docker

```bash
docker compose up --build
```

A API ficará disponível em `http://localhost:8000` com documentação em `/docs`.

O container `api` executa `alembic upgrade head` antes de iniciar o servidor (uvicorn).

## Como rodar sem Docker

1. Instale as dependências:

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
```

2. Copie o `.env.example` para `.env` e ajuste as variáveis:

```bash
cp .env.example .env
```

3. Crie um banco PostgreSQL chamado `financas` (ou ajuste a `DATABASE_URL`).

4. Rode as migrações:

```bash
alembic upgrade head
```

5. Inicie o servidor:

```bash
uvicorn app.main:app --reload
```

## Como rodar os testes

Os testes usam um banco PostgreSQL separado (`financas_test`).

```bash
pytest --cov=app --cov-report=term-missing
```

Cobertura mínima exigida: 80%.

## Resumo dos endpoints

Todas as rotas (exceto `/health`, `/api/v1/auth/register`, `/api/v1/auth/login`) exigem Bearer token.

### Infra
- `GET /health` → `{"status": "ok"}`

### Autenticação
- `POST /api/v1/auth/register` — cadastra usuário (201). E-mail duplicado: 409.
- `POST /api/v1/auth/login` — login via OAuth2 form-data (`username`=e-mail, `password`). Retorna `access_token` (201). Credenciais inválidas: 401.
- `GET /api/v1/users/me` — dados do usuário autenticado.

### Contas
- `POST /api/v1/accounts`
- `GET /api/v1/accounts` — lista com `balance` calculado
- `GET /api/v1/accounts/{id}` — inclui `balance`
- `PATCH /api/v1/accounts/{id}` — altera nome e/ou saldo inicial
- `DELETE /api/v1/accounts/{id}` — 409 se houver transações

### Categorias
- `POST /api/v1/categories`
- `GET /api/v1/categories?type=INCOME|EXPENSE`
- `GET /api/v1/categories/{id}`
- `PATCH /api/v1/categories/{id}` — altera somente nome
- `DELETE /api/v1/categories/{id}` — 409 se houver transações

### Transações
- `POST /api/v1/transactions`
- `GET /api/v1/transactions` — filtros, paginação, `total`
- `GET /api/v1/transactions/{id}`
- `PATCH /api/v1/transactions/{id}`
- `DELETE /api/v1/transactions/{id}`

### Orçamentos
- `POST /api/v1/budgets` — apenas categoria EXPENSE
- `GET /api/v1/budgets?year=&month=`
- `PATCH /api/v1/budgets/{id}` — altera somente `limit_amount`
- `DELETE /api/v1/budgets/{id}`
- `GET /api/v1/budgets/status?year=&month=` — OK / WARNING / EXCEEDED

### Relatórios
- `GET /api/v1/reports/monthly-summary?year=&month=`
- `GET /api/v1/reports/by-category?year=&month=&type=`
- `GET /api/v1/reports/monthly-evolution?months=`

## Exemplo de fluxo de uso

1. Cadastrar:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"usuario@exemplo.com","password":"senha123","full_name":"Usuário Exemplo"}'
```

2. Logar:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=usuario@exemplo.com&password=senha123"
```

3. Criar conta (usando o token):

```bash
curl -X POST http://localhost:8000/api/v1/accounts \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Carteira","initial_balance":"1000.00"}'
```

4. Criar categoria:

```bash
curl -X POST http://localhost:8000/api/v1/categories \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Salário","type":"INCOME"}'
```

5. Criar transação:

```bash
curl -X POST http://localhost:8000/api/v1/transactions \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"account_id":1,"category_id":1,"type":"INCOME","amount":"500.00","date":"2026-01-10","description":"Pagamento"}'
```

6. Ver relatório mensal:

```bash
curl "http://localhost:8000/api/v1/reports/monthly-summary?year=2026&month=1" \
  -H "Authorization: Bearer <TOKEN>"
```

## Decisões de projeto

- **Money**: valores monetários usam `Decimal` no Python e `Numeric(12, 2)` no banco. Na resposta JSON, são strings com duas casas decimais (ex.: `"1250.50"`). Nunca `float`.
- **amount**: sempre positivo (> 0). Entrada/saída é definida pelo campo `type`.
- **Datas**: `date` é `date` (AAAA-MM-DD), sem horário. `created_at`/`updated_at` são timestamp com timezone em UTC.
- **Identificadores**: inteiros autoincrementais.
- **Nomes em inglês**: código, variáveis, tabelas e campos JSON. Comentários, docstrings, README e mensagens de erro em português do Brasil.
- **Prefixo**: todas as rotas sob `/api/v1`, exceto `/health`, `/auth/register`, `/auth/login`.
- **Erros**: formato único `{"detail": "mensagem em português"}`. Pydantic 422 segue o padrão do FastAPI.
- **Recurso inexistente ou de outro usuário**: 404 (nunca revela que existe).
- **Saldo da conta**: não é armazenado. Calculado como `initial_balance + soma(INCOME) − soma(EXPENSE)`.
- **Exclusão**: não é permitido excluir conta ou categoria com transações (409). Excluir categoria sem transações também exclui seus orçamentos.
- **Ambiente local**: Python 3.14/Windows não compila pacotes com extensões Rust (pydantic-core, psycopg2-binary). A entrega é validada via Docker (Python 3.12/linux).

## Checklist de conformidade

- [x] Backend apenas (REST + JSON, sem frontend)
- [x] Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL 16
- [x] Pydantic v2 + pydantic-settings
- [x] JWT (PyJWT) + bcrypt direto
- [x] Testes pytest, httpx, pytest-cov (≥80%)
- [x] ruff lint + format
- [x] Docker + Docker Compose
- [x] GitHub Actions CI
- [x] requirements.txt e requirements-dev.txt com versões fixas
- [x] Decimal / Numeric(12,2), strings com 2 casas no JSON
- [x] amount sempre > 0, type define entrada/saída
- [x] date sem horário, timestamps UTC
- [x] IDs inteiros autoincrementais
- [x] Nomes em inglês, mensagens em português
- [x] Prefixo /api/v1
- [x] Rotas públicas: /health, register, login
- [x] 404 para recurso inexistente ou de outro usuário
- [x] Formato de erro {"detail": "..."}
- [x] Códigos HTTP: 200, 201, 204, 401, 404, 409, 422
- [x] Tabela users com email único (lowercase), full_name 1-100
- [x] Tabela accounts com nome único por usuário (case-insensitive)
- [x] Tabela categories com (user_id, name, type) único, type imutável
- [x] Tabela transactions com validação type == categoria.type
- [x] Tabela budgets com (user_id, category_id, year, month) único, apenas EXPENSE
- [x] Saldo calculado, não armazenado
- [x] Bloqueio 409 exclusão de conta/categoria com transações
- [x] Endpoints de relatório prontos em JSON
- [x] README em português com seção Decisões de projeto
