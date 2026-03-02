# Gap Analysis: Legacy Backend vs New Backend

> **Gerado em:** Junho 2025 | **Revisado em:** Março 2026
> **Escopo:** Comparação exaustiva entre o backend legacy (`Hedge_Control_Alcast-Backend`) e o novo backend (`HEDGE-CONTROL-NEW`).
> **Método:** Análise profunda de todos os ~48 services, ~47 routes, 50 models (legacy) vs 23 services, 13 route files (47 endpoints), 15 models (novo).

### Decisões de Escopo (Revisão Março 2026)

1. **Westmetall é a única fonte de preços** — LME Scraper (Playwright) descartado. Toda referência a `lme_public.py` e scraping LME intraday removida do escopo.
2. **Sem gestão de estoques/locações** — O sistema não controlará inventário físico. `Warehouse Locations` e `Inventory Management` removidos.
3. **Deal e Exposure são fundamentais** — São a base para cálculos de P&L consolidado e para tomada de decisões de hedge. Implementação prioritária.
4. **RFQ apresenta resultados do legacy, orquestrado por LLM** — O sistema de RFQ deve entregar os mesmos resultados/outputs do legacy, mas usando o LLM Agent como orquestrador em vez de lógica inline.

---

## Resumo Executivo

| Métrica           | Legacy                        | Novo                       | Cobertura |
| ----------------- | ----------------------------- | -------------------------- | --------- |
| Services          | 48 arquivos                   | 23 arquivos                | ~48%      |
| Routes            | 47 arquivos (~140+ endpoints) | 13 arquivos (47 endpoints) | ~34%      |
| Models/Tabelas    | 50 classes / 42 tabelas       | 15 classes / 15 tabelas    | ~36%      |
| Enums             | 18+                           | ~3 (inline)                | ~17%      |
| Linhas de serviço | ~8.500+                       | ~3.578                     | ~42%      |

O novo backend tem **arquitetura superior** (UUID PKs, Pydantic schemas, HMAC audit, LLM integration, what-if engine), mas cobre apenas **~35-40% das funcionalidades de negócio** do legacy.

---

## Legenda de Prioridade

| Prioridade          | Significado                                                |
| ------------------- | ---------------------------------------------------------- |
| 🔴 **P0 — Crítico** | Funcionalidade core de negócio, bloqueia operações diárias |
| 🟠 **P1 — Alto**    | Funcionalidade importante, impacta governança/compliance   |
| 🟡 **P2 — Médio**   | Funcionalidade desejável, melhoria operacional             |
| 🟢 **P3 — Baixo**   | Nice-to-have, pode ser adiado                              |

---

## 1. GAPS CRÍTICOS (P0) — Funcionalidades Core Ausentes

### 1.1 Deal Engine — Gestão de Negócios

**Legacy:** `deal_engine.py` (190 linhas) + models `Deal`, `DealLink`, `DealPNLSnapshot` + route `deals.py`
**Novo:** ❌ Completamente ausente

| Funcionalidade                   | Descrição                                                               |
| -------------------------------- | ----------------------------------------------------------------------- |
| Criação de Deal a partir de SO   | Agrupamento de Sales Orders em Deals                                    |
| Vinculação PO/Hedge via DealLink | Links polimórficos (SO, PO, Contract, Hedge)                            |
| P&L consolidado por Deal         | `physical_revenue + hedge_pnl_realized + hedge_pnl_mtm - physical_cost` |
| Deal lifecycle status            | `open → partially_hedged → fully_hedged → settled → closed`             |

**Impacto:** Sem deals, não há visão consolidada de negócios. O P&L fica fragmentado por contrato. **Deal é a entidade central que conecta SO → PO → Hedge → Contract e permite calcular P&L físico + financeiro de forma unificada. É pré-requisito para decisões de hedge informadas.**

**Modelos necessários:** `Deal`, `DealLink`, `DealPNLSnapshot` (3 tabelas)
**Estimativa:** ~400 linhas (service + route + schemas)

---

### 1.2 Exposure Engine — Motor de Exposição

**Legacy:** `exposure_engine.py` (225 linhas) + `exposure_aggregation.py` (100 linhas) + `exposure_timeline.py` (115 linhas) + models `Exposure`, `ContractExposure`, `HedgeExposure`, `HedgeTask` + routes `exposures.py`, `exposure_links.py`, `net_exposure.py`
**Novo:** ⚠️ Parcial — tem `exposure_service.py` (270 linhas) que computa snapshots analíticos, mas **sem persistência**, sem engine de reconciliação, sem auto-cancelamento de HedgeTasks

| Presente no Novo                          | Ausente                                      |
| ----------------------------------------- | -------------------------------------------- |
| ✅ Snapshot de exposição comercial/global | ❌ Reconciliação automática SO/PO → Exposure |
| ✅ Cálculo net exposure                   | ❌ Persistência de exposições no banco       |
|                                           | ❌ HedgeTask auto-creation/cancellation      |
|                                           | ❌ ContractExposure / HedgeExposure links    |
|                                           | ❌ Timeline de mudanças de exposição         |
|                                           | ❌ CRUD de exposições                        |
|                                           | ❌ Exposure links management                 |
|                                           | ❌ Net exposure aggregation route            |

