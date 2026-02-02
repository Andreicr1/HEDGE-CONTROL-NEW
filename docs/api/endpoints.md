# API Endpoints — Phase 3 (Step 2)

## Orders
- POST /orders/sales
- POST /orders/purchase
- GET /orders/{order_id}

## Exposures
- GET /exposures/commercial
- GET /exposures/global

## Contracts
- POST /contracts/hedge
- GET /contracts/hedge/{contract_id}

## Linkages
- POST /linkages
- GET /linkages/{linkage_id}

## RFQs
- POST /rfqs
- GET /rfqs/{rfq_id}
- POST /rfqs/{rfq_id}/quotes
- GET /rfqs/{rfq_id}/ranking

## CashFlows
- POST /cashflows
- GET /cashflows
- GET /cashflows/{cashflow_id}

## CashFlow Ledger (Phase 5)

### POST /cashflow/contracts/{contract_id}/settle
- Purpose: registrar evento HEDGE_CONTRACT_SETTLED e gerar duas entradas no ledger (FIXED/FLOAT).
- Request (JSON):
  ```json
  {
    "source_event_id": "uuid",
    "cashflow_date": "YYYY-MM-DD",
    "currency": "USD",
    "legs": [
      {"leg_id": "FIXED", "direction": "OUT", "amount": "100.00"},
      {"leg_id": "FLOAT", "direction": "IN", "amount": "110.00"}
    ]
  }
  ```
- Success: 201 + evento + ledger_entries.
- Errors:
  - 409: conflito de idempotência ou contrato não ativo.
  - 422: validação (currency != USD, amount <= 0, leg_id/direction inválidos).

### GET /cashflow/ledger/hedge-contracts/{contract_id}?start=YYYY-MM-DD&end=YYYY-MM-DD
- Purpose: consultar ledger por contrato e intervalo de datas.
- Errors:
  - 422: parâmetros inválidos.

### GET /cashflow/ledger?source_event_id=UUID
- Purpose: consultar ledger por evento.
- Errors:
  - 422: source_event_type inválido ou parâmetros inválidos.

## P&L (Phase 5)

### GET /pl/{entity_type}/{entity_id}?period_start=YYYY-MM-DD&period_end=YYYY-MM-DD
- Purpose: calcular P&L no período explícito.
- Errors:
  - 424: orders sem ledger autorizado.
  - 422: entidade inválida ou período inválido.
  - Note: atualmente apenas `entity_type=hedge_contract` é suportado. `entity_type=order` hard-fail (424).

### POST /pl/snapshots
- Purpose: criar snapshot append-only para (entity_type, entity_id, period_start, period_end).
- Request:
  ```json
  {
    "entity_type": "hedge_contract",
    "entity_id": "uuid",
    "period_start": "YYYY-MM-DD",
    "period_end": "YYYY-MM-DD"
  }
  ```
- Errors:
  - 409: snapshot existente com valores divergentes.
  - 424/422: conforme regras do compute_pl.
  - Note: atualmente apenas snapshots para `entity_type=hedge_contract` são suportados. `order` hard-fail (424).

### GET /pl/snapshots?entity_type=...&entity_id=...&period_start=...&period_end=...
- Purpose: obter snapshot por chave completa.
- Errors:
  - 404: snapshot não encontrado.

## Scenario (Phase 6)

### POST /scenario/what-if/run
- Purpose: executar cenário what-if **in-memory** (nenhuma persistência/audit write) com deltas explícitos e outputs determinísticos.
- Request (JSON):
  ```json
  {
    "as_of_date": "YYYY-MM-DD",
    "period_start": "YYYY-MM-DD",
    "period_end": "YYYY-MM-DD",
    "deltas": [
      {
        "delta_type": "add_unlinked_hedge_contract",
        "contract_id": "uuid",
        "quantity_mt": "10",
        "fixed_leg_side": "buy",
        "variable_leg_side": "sell",
        "fixed_price_value": "100",
        "fixed_price_unit": "USD/MT",
        "float_pricing_convention": "avg"
      },
      {
        "delta_type": "adjust_order_quantity_mt",
        "order_id": "uuid",
        "new_quantity_mt": "10"
      },
      {
        "delta_type": "add_cash_settlement_price_override",
        "symbol": "LME_ALU_CASH_SETTLEMENT_DAILY",
        "settlement_date": "YYYY-MM-DD",
        "price_usd": "120"
      }
    ]
  }
  ```
- Response: **lista fechada de outputs**
  - `commercial_exposure_snapshot`
  - `global_exposure_snapshot`
  - `mtm_snapshot`
  - `cashflow_snapshot` (analytic + baseline)
  - `pl_snapshot` (**apenas hedge_contract**, não inclui P&L de orders)
- Errors (determinísticos):
  - 422: payload inválido, período inválido, delta inválido.
  - 404: `order_id` inexistente no delta `adjust_order_quantity_mt`.
  - 409: colisão de `contract_id` virtual com contrato real; `fixed_leg_side`/`variable_leg_side` inválidos; MTM não definido (e.g., contrato sem entry_price, ordem sem avg_entry_price/pricing_convention elegível); conflitos de exposição (residual negativo) ou preço ambíguo.
  - 424: preço D-1 ausente para o símbolo padrão (sem fallback).
- Declaração explícita: **no persistence** (nenhuma gravação em tabela/snapshot/ledger).

## Audit (Phase 7)

### GET /audit/events?entity_type=...&entity_id=...&start=...&end=...&cursor=...&limit=...
- Purpose: consultar eventos de auditoria (append-only) por filtros determinísticos.
- Ordering: ascendente por `timestamp_utc`, depois `id`.
- Errors:
  - 422: filtros inválidos.
