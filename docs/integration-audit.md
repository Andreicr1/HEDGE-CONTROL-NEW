# Auditoria de Integração Backend (FastAPI) ↔ Frontend (SAPUI5)

> Gerado em: 2025-03-02
> Base: evidência de código — nenhuma suposição implícita.
>
> **⚠ ATENÇÃO:** Este documento foi gerado quando o backend possuía 42 endpoints.
> O backend atual possui **75 endpoints de API** (79 incluindo docs auto-gerados).
> Para o inventário atualizado, consulte → [AUDIT_CROSS_REFERENCE.md](../AUDIT_CROSS_REFERENCE.md).

---

## Índice

1. [Resumo Executivo](#resumo-executivo)
2. [Inventário Completo — Endpoints × Consumo](#inventário-completo--endpoints--consumo)
3. [Endpoints Backend SEM Consumo no Frontend](#endpoints-backend-sem-consumo-no-frontend)
4. [Divergências Frontend ↔ Backend](#divergências-frontend--backend)
   - [C.1 — Endpoints fantasma (404 em runtime)](#c1--endpoints-fantasma-404-em-runtime)
   - [C.2 — apiClient.js não suporta PATCH/PUT/DELETE](#c2--apiclientjs-não-suporta-patchputdelete)
   - [C.3 — Ausência de autenticação no frontend](#c3--ausência-de-autenticação-no-frontend)
   - [C.4 — manifest.json declara /api/v1/ sem correspondência no backend](#c4--manifestjson-declara-apiv1-sem-correspondência-no-backend)
   - [C.5 — Endpoints de listagem sem consumo](#c5--endpoints-de-listagem-sem-consumo)
5. [Estatísticas](#estatísticas)
6. [Arquitetura do apiClient.js](#arquitetura-do-apiclientjs)
7. [Mapa de Service Files do Frontend](#mapa-de-service-files-do-frontend)

---

## Resumo Executivo

| Métrica                                   | Valor |
| ----------------------------------------- | ----- |
| Total endpoints backend                   | 42    |
| Consumidos pelo frontend                  | 30    |
| Não consumidos (exceto webhook)           | 10    |
| Não aplicáveis (webhook Meta)             | 2     |
| Endpoints fantasma no frontend (→ 404)    | 3     |
| Endpoints inalcançáveis (sem PATCH na UI) | 3     |
| Endpoints protegidos sem auth no frontend | 35    |

---

## Inventário Completo — Endpoints × Consumo

### Infraestrutura

| #   | Método | Rota       | Handler     | Auth | Status       | Evidência                                            |
| --- | ------ | ---------- | ----------- | ---- | ------------ | ---------------------------------------------------- |
| 1   | GET    | `/health`  | `health`    | —    | ✅ Consumido | `observabilityService.js` → `getHealth()`            |
| 2   | GET    | `/ready`   | `readiness` | —    | ✅ Consumido | `observabilityService.js` → `getReady()`             |
| 3   | GET    | `/metrics` | prometheus  | —    | ✅ Consumido | `observabilityService.js` → `getMetrics()` (getText) |

### Orders (`/orders`)

| #   | Método | Rota                         | Handler                 | Auth                     | Status           | Evidência                                     |
| --- | ------ | ---------------------------- | ----------------------- | ------------------------ | ---------------- | --------------------------------------------- |
| 4   | POST   | `/orders/sales`              | `create_sales_order`    | `require_role("trader")` | ✅ Consumido     | `ordersService.js` → `createSales()`          |
| 5   | POST   | `/orders/purchase`           | `create_purchase_order` | `require_role("trader")` | ✅ Consumido     | `ordersService.js` → `createPurchase()`       |
| 6   | GET    | `/orders`                    | `list_orders`           | `require_any_role(...)`  | ❌ Não consumido | Nenhuma função `list()` em `ordersService.js` |
| 7   | GET    | `/orders/{order_id}`         | `get_order`             | —                        | ✅ Consumido     | `ordersService.js` → `getById()`              |
| 8   | PATCH  | `/orders/{order_id}/archive` | `archive_order`         | `require_role("trader")` | ❌ Inalcançável  | `apiClient.js` não expõe PATCH                |

### Exposures (`/exposures`)

| #   | Método | Rota                    | Handler                   | Auth                    | Status       | Evidência                                 |
| --- | ------ | ----------------------- | ------------------------- | ----------------------- | ------------ | ----------------------------------------- |
| 9   | GET    | `/exposures/commercial` | `get_commercial_exposure` | `require_any_role(...)` | ✅ Consumido | `exposuresService.js` → `getCommercial()` |
| 10  | GET    | `/exposures/global`     | `get_global_exposure`     | `require_any_role(...)` | ✅ Consumido | `exposuresService.js` → `getGlobal()`     |

### Contracts (`/contracts`)

| #   | Método | Rota                                     | Handler                  | Auth                     | Status           | Evidência                                        |
| --- | ------ | ---------------------------------------- | ------------------------ | ------------------------ | ---------------- | ------------------------------------------------ |
| 11  | POST   | `/contracts/hedge`                       | `create_hedge_contract`  | `require_role("trader")` | ✅ Consumido     | `contractsService.js` → `createHedge()`          |
| 12  | GET    | `/contracts/hedge`                       | `list_hedge_contracts`   | `require_any_role(...)`  | ❌ Não consumido | Nenhuma função `list()` em `contractsService.js` |
| 13  | GET    | `/contracts/hedge/{contract_id}`         | `get_hedge_contract`     | —                        | ✅ Consumido     | `contractsService.js` → `getHedgeById()`         |
| 14  | PATCH  | `/contracts/hedge/{contract_id}/archive` | `archive_hedge_contract` | `require_role("trader")` | ❌ Inalcançável  | `apiClient.js` não expõe PATCH                   |

### Linkages (`/linkages`)

| #   | Método | Rota                     | Handler          | Auth                     | Status           | Evidência                                       |
| --- | ------ | ------------------------ | ---------------- | ------------------------ | ---------------- | ----------------------------------------------- |
| 15  | GET    | `/linkages`              | `list_linkages`  | `require_any_role(...)`  | ❌ Não consumido | Nenhuma função `list()` em `linkagesService.js` |
| 16  | POST   | `/linkages`              | `create_linkage` | `require_role("trader")` | ✅ Consumido     | `linkagesService.js` → `create()`               |
| 17  | GET    | `/linkages/{linkage_id}` | `get_linkage`    | —                        | ✅ Consumido     | `linkagesService.js` → `getById()`              |

### RFQs (`/rfqs`)

| #   | Método | Rota                             | Handler              | Auth                     | Status           | Evidência                                        |
| --- | ------ | -------------------------------- | -------------------- | ------------------------ | ---------------- | ------------------------------------------------ |
| 18  | GET    | `/rfqs`                          | `list_rfqs`          | `require_any_role(...)`  | ❌ Não consumido | Nenhuma função `list()` em `rfqService.js`       |
| 19  | POST   | `/rfqs`                          | `create_rfq`         | `require_role("trader")` | ✅ Consumido     | `rfqService.js` → `create()`                     |
| 20  | GET    | `/rfqs/{rfq_id}`                 | `get_rfq`            | —                        | ✅ Consumido     | `rfqService.js` → `getById()`                    |
| 21  | GET    | `/rfqs/{rfq_id}/quotes`          | `list_rfq_quotes`    | `require_any_role(...)`  | ❌ Não consumido | Nenhuma função `listQuotes()` em `rfqService.js` |
| 22  | POST   | `/rfqs/{rfq_id}/quotes`          | `create_quote`       | `require_role("trader")` | ✅ Consumido     | `rfqService.js` → `createQuote()`                |
| 23  | GET    | `/rfqs/{rfq_id}/trade-ranking`   | `get_trade_ranking`  | —                        | ✅ Consumido     | `rfqService.js` → `getTradeRanking()`            |
| 24  | GET    | `/rfqs/{rfq_id}/ranking`         | `get_spread_ranking` | —                        | ✅ Consumido     | `rfqService.js` → `getRanking()`                 |
| 25  | POST   | `/rfqs/{rfq_id}/actions/reject`  | `reject_rfq`         | `require_role("trader")` | ✅ Consumido     | `rfqService.js` → `reject()`                     |
| 26  | POST   | `/rfqs/{rfq_id}/actions/refresh` | `refresh_rfq`        | `require_role("trader")` | ✅ Consumido     | `rfqService.js` → `refresh()`                    |
| 27  | POST   | `/rfqs/{rfq_id}/actions/award`   | `award_rfq`          | `require_role("trader")` | ✅ Consumido     | `rfqService.js` → `award()`                      |
| 28  | PATCH  | `/rfqs/{rfq_id}/archive`         | `archive_rfq`        | `require_role("trader")` | ❌ Inalcançável  | `apiClient.js` não expõe PATCH                   |

### CashFlow (`/cashflow`)

| #   | Método | Rota                                             | Handler                            | Auth                     | Status       | Evidência                                          |
| --- | ------ | ------------------------------------------------ | ---------------------------------- | ------------------------ | ------------ | -------------------------------------------------- |
| 29  | GET    | `/cashflow/analytic`                             | `get_cashflow_analytic`            | `require_any_role(...)`  | ✅ Consumido | `cashflowAnalyticService.js` → `get()`             |
| 30  | POST   | `/cashflow/baseline/snapshots`                   | `create_baseline_snapshot`         | `require_role("trader")` | ✅ Consumido | `cashflowBaselineSnapshotsService.js` → `create()` |
| 31  | GET    | `/cashflow/baseline/snapshots`                   | `get_baseline_snapshot`            | `require_any_role(...)`  | ✅ Consumido | `cashflowBaselineSnapshotsService.js` → `get()`    |
| 32  | POST   | `/cashflow/contracts/{contract_id}/settle`       | `settle_hedge_contract`            | `require_role("trader")` | ✅ Consumido | `cashflowLedgerService.js` → `settleContract()`    |
| 33  | GET    | `/cashflow/ledger`                               | `list_ledger_entries_by_event`     | —                        | ✅ Consumido | `cashflowLedgerService.js` → `listByEvent()`       |
| 34  | GET    | `/cashflow/ledger/hedge-contracts/{contract_id}` | `list_ledger_entries_for_contract` | —                        | ✅ Consumido | `cashflowLedgerService.js` → `listForContract()`   |

### P&L (`/pl`)

| #   | Método | Rota                            | Handler            | Auth                     | Status       | Evidência                           |
| --- | ------ | ------------------------------- | ------------------ | ------------------------ | ------------ | ----------------------------------- |
| 35  | GET    | `/pl/{entity_type}/{entity_id}` | `get_pl`           | `require_any_role(...)`  | ✅ Consumido | `plService.js` → `getPl()`          |
| 36  | POST   | `/pl/snapshots`                 | `post_pl_snapshot` | `require_role("trader")` | ✅ Consumido | `plService.js` → `createSnapshot()` |
| 37  | GET    | `/pl/snapshots`                 | `get_pl_snapshot`  | `require_any_role(...)`  | ✅ Consumido | `plService.js` → `getSnapshot()`    |

### Scenario (`/scenario`)

| #   | Método | Rota                    | Handler                | Auth                    | Status       | Evidência                            |
| --- | ------ | ----------------------- | ---------------------- | ----------------------- | ------------ | ------------------------------------ |
| 38  | POST   | `/scenario/what-if/run` | `run_what_if_scenario` | `require_any_role(...)` | ✅ Consumido | `scenarioService.js` → `runWhatIf()` |

### Audit (`/audit`)

| #   | Método | Rota                              | Handler              | Auth                      | Status           | Evidência                                      |
| --- | ------ | --------------------------------- | -------------------- | ------------------------- | ---------------- | ---------------------------------------------- |
| 39  | GET    | `/audit/events`                   | `list_audit_events`  | `require_role("auditor")` | ✅ Consumido     | `auditService.js` → `getAuditEvents()`         |
| 40  | GET    | `/audit/events/{event_id}/verify` | `verify_audit_event` | `require_role("auditor")` | ❌ Não consumido | Nenhuma função `verify()` em `auditService.js` |

### Market Data (`/market-data`)

| #   | Método | Rota                                                      | Handler                        | Auth | Status       | Evidência                                        |
| --- | ------ | --------------------------------------------------------- | ------------------------------ | ---- | ------------ | ------------------------------------------------ |
| 41  | POST   | `/market-data/westmetall/aluminum/cash-settlement/ingest` | `ingest_cash_settlement_daily` | —    | ✅ Consumido | `marketDataService.js` → `ingestWestmetall...()` |

### MTM (`/mtm`)

| #   | Método | Rota                                 | Handler                      | Auth                     | Status           | Evidência                                      |
| --- | ------ | ------------------------------------ | ---------------------------- | ------------------------ | ---------------- | ---------------------------------------------- |
| 42  | GET    | `/mtm/hedge-contracts/{contract_id}` | `get_mtm_for_hedge_contract` | `require_any_role(...)`  | ✅ Consumido     | `mtmService.js` → `getForHedgeContract()`      |
| 43  | GET    | `/mtm/orders/{order_id}`             | `get_mtm_for_order`          | `require_any_role(...)`  | ✅ Consumido     | `mtmService.js` → `getForOrder()`              |
| 44  | POST   | `/mtm/snapshots`                     | `create_mtm_snapshot`        | `require_role("trader")` | ❌ Não consumido | `mtmService.js` só expõe `getSnapshot()` (GET) |
| 45  | GET    | `/mtm/snapshots`                     | `get_mtm_snapshot`           | `require_any_role(...)`  | ✅ Consumido     | `mtmService.js` → `getSnapshot()`              |

### Webhooks (`/webhooks`)

| #   | Método | Rota                 | Handler           | Auth | Status | Evidência                              |
| --- | ------ | -------------------- | ----------------- | ---- | ------ | -------------------------------------- |
| 46  | GET    | `/webhooks/whatsapp` | `verify_webhook`  | —    | ❌ N/A | Callback Meta — não é endpoint para UI |
| 47  | POST   | `/webhooks/whatsapp` | `receive_webhook` | —    | ❌ N/A | Callback Meta — não é endpoint para UI |

---

## Endpoints Backend SEM Consumo no Frontend

| #   | Método | Rota                                     | Motivo                                                                      |
| --- | ------ | ---------------------------------------- | --------------------------------------------------------------------------- |
| 1   | GET    | `/orders`                                | `ordersService.js` não expõe `list()`                                       |
| 2   | PATCH  | `/orders/{order_id}/archive`             | `apiClient.js` não possui método PATCH — **estruturalmente inalcançável**   |
| 3   | GET    | `/contracts/hedge`                       | `contractsService.js` não expõe `list()`                                    |
| 4   | PATCH  | `/contracts/hedge/{contract_id}/archive` | `apiClient.js` não possui método PATCH — **estruturalmente inalcançável**   |
| 5   | GET    | `/linkages`                              | `linkagesService.js` não expõe `list()`                                     |
| 6   | GET    | `/rfqs`                                  | `rfqService.js` não expõe `list()`                                          |
| 7   | GET    | `/rfqs/{rfq_id}/quotes`                  | `rfqService.js` não expõe `listQuotes()`                                    |
| 8   | PATCH  | `/rfqs/{rfq_id}/archive`                 | `apiClient.js` não possui método PATCH — **estruturalmente inalcançável**   |
| 9   | GET    | `/audit/events/{event_id}/verify`        | `auditService.js` não expõe `verify()`                                      |
| 10  | POST   | `/mtm/snapshots`                         | `mtmService.js` tem `getSnapshot()` (GET) mas não `createSnapshot()` (POST) |
| 11  | GET    | `/webhooks/whatsapp`                     | Callback Meta — não é endpoint para UI                                      |
| 12  | POST   | `/webhooks/whatsapp`                     | Callback Meta — não é endpoint para UI                                      |

---

## Divergências Frontend ↔ Backend

### C.1 — Endpoints fantasma (404 em runtime)

O arquivo `frontend/webapp/service/cashflowsService.js` chama endpoints que **não existem** no backend:

| Função frontend | Chamada HTTP                  | Endpoint backend correspondente |
| --------------- | ----------------------------- | ------------------------------- |
| `list()`        | `GET /cashflows`              | **NÃO EXISTE**                  |
| `create()`      | `POST /cashflows`             | **NÃO EXISTE**                  |
| `getById(id)`   | `GET /cashflows/{cashflowId}` | **NÃO EXISTE**                  |

O backend não possui nenhuma rota em `/cashflows`. As rotas reais de cashflow são:

- `GET /cashflow/analytic`
- `POST /cashflow/baseline/snapshots`
- `GET /cashflow/baseline/snapshots`
- `POST /cashflow/contracts/{contract_id}/settle`
- `GET /cashflow/ledger`
- `GET /cashflow/ledger/hedge-contracts/{contract_id}`

**Impacto**: Qualquer view/controller que dependa de `cashflowsService.js` retornará 404/405 em produção.

### C.2 — apiClient.js não suporta PATCH/PUT/DELETE

O módulo `frontend/webapp/service/apiClient.js` (171 linhas) exporta exclusivamente:

```javascript
return {
  getJson: function (path) {
    /* GET */
  },
  getText: function (path) {
    /* GET */
  },
  postJson: function (path, body) {
    /* POST */
  },
};
```

**Métodos ausentes**: `patchJson`, `putJson`, `deleteJson`.

Isso torna os 3 endpoints PATCH do backend **estruturalmente inalcançáveis** pela UI:

| Endpoint                                       | Handler                  |
| ---------------------------------------------- | ------------------------ |
| `PATCH /orders/{order_id}/archive`             | `archive_order`          |
| `PATCH /contracts/hedge/{contract_id}/archive` | `archive_hedge_contract` |
| `PATCH /rfqs/{rfq_id}/archive`                 | `archive_rfq`            |

### C.3 — Ausência de autenticação no frontend

O backend protege **35 dos 42 endpoints** com `require_role()` ou `require_any_role()`.

O `apiClient.js` **não inclui nenhum header `Authorization`** — nenhum token JWT, nenhum interceptor de autenticação. Todas as requests são enviadas sem credenciais:

```javascript
// apiClient.js — headers enviados
headers: {
  Accept: "application/json"             // GET
}
headers: {
  Accept: "application/json",            // POST
  "Content-Type": "application/json"
}
```

**Impacto**: Com middleware de auth ativo, **todos os 35 endpoints protegidos** retornarão `401 Unauthorized`.

### C.4 — manifest.json declara /api/v1/ sem correspondência no backend

O `frontend/webapp/manifest.json` declara:

```json
"dataSources": {
  "mainService": {
    "uri": "/api/v1/",
    "type": "JSON"
  }
}
```

As rotas do backend **não possuem prefixo `/api/v1/`** — são `/orders`, `/rfqs`, `/contracts`, etc.

Este dataSource nunca é vinculado a um named model — todas as chamadas passam pela camada imperativa de services via `apiClient.js` — logo **não causa 404 hoje**, mas é uma declaração inconsistente que quebrará se alguém tentar usar model binding.

### C.5 — Endpoints de listagem sem consumo

Cinco endpoints de listagem existem no backend mas não são consumidos por nenhum service no frontend:

| Endpoint                    | Handler                | Service file                         |
| --------------------------- | ---------------------- | ------------------------------------ |
| `GET /orders`               | `list_orders`          | `ordersService.js` — sem `list()`    |
| `GET /contracts/hedge`      | `list_hedge_contracts` | `contractsService.js` — sem `list()` |
| `GET /linkages`             | `list_linkages`        | `linkagesService.js` — sem `list()`  |
| `GET /rfqs`                 | `list_rfqs`            | `rfqService.js` — sem `list()`       |
| `GET /rfqs/{rfq_id}/quotes` | `list_rfq_quotes`      | `rfqService.js` — sem `listQuotes()` |

**Impacto**: Impossível construir telas de listagem/tabela para essas entidades sem adicionar as funções nos services correspondentes.

---

## Estatísticas

```
Backend total ................. 42 endpoints
  ├─ Infraestrutura ........... 3  (health, ready, metrics)
  ├─ Domínio .................. 37
  └─ Webhook (Meta) ........... 2

Frontend total ................ 38 chamadas HTTP (em 16 service files)

Consumo:
  ├─ ✅ Consumidos ............. 30  (71,4%)
  ├─ ❌ Não consumidos ......... 10  (23,8%)
  └─ ❌ N/A (webhook) .......... 2   (4,8%)

Divergências críticas:
  ├─ Phantom endpoints (404) .. 3   (cashflowsService.js)
  ├─ PATCH inalcançável ....... 3   (apiClient.js sem PATCH)
  ├─ Auth ausente na UI ....... 35  endpoints protegidos
  └─ Listagem sem consumo ..... 5   endpoints GET list
```

---

## Arquitetura do apiClient.js

```
┌─────────────────────────────────────────┐
│            apiClient.js                 │
├─────────────────────────────────────────┤
│                                         │
│  Resolução de Base URL (prioridade):    │
│  1. Query string ?apiBaseUrl=           │
│  2. Config.js __HC_API_BASE_URL__       │
│  3. localStorage hc.apiBaseUrl          │
│  4. Same-origin (string vazia)          │
│                                         │
│  ⚠ Azure Static Web Apps sem config    │
│    → throw API_BASE_URL_NOT_CONFIGURED  │
│                                         │
├─────────────────────────────────────────┤
│  Métodos expostos:                      │
│  • getJson(path)  → GET  + parseJson    │
│  • getText(path)  → GET  + parseText    │
│  • postJson(path) → POST + parseJson    │
│                                         │
│  ❌ Ausentes: patchJson, putJson,       │
│              deleteJson                 │
├─────────────────────────────────────────┤
│  ❌ Sem header Authorization            │
│  ❌ Sem interceptor de auth             │
│  ❌ Sem refresh token                   │
└─────────────────────────────────────────┘
```

---

## Mapa de Service Files do Frontend

```
frontend/webapp/service/
├── apiClient.js                       ← HTTP client central (GET/POST only)
├── observabilityService.js            ← /health, /ready, /metrics
├── ordersService.js                   ← /orders/sales, /orders/purchase, /orders/{id}
├── exposuresService.js                ← /exposures/commercial, /exposures/global
├── contractsService.js                ← /contracts/hedge (POST), /contracts/hedge/{id}
├── linkagesService.js                 ← /linkages (POST), /linkages/{id}
├── rfqService.js                      ← /rfqs (CRUD + actions, 8 chamadas)
├── cashflowsService.js                ← ⚠ PHANTOM: /cashflows (NÃO EXISTE no backend)
├── cashflowAnalyticService.js         ← /cashflow/analytic
├── cashflowBaselineSnapshotsService.js← /cashflow/baseline/snapshots (GET + POST)
├── cashflowLedgerService.js           ← /cashflow/contracts/{id}/settle, /cashflow/ledger
├── plService.js                       ← /pl/{type}/{id}, /pl/snapshots (GET + POST)
├── mtmService.js                      ← /mtm/hedge-contracts/{id}, /mtm/orders/{id}, /mtm/snapshots
├── scenarioService.js                 ← /scenario/what-if/run
├── auditService.js                    ← /audit/events
└── marketDataService.js               ← /market-data/westmetall/.../ingest
```

---

_Documento gerado por análise estática do código-fonte. Nenhuma suposição de comportamento implícito._