**Impacto:** **Exposure é a base para toda decisão de hedge.** Sem exposição persistida e reconciliada, o operador não sabe quanto do risco de preço está aberto vs. coberto. É pré-requisito para Deal P&L, Treasury Decisions e Finance Pipeline.

**Modelos necessários:** `Exposure`, `ContractExposure`, `HedgeExposure`, `HedgeTask` (4 tabelas)
**Estimativa:** ~600 linhas adicionais

---

### 1.3 Hedge Lifecycle — Gestão de Hedges

**Legacy:** routes `hedges.py` + `hedge_manual.py` + `hedge_tasks.py` + model `Hedge` (com 15+ colunas)
**Novo:** ❌ Sem CRUD de hedges, sem lifecycle

| Funcionalidade           | Descrição                                       |
| ------------------------ | ----------------------------------------------- |
| CRUD de Hedges           | Criação, listagem, detalhamento                 |
| Hedge Manual             | Criação manual com KYC gate + workflow approval |
| Hedge Tasks              | Pending tasks derivadas de exposições           |
| Hedge status machine     | `active → closed → cancelled`                   |
| Vínculo Hedge ↔ Exposure | Via HedgeExposure                               |

**Impacto:** O `HedgeContract` do novo backend é um contrato de hedge (output do RFQ award), mas não há entidade `Hedge` separada para gestão de posições.

**Estimativa:** ~500 linhas

---

### 1.4 Sales Orders & Purchase Orders — CRUD Completo

**Legacy:** `sales_orders.py`, `purchase_orders.py` (CRUD completo com exposure reconciliation triggers)
**Novo:** ⚠️ Parcial — tem `orders.py` com POST/GET/PATCH, mas sem:

| Presente no Novo          | Ausente                                                                 |
| ------------------------- | ----------------------------------------------------------------------- |
| ✅ Criar SO/PO            | ❌ Trigger de reconciliação de exposição                                |
| ✅ Listar/detalhar orders | ❌ SoPoLink (vinculação direta SO↔PO)                                   |
| ✅ Soft-delete            | ❌ Campos detalhados (pricing_type, counterparty, delivery_terms, etc.) |
|                           | ❌ Enums OrderStatus, PricingType diferenciados                         |

**Modelos necessários:** Ampliar `Order` com campos do legacy `SalesOrder`/`PurchaseOrder`
**Estimativa:** ~200 linhas de migração de modelo + schemas

---

### 1.5 Finance Pipeline Daily — Orquestrador Diário

**Legacy:** `finance_pipeline_daily.py` (698 linhas!) + `finance_pipeline_run_service.py` (258 linhas) + `finance_pipeline_timeline.py` (97 linhas) + models `FinancePipelineRun`, `FinancePipelineStep`
**Novo:** ❌ Completamente ausente

Pipeline de 6 etapas (idempotente, resumível):

1. **Market Snapshot** — Captura preços LME/Westmetall
2. **MTM Computation** — Calcula MTM de todos os contratos
3. **P&L Snapshot** — Materializa P&L
4. **Cashflow Baseline** — Gera projeções de fluxo de caixa
5. **Risk Flags** — Sinaliza problemas de qualidade de dados
6. **Exports** — Gera artefatos para auditoria

**Impacto:** Sem o pipeline, todas as operações de fim de dia precisam ser manuais. É o coração operacional do sistema.

**Modelos necessários:** `FinancePipelineRun`, `FinancePipelineStep` (2 tabelas)
**Estimativa:** ~1.000 linhas (pipeline + run service + timeline)

---

### 1.6 Contracts — Enriquecimento de Dados

**Legacy:** `contracts.py` route com trade leg enrichment, settlement adjustment, exposure allocations + model `Contract` (UUID PK, JSON `trade_snapshot`, `@validates`, status enum, FK para RFQ/Counterparty/SO)
**Novo:** ⚠️ Parcial — tem `HedgeContract` com campos básicos

| Presente no Novo     | Ausente no Novo                                    |
| -------------------- | -------------------------------------------------- |
| ✅ CRUD básico       | ❌ `trade_snapshot` (JSON blob do estado do trade) |
| ✅ FK para RFQ/Quote | ❌ Settlement date/value computation               |
| ✅ Soft delete       | ❌ Trade leg enrichment na listagem                |
|                      | ❌ Exposure allocation display                     |
|                      | ❌ `@validates` hooks (invariant checks)           |

**Estimativa:** ~250 linhas de enriquecimento

---

## 2. GAPS ALTOS (P1) — Governança e Compliance

### 2.1 KYC & Compliance Suite

**Legacy:** `kyc.py` (40 linhas) + `kyc_gate.py` (120 linhas) + `so_kyc_gate.py` (91 linhas) + models `KycDocument`, `CreditCheck`, `KycCheck`
**Novo:** ❌ Completamente ausente

