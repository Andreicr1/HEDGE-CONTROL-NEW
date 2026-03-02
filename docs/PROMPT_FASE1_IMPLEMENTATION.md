# Prompt: Implementação Fase 1 — Core Domain (P0)

> **Copie este prompt inteiro para uma nova sessão do Copilot Chat com memória livre.**

---

## PROMPT

Você é um engenheiro senior trabalhando no projeto **HEDGE-CONTROL-NEW** — um sistema de gestão de hedge de commodities metálicas (alumínio/cobre/zinco). O backend é FastAPI + SQLAlchemy + Pydantic v2, roda em Azure Container Apps.

### CONTEXTO DO PROJETO

**Stack:**

- Python 3.13, FastAPI 0.111, SQLAlchemy 2.0, Pydantic 2.7, Alembic 1.13
- Auth: JWT via Entra ID (JWKS), HMAC-SHA256 audit trail
- DB: PostgreSQL (prod), SQLite in-memory (testes)
- Testes: pytest + FastAPI TestClient, fixtures em `tests/conftest.py`
- Venv: `.venv/Scripts/python.exe` (Windows)

**Padrões arquiteturais obrigatórios (leia `docs/GAP_ANALYSIS_LEGACY_VS_NEW.md` para contexto completo):**

1. **UUID PKs** em todos os models — nunca Integer
2. **Pydantic v2 schemas** para request/response — nunca dict inline
3. **`Base` do SQLAlchemy** em `app/models/base.py` (DeclarativeBase simples)
4. **Soft delete** via `is_deleted` boolean + `deleted_at` timestamp
5. **Toda rota autenticada** via `Depends(get_current_user)` (override em testes)
6. **Testes com SQLite in-memory** — `conftest.py` faz `drop_all/create_all` entre testes
7. **Registrar models** em `app/models/__init__.py` para Alembic detectar
8. **Westmetall é a ÚNICA fonte de preços** — sem LME scraper, sem Yahoo Finance
9. **Deal + Exposure são os pilares do domínio** — base para P&L e decisões de hedge

**Estrutura atual dos arquivos backend:**

```
app/
  models/        → base.py, audit.py, cashflow.py, contracts.py, linkages.py,
                   market_data.py, mtm.py, orders.py, pl.py, quotes.py, rfqs.py
  schemas/       → audit.py, cashflow.py, contracts.py, exposure.py, linkages.py,
                   llm.py, market_data.py, mtm.py, orders.py, pl.py, rfq.py,
                   scenario.py, whatsapp.py
  services/      → 23 serviços (rfq_service, exposure_service, llm_agent, etc.)
  api/routes/    → audit, cashflow, cashflow_ledger, contracts, exposures,
                   linkages, mtm, orders, pl, rfqs, scenario, webhooks, westmetall
  core/          → auth.py, database.py, logging.py, metrics.py, pagination.py,
                   rate_limit.py, utils.py
tests/           → 35+ test files, conftest.py
```

**Models existentes (15):** `AuditEvent`, `CashFlowBaselineSnapshot`, `HedgeContractSettlementEvent`, `CashFlowLedgerEntry`, `HedgeContract`, `HedgeOrderLinkage`, `CashSettlementPrice`, `MTMSnapshot`, `Order`, `PLSnapshot`, `RFQQuote`, `RFQ`, `RFQInvitation`, `RFQStateEvent`, `RFQSequence`

**Enums existentes:** `HedgeClassification`, `HedgeContractStatus`, `HedgeLegSide`, `MTMObjectType`, `OrderType`, `OrderPricingConvention`, `PriceType`, `RFQDirection`, `RFQIntent`, `RFQState`, `RFQInvitationChannel`, `RFQInvitationStatus`

---

### TAREFA: IMPLEMENTAR FASE 1 — CORE DOMAIN (P0)

Implemente os 6 componentes do roadmap Fase 1, na ordem exata. Cada componente inclui: **model + schema + service + route + testes**. Após cada componente, rode os testes para validar.

#### 1.1 — Counterparty Model + CRUD (~300 linhas)

Criar model `Counterparty` unificando Customer/Supplier/Counterparty do legacy:

**Model (`app/models/counterparty.py`):**

