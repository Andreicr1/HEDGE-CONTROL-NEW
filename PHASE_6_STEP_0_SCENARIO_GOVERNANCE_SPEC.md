# PHASE_6_STEP_0_SCENARIO_GOVERNANCE_SPEC.md

## Scope
- Define governança do What-if (Scenario) exclusivamente in-memory.
- Sem persistência, sem timeline, sem audit writes.
- Usa dados autoritativos + deltas explícitos.
- Não altera estado econômico oficial (backend permanece autoridade).

## What-if Does
- Executa projeções determinísticas com dados oficiais + deltas explícitos.
- Retorna resultados calculados (exposures, MTM, CashFlow, P&L) em memória.

## What-if Does NOT Do
- Não persiste dados.
- Não cria ou atualiza entidades oficiais.
- Não registra snapshots, eventos ou ledger.
- Não aplica fallback ou heurística.

## Outputs (Closed List)
- commercial_exposure_snapshot (active, passive, net)
- global_exposure_snapshot (active, passive, net)
- mtm_snapshot (para hedge_contracts e orders afetados)
- cashflow_snapshot (analytic + baseline view)
- pl_snapshot (realized/unrealized no período explícito)

## Allowed Deltas (Closed List)

### delta: add_unlinked_hedge_contract
- Fields:
  - contract_id (UUID, required)
  - quantity_mt (Decimal > 0)
  - fixed_leg_side (buy|sell)
  - variable_leg_side (buy|sell)
  - fixed_price_value (Decimal > 0)
  - fixed_price_unit ("USD/MT")
  - float_pricing_convention (string, required)
- Invariants:
  - fixed_leg_side determines classification (long/short) deterministically.
  - Não gera linkage.
  - MT positivo.
- Effect:
  - Adiciona exposição global (hedge long/short unlinked).
  - Participa de MTM e P&L no cenário.

### delta: adjust_order_quantity_mt
- Fields:
  - order_id (UUID, required)
  - new_quantity_mt (Decimal > 0)
- Invariants:
  - Aplica-se somente a orders existentes.
  - Mantém pricing convention original.
- Effect:
  - Recalcula exposure comercial e global (se order variável).

### delta: add_cash_settlement_price_override
- Fields:
  - symbol (string, required)
  - settlement_date (date, required)
  - price_usd (Decimal > 0)
- Invariants:
  - Override explícito por símbolo + data.
  - Não persiste no banco.
- Effect:
  - Substitui preço D-1 para MTM/CashFlow/P&L no cenário.

## Price Source in Scenario (Binding)
- Default: Cash Settlement D-1 (series oficial) para MTM/CashFlow/P&L.
- Override: permitido somente via delta add_cash_settlement_price_override.
- Ausência de preço: hard-fail do cenário (HTTP 424).

## Execution Rules
- Inputs: payload de cenário com datas de período explícitas + lista de deltas.
- Outputs: estrutura determinística com snapshots calculados em memória.
- Determinismo: mesma entrada → mesma saída.

## Proposed Endpoint (Design Only)
- POST /scenario/what-if/run
- Sem persistência, sem "save scenario", sem histórico.

## BLOCKERS
- Definição final dos outputs obrigatórios (lista fechada) precisa aprovação.
- Lista de deltas permitidos precisa aprovação formal (inclusive nomes e campos).
- Regras de cálculo para CashFlow/P&L em cenário precisam confirmação (ex.: períodos padrão).

BLOCKED — requires governance decision