| Componente       | Lógica                                                                                          |
| ---------------- | ----------------------------------------------------------------------------------------------- |
| `kyc.py`         | Mock credit check — score determinístico via hash                                               |
| `kyc_gate.py`    | Gate multi-critério: `kyc_status`, sanctions, risk_rating, TTL expiration, required check types |
| `so_kyc_gate.py` | Gate específico para Sales Orders                                                               |

**Onde é usado no legacy:**

- `rfqs.py` → KYC gate no create e award
- `hedge_manual.py` → KYC gate na criação manual
- `treasury_decisions.py` → KYC gate (non-blocking)

**Modelos necessários:** `KycDocument`, `CreditCheck`, `KycCheck` (3 tabelas)
**Estimativa:** ~350 linhas

---

### 2.2 Workflow Approvals — Aprovações com Threshold

**Legacy:** `workflow_approvals.py` (281 linhas) + models `WorkflowRequest`, `WorkflowDecision` + route `workflows.py`
**Novo:** ❌ Completamente ausente

| Funcionalidade       | Detalhes                                         |
| -------------------- | ------------------------------------------------ |
| Ações controladas    | `rfq.award`, `hedge.manual.create`               |
| Threshold            | > $250.000 → requer role `financeiro` ou `admin` |
| Ciclo de vida        | `pending → approved/rejected/adjustment`         |
| Idempotência         | Request creation idempotente                     |
| RBAC decision matrix | Papel do usuário × ação × valor                  |

**Modelos necessários:** `WorkflowRequest`, `WorkflowDecision` (2 tabelas)
**Estimativa:** ~400 linhas

---

### 2.3 Treasury Decisions — Decisões de Tesouraria

**Legacy:** `treasury_decisions_service.py` (210 linhas) + route `treasury_decisions.py` + models `TreasuryDecision`, `TreasuryKycOverride`
**Novo:** ❌ Completamente ausente

| Funcionalidade           | Detalhes                                  |
| ------------------------ | ----------------------------------------- |
| Decision lifecycle       | Registrar decisões de hedge por exposição |
| KYC gates (non-blocking) | Verifica KYC mas permite override         |
| KYC override audit       | Registra quem fez override e por quê      |
| Timeline integration     | Emite eventos para timeline               |

**Modelos necessários:** `TreasuryDecision`, `TreasuryKycOverride` (2 tabelas)
**Estimativa:** ~350 linhas

---

### 2.4 Document Numbering — Numeração Sequencial

**Legacy:** `document_numbering.py` (85 linhas) + model `DocumentMonthlySequence`
**Novo:** ⚠️ Parcial — o `RFQSequence` no novo backend é autoincrement simples

| Legacy                                   | Novo                                      |
| ---------------------------------------- | ----------------------------------------- |
| `RFQ_001-03.25` (mensal, reseta por mês) | `RFQ-{autoincrement}` (sequencial global) |
| `SELECT FOR UPDATE` (concurrency-safe)   | Sem lock explícito                        |
| Configurável por prefixo                 | Fixo para RFQ                             |

**Estimativa:** ~100 linhas

---

### 2.5 Timeline System — Eventos Unificados

**Legacy:** `timeline_emitters.py` (97 linhas) + `timeline_attachments_storage.py` (64 linhas) + model `TimelineEvent` + route `timeline.py` (8 endpoints)
**Novo:** ❌ Completamente ausente (o `AuditEvent` do novo é audit trail, não timeline)

| Funcionalidade    | Detalhes                                                                    |
| ----------------- | --------------------------------------------------------------------------- |
| Machine events    | Emissão automática de eventos de sistema                                    |
| Human comments    | Comentários manuais por usuários                                            |
| Corrections       | Registro de correções                                                       |
| Attachments       | Upload/download de arquivos                                                 |
| @mentions         | Menções de usuários em comentários                                          |
| RBAC visibility   | Filtragem por role do usuário                                               |
| Fingerprint dedup | Detecção de mudanças via fingerprint                                        |
| 8 endpoints       | list, recent, machine, comments, corrections, attachments, upload, download |

**Modelos necessários:** `TimelineEvent` (1 tabela, ~20 colunas)
**Estimativa:** ~400 linhas

---

### 2.6 Finance Risk Flags

**Legacy:** `finance_risk_flags_service.py` (185 linhas) + models `FinanceRiskFlagRun`, `FinanceRiskFlag`
**Novo:** ❌ Completamente ausente

Materializa flags de qualidade de dados a partir do baseline de cashflow:

- Missing settlement dates
- Missing prices
- Quantity mismatches
- Stale market data

**Modelos necessários:** `FinanceRiskFlagRun`, `FinanceRiskFlag` (2 tabelas)
**Estimativa:** ~200 linhas

---

## 3. GAPS MÉDIOS (P2) — Funcionalidades Operacionais

### 3.1 Customers, Suppliers, Counterparties — CRUD de Entidades