```python
# Campos obrigatórios:
- id: UUID PK (server_default uuid4)
- type: Enum("customer", "supplier", "broker") — não nullable
- name: String(200) — não nullable
- short_name: String(50) — nullable
- tax_id: String(50) — nullable, unique
- country: String(3) — ISO 3166-1 alpha-3
- city: String(100) — nullable
- address: Text — nullable
- contact_name: String(200) — nullable
- contact_email: String(200) — nullable
- contact_phone: String(50) — nullable
- payment_terms_days: Integer — default 30
- credit_limit_usd: Numeric(15,2) — nullable
- kyc_status: Enum("pending", "approved", "expired", "rejected") — default "pending"
- sanctions_status: Enum("clear", "flagged", "blocked") — default "clear"
- risk_rating: Enum("low", "medium", "high") — default "medium"
- is_active: Boolean — default True
- notes: Text — nullable
- created_at: DateTime — server_default utcnow
- updated_at: DateTime — onupdate utcnow
- is_deleted: Boolean — default False
- deleted_at: DateTime — nullable
```

**Schema:** Create, Update (partial), Response, List com paginação
**Route:** GET (list com filtros type/kyc_status/is_active), GET /{id}, POST, PATCH /{id}, DELETE /{id} (soft delete)
**Service:** CRUD simples com soft delete filter
**Testes:** CRUD completo, filtros, soft delete, validação de duplicata tax_id

#### 1.2 — Ampliar Order Model (~200 linhas)

Enriquecer o `Order` existente com campos do legacy SO/PO:

**Campos novos no model `Order`:**

```python
- counterparty_id: UUID FK → counterparties.id — nullable (migração gradual)
- pricing_type: Enum("fixed", "average", "avginter", "fix", "c2r") — nullable
- delivery_terms: String(50) — nullable (ex: "CIF Rotterdam")
- delivery_date_start: Date — nullable
- delivery_date_end: Date — nullable
- payment_terms_days: Integer — nullable
- currency: String(3) — default "USD"
- notes: Text — nullable
```

**Novo model `SoPoLink` (`app/models/orders.py`):**

```python
- id: UUID PK
- sales_order_id: UUID FK → orders.id — não nullable
- purchase_order_id: UUID FK → orders.id — não nullable
- linked_tons: Numeric(15,3) — não nullable
- created_at: DateTime
- UniqueConstraint(sales_order_id, purchase_order_id)
```

**Route nova:** POST `/orders/links` (criar link SO↔PO), GET `/orders/links` (listar)
**Testes:** Criar SO, criar PO, linkar, validar que SO e PO existem e têm tipos corretos

#### 1.3 — Exposure Engine (~600 linhas)

Motor de exposição com persistência e reconciliação automática.

**Model `Exposure` (`app/models/exposure.py`):**

```python
- id: UUID PK
- commodity: String(20) — não nullable (ex: "ALUMINUM", "COPPER")
- direction: Enum("long", "short") — long=compra, short=venda
- source_type: Enum("sales_order", "purchase_order") — origem
- source_id: UUID — FK polimórfico para o order
- original_tons: Numeric(15,3) — toneladas originais
- open_tons: Numeric(15,3) — toneladas ainda não hedgeadas
- price_per_ton: Numeric(15,2) — nullable
- settlement_month: String(7) — formato "2026-03"
- status: Enum("open", "partially_hedged", "fully_hedged", "cancelled")
- created_at, updated_at, is_deleted, deleted_at
```

**Model `ContractExposure`:**

```python
- id: UUID PK
- exposure_id: UUID FK → exposures.id
- contract_id: UUID FK → hedge_contracts.id
- allocated_tons: Numeric(15,3)
- created_at
```

**Model `HedgeExposure`:**

```python
- id: UUID PK
- exposure_id: UUID FK → exposures.id
- hedge_id: UUID FK → hedges.id (criado no passo 1.4)
- allocated_tons: Numeric(15,3)
- created_at
```

**Model `HedgeTask`:**

```python
- id: UUID PK
- exposure_id: UUID FK → exposures.id
- recommended_tons: Numeric(15,3)
- recommended_action: Enum("hedge_new", "increase", "decrease", "cancel")
- status: Enum("pending", "executed", "cancelled")
- created_at, executed_at
```

**Service `exposure_engine.py`:**