**Legacy:** routes `customers.py`, `suppliers.py`, `counterparties.py` + models `Customer` (30+ colunas), `Supplier` (30+ colunas), `Counterparty` (30+ colunas)
**Novo:** ❌ Completamente ausente — RFQs e Contracts referenciam `counterparty_id` mas não há tabela/CRUD

| Modelo       | Colunas-chave Legacy                                                                                                |
| ------------ | ------------------------------------------------------------------------------------------------------------------- |
| Customer     | name, tax_id, address, bank_info, payment_terms, credit_limit, kyc_status, sanctions_status, risk_rating + KYC docs |
| Supplier     | Idêntico ao Customer (30+ colunas, sem mixin)                                                                       |
| Counterparty | Idêntico — name, type (enum), contact, bank details, KYC fields                                                     |

**Impacto:** Sem cadastro de contrapartes, todo o sistema depende de IDs hardcoded ou strings.

**Modelos necessários:** Pelo menos `Counterparty` (1 tabela unificada)
**Estimativa:** ~300 linhas (CRUD + schema)

---

### 3.2 Dashboard — Painel Operacional

**Legacy:** route `dashboard.py` — 6 widgets com TTL cache in-memory
**Novo:** ❌ Completamente ausente

| Widget            | Dados                              |
| ----------------- | ---------------------------------- |
| Exposure summary  | Net exposure por commodity         |
| Hedge summary     | Hedges ativos, valor total         |
| P&L summary       | P&L aggregado                      |
| Cash position     | Posição de caixa                   |
| Pending approvals | Workflows pending count            |
| Recent timeline   | Últimos eventos filtrados por role |

**Estimativa:** ~200 linhas

---

### 3.3 Exports Suite — Auditoria e Relatórios

**Legacy:** 9 services (~2.240 linhas total) + route `exports.py`
**Novo:** ❌ Completamente ausente

| Service                    | Linhas | Funcionalidade                                        |
| -------------------------- | ------ | ----------------------------------------------------- |
| `exports_chain_export.py`  | 1.058  | Grafo completo de entidades como CSV/PDF/manifest/ZIP |
| `exports_state_at_time.py` | 483    | Snapshot point-in-time do sistema (regulatório)       |
| `exports_audit_log.py`     | ~100   | Exportação de audit logs                              |
| `exports_job_service.py`   | ~150   | Gestão de jobs assíncronos de exportação              |
| `exports_manifest.py`      | ~80    | Geração de manifesto SHA256                           |
| `exports_pdf.py`           | ~100   | Geração de PDF                                        |
| `exports_pnl_aggregate.py` | ~80    | P&L agregado para exportação                          |
| `exports_storage.py`       | ~90    | Storage abstraction para artefatos                    |
| `exports_worker.py`        | ~100   | Worker assíncrono de exportação                       |

**Modelos necessários:** `ExportJob` (1 tabela)
**Estimativa:** ~2.500 linhas (é o maior gap em volume de código)

---

### 3.4 Reports — Relatórios Operacionais

**Legacy:** route `reports.py` — 5 endpoints
**Novo:** ❌ Completamente ausente

| Endpoint                        | Funcionalidade                                     |
| ------------------------------- | -------------------------------------------------- |
| Cashflow ledger (JSON)          | Ledger em formato JSON                             |
| Cashflow ledger (CSV)           | Export CSV                                         |
| Cashflow ledger público (token) | Endpoint público token-authenticated para BI tools |
| RFQ por counterparty            | Relatório de RFQs agrupado por contraparte         |
| RFQ attempts                    | Histórico de tentativas de envio                   |
| RFQ unified export              | Exportação unificada com quotes + invitations      |

**Estimativa:** ~300 linhas

---

### ~~3.5 Inventory Management~~ _(REMOVIDO DO ESCOPO)_

> **Decisão:** O sistema não controlará estoque físico. Removido na revisão de Março 2026.

---

### 3.5 Inbox / Workbench View

**Legacy:** route `inbox.py` — Workbench com counts, net exposure matrix, exposure decisions
**Novo:** ❌ Completamente ausente

**Estimativa:** ~200 linhas

---

### 3.6 Scheduler — Jobs Automáticos

**Legacy:** `scheduler.py` (185 linhas) — Background daemon
**Novo:** ❌ Completamente ausente

| Job                      | Horário   | Ação                      |
| ------------------------ | --------- | ------------------------- |
| Westmetall scraper       | 09:00 UTC | Captura preços diários    |
| Finance pipeline         | 10:00 UTC | Executa pipeline completo |
| PostgreSQL advisory lock | —         | Garante single-instance   |

**Estimativa:** ~200 linhas

---

### 3.7 Users & Auth — CRUD Completo

**Legacy:** route `users.py` (CRUD + bootstrap) + `auth.py` (token login, /me, signup + Entra ID gate) + models `User`, `Role`
**Novo:** ❌ Sem CRUD de users, sem roles persistidas — auth é JWT validation only

| Legacy                                   | Novo               |
| ---------------------------------------- | ------------------ |
| User CRUD (create, list, update, delete) | Sem CRUD           |
| Role model + assignment                  | Sem roles no banco |
| Bootstrap pattern (first user = no auth) | Sem bootstrap      |
| Signup com Entra ID gate                 | Sem signup         |
| `/me` endpoint                           | Sem `/me`          |

**Modelos necessários:** `User`, `Role` (2 tabelas)
**Estimativa:** ~300 linhas

---

## 4. GAPS BAIXOS (P3) — Nice-to-have

### ~~4.1 LME Public Scraper (Playwright)~~ _(REMOVIDO DO ESCOPO)_

> **Decisão:** Westmetall é a única fonte de preços. LME Scraper descartado na revisão de Março 2026.

### ~~4.2 Market Data Hub (multi-source)~~ _(ESCOPO REDUZIDO)_

> **Decisão:** Com Westmetall como fonte única, o hub multi-source (Yahoo Finance, LME ingest, aluminum fallback chain) não é necessário. O `CashSettlementPrice` + `price_lookup_service.py` existentes atendem ao requisito.

### ~~4.3 Warehouse Locations~~ _(REMOVIDO DO ESCOPO)_

> **Decisão:** Sistema não controlará estoque físico. Removido na revisão de Março 2026.

### 4.1 FX Policies

**Legacy:** route `fx_policies.py` + model `FxPolicyMap`
**Novo:** ❌ Ausente
**Estimativa:** ~100 linhas

### 4.2 Analytics — Entity Tree

**Legacy:** route `analytics.py` — Entity tree (Deals → SOs/POs/Contracts hierarchy)
**Novo:** ❌ Ausente
**Estimativa:** ~150 linhas

### 4.3 MTM/P&L Enhancements

**Legacy:**

- `mtm_service.py` com FX conversion e scenario adjustments
- `mtm_snapshot_service.py` com snapshots multi-object
- `pnl_engine.py` com trade spec parsing (avg/avginter/fix/c2r)
- Models: `MtmRecord`, `MtmContractSnapshot` (run pattern), `PnlSnapshotRun`, `PnlContractSnapshot`, `PnlContractRealized`

**Novo:** ⚠️ Parcial — tem MTM e P&L básicos mas sem:

- FX conversion
- Scenario adjustments (tem what-if separado)
- Trade spec parsing detalhado
- Run pattern (PnlSnapshotRun + items)
- Realized P&L tracking (PnlContractRealized)

**Estimativa:** ~500 linhas para paridade

---

## 5. FUNCIONALIDADES ONDE O NOVO SUPERA O LEGACY

| Funcionalidade                                                               | Novo                                                                            | Legacy                              |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ----------------------------------- |
| **LLM Agent** (`llm_agent.py`, 285 linhas)                                   | ✅ Azure OpenAI GPT-4o-mini para classificação e parsing de mensagens           | ❌ Inexistente                      |
| **RFQ Orchestrator** (`rfq_orchestrator.py`, 310 linhas)                     | ✅ Pipeline LLM-powered: auto-quote extraction, counter-party matching, ranking | ❌ Inexistente                      |
| **Scenario What-If** (`scenario_whatif_service.py`, 534 linhas)              | ✅ Engine completo de simulação sandboxed com shifts de preço                   | ❌ Inexistente                      |
| **HMAC Audit Trail** (`audit_trail_service.py`, 100 linhas)                  | ✅ Assinatura criptográfica de eventos de auditoria                             | ⚠️ Auditoria simples sem assinatura |
| **Webhook Processor** (`webhook_processor.py`, 145 linhas)                   | ✅ Queue in-memory estruturada com HMAC verification                            | ⚠️ Parsing direto na rota           |
| **WhatsApp Cloud API** (`whatsapp_service.py`, 165 linhas)                   | ✅ Integração direta com Cloud API                                              | ⚠️ Stub/mock                        |
| **RFQ Engine** (`rfq_engine.py`, 624 linhas + `lme_calendar.py`, 145 linhas) | ✅ Gerador de texto RFQ holiday-aware com 10 formatos                           | ⚠️ Engine mais simples              |
| **Westmetall Scraper** (`westmetall_cash_settlement.py`, 166 linhas)         | ✅ Circuit breaker + retry pattern                                              | ⚠️ Scraper simples                  |
| **UUID Primary Keys**                                                        | ✅ Todos os models usam UUID                                                    | ⚠️ Misto (Integer + UUID)           |
| **Pydantic Schemas**                                                         | ✅ Validação rigorosa com Pydantic v2                                           | ⚠️ Schemas mais simples             |
| **Healthcheck duplo**                                                        | ✅ `/health` (liveness) + `/ready` (readiness com DB + JWKS)                    | ⚠️ Apenas `/health`                 |

---

## 6. MODELOS — Comparação Detalhada

### Tabelas no Legacy sem equivalente no Novo (27 tabelas ausentes)