- `reconcile_from_orders(session)` → Varre todas as Orders ativas, cria/atualiza Exposures
- `compute_net_exposure(session, commodity)` → Retorna net (long - short) por commodity
- `create_hedge_tasks(session)` → Para exposições abertas, cria HedgeTasks pendentes
- `cancel_stale_tasks(session)` → Cancela tasks de exposições que foram hedgeadas

**Routes:**

- GET `/exposures` — listar exposições com filtros (commodity, status, settlement_month)
- GET `/exposures/{id}` — detalhe com contract_exposures e hedge_exposures
- POST `/exposures/reconcile` — trigger de reconciliação
- GET `/exposures/net` — net exposure por commodity
- GET `/exposures/tasks` — hedge tasks pendentes
- POST `/exposures/tasks/{id}/execute` — marcar task como executada

**Testes (mínimo 10):** Reconciliação cria exposures a partir de orders, net exposure calculation, hedge tasks creation, idempotência de reconciliação, filtros

#### 1.4 — Hedge Model + CRUD + Lifecycle (~500 linhas)

**Model `Hedge` (`app/models/hedge.py`):**

```python
- id: UUID PK
- reference: String(50) — único, gerado automaticamente
- counterparty_id: UUID FK → counterparties.id
- commodity: String(20)
- direction: Enum("buy", "sell")
- tons: Numeric(15,3)
- price_per_ton: Numeric(15,2)
- premium_discount: Numeric(15,2) — default 0
- settlement_date: Date
- prompt_date: Date — nullable (LME prompt date)
- trade_date: Date — default today
- status: Enum("active", "partially_settled", "settled", "cancelled")
- source_type: Enum("rfq_award", "manual", "auto") — como foi criado
- source_id: UUID — nullable, FK para RFQ ou HedgeTask
- contract_id: UUID FK → hedge_contracts.id — nullable
- notes: Text
- created_by: String(200) — user que criou
- created_at, updated_at, is_deleted, deleted_at
```

**Service `hedge_service.py`:**

- `create_hedge(session, data)` → Cria hedge, vincula HedgeExposure se exposure_id fornecido
- `create_from_rfq_award(session, rfq_id)` → Cria hedge a partir de RFQ awarded
- `list_hedges(session, filters)` → Com paginação e filtros
- `update_status(session, hedge_id, new_status)` → Transição de status validada
- `cancel_hedge(session, hedge_id)` → Soft delete + libera exposure tons

**Routes:**

- GET `/hedges` — listar com filtros (commodity, status, counterparty, date range)
- GET `/hedges/{id}` — detalhe com exposures vinculadas
- POST `/hedges` — criar manualmente
- POST `/hedges/from-rfq/{rfq_id}` — criar a partir de award
- PATCH `/hedges/{id}` — atualizar
- PATCH `/hedges/{id}/status` — transição de status
- DELETE `/hedges/{id}` — soft delete + cancel

**Testes (mínimo 8):** CRUD, status transitions válidas/inválidas, criação a partir de RFQ, vínculo com exposure, cancelamento libera tons

#### 1.5 — Deal Engine (~400 linhas)

**Model `Deal` (`app/models/deal.py`):**

```python
- id: UUID PK
- reference: String(50) — único
- name: String(200)
- commodity: String(20)
- status: Enum("open", "partially_hedged", "fully_hedged", "settled", "closed")
- total_physical_tons: Numeric(15,3) — computed
- total_hedge_tons: Numeric(15,3) — computed
- hedge_ratio: Numeric(5,2) — computed (hedge_tons / physical_tons)
- created_at, updated_at, is_deleted, deleted_at
```

**Model `DealLink`:**

```python
- id: UUID PK
- deal_id: UUID FK → deals.id
- linked_type: Enum("sales_order", "purchase_order", "hedge", "contract")
- linked_id: UUID — FK polimórfico
- created_at
- UniqueConstraint(deal_id, linked_type, linked_id)
```

**Model `DealPNLSnapshot`:**

```python
- id: UUID PK
- deal_id: UUID FK → deals.id
- snapshot_date: Date
- physical_revenue: Numeric(15,2) — default 0
- physical_cost: Numeric(15,2) — default 0
- hedge_pnl_realized: Numeric(15,2) — default 0
- hedge_pnl_mtm: Numeric(15,2) — default 0
- total_pnl: Numeric(15,2) — computed (revenue - cost + realized + mtm)
- inputs_hash: String(64) — SHA256 para idempotência
- created_at
```