| #      | Tabela Legacy                | Domínio         | Prioridade                                   |
| ------ | ---------------------------- | --------------- | -------------------------------------------- |
| 1      | `users`                      | Auth            | 🟡 P2                                        |
| 2      | `roles`                      | Auth            | 🟡 P2                                        |
| 3      | `deals`                      | Deal Engine     | 🔴 P0                                        |
| 4      | `deal_links`                 | Deal Engine     | 🔴 P0                                        |
| 5      | `deal_pnl_snapshots`         | Deal Engine     | 🔴 P0                                        |
| 6      | `exposures`                  | Exposure        | 🔴 P0                                        |
| 7      | `contract_exposures`         | Exposure        | 🔴 P0                                        |
| 8      | `hedge_exposures`            | Exposure        | 🔴 P0                                        |
| 9      | `hedge_tasks`                | Exposure        | 🔴 P0                                        |
| 10     | `hedges`                     | Hedge           | 🔴 P0                                        |
| 11     | `customers`                  | Entity          | 🟡 P2                                        |
| 12     | `suppliers`                  | Entity          | 🟡 P2                                        |
| 13     | `counterparties`             | Entity          | 🟡 P2                                        |
| 14     | `kyc_documents`              | Compliance      | 🟠 P1                                        |
| 15     | `credit_checks`              | Compliance      | 🟠 P1                                        |
| 16     | `kyc_checks`                 | Compliance      | 🟠 P1                                        |
| 17     | `workflow_requests`          | Governance      | 🟠 P1                                        |
| 18     | `workflow_decisions`         | Governance      | 🟠 P1                                        |
| 19     | `treasury_decisions`         | Treasury        | 🟠 P1                                        |
| 20     | `treasury_kyc_overrides`     | Treasury        | 🟠 P1                                        |
| 21     | `timeline_events`            | Timeline        | 🟠 P1                                        |
| 22     | `document_monthly_sequences` | Doc Numbering   | 🟠 P1                                        |
| 23     | `finance_pipeline_runs`      | Pipeline        | 🔴 P0                                        |
| 24     | `finance_pipeline_steps`     | Pipeline        | 🔴 P0                                        |
| 25     | `finance_risk_flag_runs`     | Risk            | 🟠 P1                                        |
| 26     | `finance_risk_flags`         | Risk            | 🟠 P1                                        |
| 27     | `export_jobs`                | Exports         | 🟡 P2                                        |
| ~~28~~ | ~~`warehouse_locations`~~    | ~~Ops~~         | ❌ Fora do escopo                            |
| 29     | `fx_policy_map`              | FX              | 🟢 P3                                        |
| ~~30~~ | ~~`market_prices`~~          | ~~Market Data~~ | ❌ Fora do escopo (Westmetall = fonte única) |
| ~~31~~ | ~~`lme_prices`~~             | ~~Market Data~~ | ❌ Fora do escopo (Westmetall = fonte única) |
| 32     | `mtm_records`                | MTM             | 🟢 P3                                        |
| 33     | `pnl_snapshot_runs`          | P&L             | 🟡 P2                                        |
| 34     | `pnl_contract_snapshots`     | P&L             | 🟡 P2                                        |
| 35     | `pnl_contract_realized`      | P&L             | 🟡 P2                                        |
| 36     | `mtm_contract_snapshot_runs` | MTM             | 🟢 P3                                        |
| 37     | `cashflow_baseline_runs`     | Cashflow        | 🟡 P2                                        |
| 38     | `whatsapp_messages`          | Messaging       | 🟢 P3                                        |
| 39     | `so_po_links`                | Orders          | 🟡 P2                                        |

### Tabelas no Novo sem equivalente no Legacy (2 tabelas novas)

| #   | Tabela Novo              | Domínio                             |
| --- | ------------------------ | ----------------------------------- |
| 1   | `rfq_state_events`       | RFQ (event-sourcing de estados)     |
| 2   | `cash_settlement_prices` | Market Data (Westmetall persistido) |

---

## 7. ROUTES — Comparação por Domínio

### Endpoints no Legacy sem equivalente no Novo (~93 endpoints ausentes)

| Domínio                   | Endpoints Legacy                 | Endpoints Novo | Gap                                          |
| ------------------------- | -------------------------------- | -------------- | -------------------------------------------- |
| Deals                     | ~5 (CRUD + links)                | 0              | -5                                           |
| Exposures                 | ~8 (CRUD + links + net)          | 2 (snapshots)  | -6                                           |
| Hedges                    | ~8 (CRUD + manual + tasks)       | 0              | -8                                           |
| Customers                 | ~4 (CRUD)                        | 0              | -4                                           |
| Suppliers                 | ~4 (CRUD)                        | 0              | -4                                           |
| Counterparties            | ~4 (CRUD + KYC docs)             | 0              | -4                                           |
| Workflows                 | ~4 (list + decide)               | 0              | -4                                           |
| Treasury                  | ~4 (CRUD + KYC override)         | 0              | -4                                           |
| Timeline                  | 8 (list + human events)          | 0              | -8                                           |
| Dashboard                 | 6 (widgets)                      | 0              | -6                                           |
| Exports                   | ~4 (manifest + jobs)             | 0              | -4                                           |
| Reports                   | 5 (ledger + RFQ reports)         | 0              | -5                                           |
| Finance Pipeline          | 2 (run + status)                 | 0              | -2                                           |
| ~~Inventory~~             | ~~~3 (list + CSV)~~              | ~~0~~          | ❌ Fora do escopo                            |
| Inbox                     | ~3 (workbench)                   | 0              | -3                                           |
| Users                     | ~4 (CRUD + bootstrap)            | 0              | -4                                           |
| Auth                      | 3 (login + me + signup)          | 0              | -3                                           |
| ~~Locations~~             | ~~~3 (CRUD)~~                    | ~~0~~          | ❌ Fora do escopo                            |
| FX Policies               | ~2 (upsert + list)               | 0              | -2                                           |
| ~~Market Data (LME)~~     | ~~~6 (ingest + live + history)~~ | ~~0~~          | ❌ Fora do escopo (Westmetall = fonte única) |
| ~~Market Data (general)~~ | ~~~4 (CRUD + Yahoo)~~            | ~~0~~          | ❌ Fora do escopo                            |
| Settlements               | ~2 (today + upcoming)            | 0              | -2                                           |
| Analytics                 | ~2 (entity tree)                 | 0              | -2                                           |
| **TOTAL**                 | **~93 endpoints**                | **0**          | **-93**                                      |

### Endpoints no Novo sem equivalente no Legacy (~6 endpoints novos)

| Endpoint                          | Domínio                |
| --------------------------------- | ---------------------- |
| POST `/scenario/what-if/run`      | Scenario engine        |
| GET `/ready`                      | Readiness probe        |
| POST `/rfqs/preview-text`         | RFQ text preview       |
| GET `/rfqs/{id}/trade-ranking`    | Trade ranking          |
| POST `/rfqs/{id}/actions/refresh` | RFQ refresh            |
| GET `/cashflow/ledger`            | Ledger by source event |

---

## 8. SERVIÇOS — Comparação por Função

### Services no Legacy sem equivalente no Novo (25 services ausentes)

| #      | Service Legacy                    | Linhas     | Prioridade        |
| ------ | --------------------------------- | ---------- | ----------------- |
| 1      | `deal_engine.py`                  | 190        | 🔴 P0             |
| 2      | `exposure_engine.py`              | 225        | 🔴 P0             |
| 3      | `exposure_aggregation.py`         | 100        | 🔴 P0             |
| 4      | `exposure_timeline.py`            | 115        | 🔴 P0             |
| 5      | `finance_pipeline_daily.py`       | 698        | 🔴 P0             |
| 6      | `finance_pipeline_run_service.py` | 258        | 🔴 P0             |
| 7      | `finance_pipeline_timeline.py`    | 97         | 🔴 P0             |
| 8      | `kyc.py`                          | 40         | 🟠 P1             |
| 9      | `kyc_gate.py`                     | 120        | 🟠 P1             |
| 10     | `so_kyc_gate.py`                  | 91         | 🟠 P1             |
| 11     | `workflow_approvals.py`           | 281        | 🟠 P1             |
| 12     | `treasury_decisions_service.py`   | 210        | 🟠 P1             |
| 13     | `document_numbering.py`           | 85         | 🟠 P1             |
| 14     | `timeline_emitters.py`            | 97         | 🟠 P1             |
| 15     | `timeline_attachments_storage.py` | 64         | 🟠 P1             |
| 16     | `finance_risk_flags_service.py`   | 185        | 🟠 P1             |
| 17     | `scheduler.py`                    | 185        | 🟡 P2             |
| 18     | `lme_price_service.py`            | 111        | 🟡 P2             |
| 19     | `pnl_engine.py`                   | 235        | 🟡 P2             |
| 20     | `pnl_snapshot_service.py`         | 263        | 🟡 P2             |
| 21     | `pnl_timeline.py`                 | 40         | 🟡 P2             |
| ~~22~~ | ~~`lme_public.py`~~               | ~~248~~    | ❌ Fora do escopo |
| 23     | `exports_chain_export.py`         | 1.058      | 🟡 P2             |
| 24     | `exports_state_at_time.py`        | 483        | 🟡 P2             |
| 25     | 7× exports auxiliares             | ~600       | 🟡 P2             |
|        | **TOTAL**                         | **~5.580** |                   |

---

## 9. ROADMAP DE IMPLEMENTAÇÃO SUGERIDO

### Fase 1 — Core Domain (P0) — ~2.500 linhas

> **Objetivo:** Habilitar o ciclo completo Deal → Exposure → Hedge → P&L

| Ordem | Componente                                     | Deps          | Estimativa |
| ----- | ---------------------------------------------- | ------------- | ---------- |
| 1.1   | Counterparty model + CRUD                      | —             | 300 linhas |
| 1.2   | Ampliar Order model (campos SO/PO)             | —             | 200 linhas |
| 1.3   | Exposure engine (persistência + reconciliação) | 1.2           | 600 linhas |
| 1.4   | Hedge model + CRUD + lifecycle                 | 1.1, 1.3      | 500 linhas |
| 1.5   | Deal engine (Deal + DealLink + P&L)            | 1.2, 1.4      | 400 linhas |
| 1.6   | Finance Pipeline Daily (6 etapas)              | 1.3, 1.4, 1.5 | 500 linhas |