**Service `deal_engine.py`:**

- `create_deal(session, data)` → Cria deal com links iniciais
- `add_link(session, deal_id, linked_type, linked_id)` → Adiciona link
- `remove_link(session, deal_id, link_id)` → Remove link
- `compute_deal_pnl(session, deal_id, snapshot_date)` → Calcula P&L consolidado e cria snapshot
- `update_deal_status(session, deal_id)` → Atualiza status baseado em hedge_ratio
- `list_deals(session, filters)` → Com paginação

**Routes:**

- GET `/deals` — listar
- GET `/deals/{id}` — detalhe com links e último P&L snapshot
- POST `/deals` — criar
- POST `/deals/{id}/links` — adicionar link
- DELETE `/deals/{id}/links/{link_id}` — remover link
- POST `/deals/{id}/pnl-snapshot` — trigger P&L snapshot
- GET `/deals/{id}/pnl-history` — histórico de P&L snapshots

**Testes (mínimo 8):** Criar deal, adicionar/remover links, P&L snapshot, idempotência (inputs_hash), status transitions baseadas em hedge_ratio

#### 1.6 — Finance Pipeline Daily (~500 linhas)

**Model `FinancePipelineRun` (`app/models/finance_pipeline.py`):**

```python
- id: UUID PK
- run_date: Date — não nullable
- status: Enum("running", "completed", "failed", "partial")
- started_at: DateTime
- finished_at: DateTime — nullable
- steps_completed: Integer — default 0
- steps_total: Integer — default 6
- error_message: Text — nullable
- inputs_hash: String(64) — idempotência por (run_date)
- created_at
```

**Model `FinancePipelineStep`:**

```python
- id: UUID PK
- run_id: UUID FK → finance_pipeline_runs.id
- step_number: Integer (1-6)
- step_name: String(50) — ex: "market_snapshot", "mtm_computation"
- status: Enum("pending", "running", "completed", "failed", "skipped")
- started_at: DateTime — nullable
- finished_at: DateTime — nullable
- records_processed: Integer — default 0
- error_message: Text — nullable
```

**Service `finance_pipeline_service.py`:**

- `run_daily_pipeline(session, run_date)` → Executa 6 etapas em sequência:
  1. **Market Snapshot** — Busca últimos preços do Westmetall (`CashSettlementPrice`)
  2. **MTM Computation** — Chama `mtm_contract_service` para todos os contratos ativos
  3. **P&L Snapshot** — Chama `pl_calculation_service` para gerar snapshots
  4. **Cashflow Baseline** — Chama `cashflow_baseline_service`
  5. **Risk Flags** — Identifica dados faltantes/inconsistentes (stub por agora)
  6. **Summary** — Conta registros processados
- Cada etapa é idempotente. Se o pipeline falha, pode ser re-executado.
- Pipeline é resumível — pula etapas já completadas.

**Routes:**

- POST `/finance/pipeline/run` — trigger pipeline para uma data
- GET `/finance/pipeline/runs` — listar execuções
- GET `/finance/pipeline/runs/{id}` — detalhe com steps

**Testes (mínimo 6):** Pipeline completo (happy path), idempotência, falha em uma etapa (parcial), re-execução, listagem de runs

---

### REGRAS DE IMPLEMENTAÇÃO

1. **Ordem estrita:** 1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6 (há dependências)
2. **Registrar cada model novo** em `app/models/__init__.py`
3. **Criar arquivo de rota** e registrar em `app/main.py` com `app.include_router()`
4. **Rodar testes** após cada componente: `cd backend && python -m pytest tests/ -x -q`
5. **Não quebrar testes existentes** — os 35+ testes atuais devem continuar passando
6. **Gerar migration Alembic** após todos os models criados: `cd backend && alembic revision --autogenerate -m "fase1_core_domain"`
7. **Seguir o padrão de testes do conftest.py existente** — use fixture `client` e `session`
8. **Cada rota usa `Depends(get_current_user)`** para autenticação

### VALIDAÇÃO FINAL

Após implementar todos os 6 componentes:

```bash
cd backend && python -m pytest tests/ -x -q
```

Todos os testes (existentes + novos) devem passar. Reporte o resultado final e a contagem de testes.