### Fase 2 — Governance (P1) — ~1.800 linhas

> **Objetivo:** Compliance, aprovações, auditoria

| Ordem | Componente                   | Deps     | Estimativa |
| ----- | ---------------------------- | -------- | ---------- |
| 2.1   | KYC suite (mock + gates)     | 1.1      | 350 linhas |
| 2.2   | Workflow approvals           | 2.1      | 400 linhas |
| 2.3   | Treasury decisions           | 2.1, 1.3 | 350 linhas |
| 2.4   | Timeline system              | —        | 400 linhas |
| 2.5   | Document numbering (monthly) | —        | 100 linhas |
| 2.6   | Finance risk flags           | 1.6      | 200 linhas |

### Fase 3 — Operations (P2) — ~1.600 linhas

> **Objetivo:** Dashboard, relatórios, exports

| Ordem | Componente                   | Deps      | Estimativa |
| ----- | ---------------------------- | --------- | ---------- |
| 3.1   | Dashboard (6 widgets)        | 1._, 2._  | 200 linhas |
| 3.2   | Reports (5 endpoints)        | 1.\*      | 300 linhas |
| 3.3   | Exports suite (simplificado) | 1.\*, 2.4 | 400 linhas |
| 3.4   | Scheduler                    | 1.6       | 200 linhas |
| 3.5   | Users + Auth CRUD            | —         | 300 linhas |
| 3.6   | Inbox/Workbench              | 1.\*, 2.2 | 200 linhas |

> **Nota:** Inventory Management e Warehouse Locations removidos desta fase (fora do escopo).

### Fase 4 — Enhancements (P3) — ~350 linhas

> **Objetivo:** Nice-to-haves

| Ordem   | Componente                                   | Deps | Estimativa        |
| ------- | -------------------------------------------- | ---- | ----------------- |
| 4.1     | FX policies                                  | —    | 100 linhas        |
| 4.2     | Analytics entity tree                        | 1.5  | 150 linhas        |
| 4.3     | MTM/P&L enhancements (FX, realized tracking) | 1.5  | 100 linhas        |
| ~~4.x~~ | ~~Market data hub (multi-source)~~           | —    | ❌ Fora do escopo |
| ~~4.x~~ | ~~Inventory management~~                     | —    | ❌ Fora do escopo |
| ~~4.x~~ | ~~Warehouse locations~~                      | —    | ❌ Fora do escopo |

---

## 10. ESTIMATIVA TOTAL

| Fase      | Prioridade | Linhas Estimadas  | Tabelas Novas   |
| --------- | ---------- | ----------------- | --------------- |
| Fase 1    | 🔴 P0      | ~2.500            | ~12             |
| Fase 2    | 🟠 P1      | ~1.800            | ~10             |
| Fase 3    | 🟡 P2      | ~1.600            | ~4              |
| Fase 4    | 🟢 P3      | ~350              | ~1              |
| **TOTAL** |            | **~6.250 linhas** | **~27 tabelas** |

> **Itens removidos do escopo (economia de ~1.050 linhas):**
>
> - LME Scraper (Playwright) — Westmetall é fonte única
> - Inventory Management — sem controle de estoque
> - Warehouse Locations — sem controle de locações
> - Market Data Hub multi-source — desnecessário com fonte única

> **Nota:** As estimativas incluem models + schemas + services + routes + testes unitários básicos. Os testes mais abrangentes (como os 60 testes do RFQ engine) adicionariam volume.

---

## 11. RECOMENDAÇÕES ARQUITETURAIS

1. **Manter o padrão UUID PK** do novo backend — não importar Integer PKs do legacy
2. **Consolidar Customer/Supplier/Counterparty** em um único model `Counterparty` com `type` enum — o legacy tem 3 modelos quase idênticos
3. **Reutilizar o `AuditEvent` existente** como base para timeline events — adicionar `event_category` para distinguir machine/human
4. **Implementar o Finance Pipeline como uma task queue** em vez de background daemon — mais cloud-native para Azure Container Apps
5. **Usar o LLM agent existente** para substituir o regex parsing do WhatsApp webhook legacy — já temos a infra
6. **Manter schemas Pydantic v2** — não importar os schemas simples do legacy
7. **Implementar Run → Items pattern** para todos os snapshots — é um padrão sólido que o legacy já validou
8. **Westmetall como fonte única de preços** — não implementar LME scraper, Yahoo Finance ou multi-source hub
9. **RFQ outputs do legacy, orquestração via LLM** — garantir que o sistema de RFQ entrega os mesmos resultados/formatos do legacy (textos, quotes, ranking, award → contract), mas com parsing e orquestração delegados ao LLM Agent existente em vez de lógica regex inline
10. **Deal + Exposure como pilares do domínio** — toda decisão de hedge e cálculo de P&L deve fluir a partir da cadeia Deal → Exposure → Hedge. Implementar primeiro, antes de governança e operações
