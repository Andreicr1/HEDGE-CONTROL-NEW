# PHASE_5_STEP_4_EXECUTION_REPORT.md

## Scope
- Documentar contratos de API para Ledger e P&L.
- Consolidar invariantes (idempotência, 409/424/422) e schemas públicos.
- Garantir alinhamento entre documentação, schemas e comportamento real.

## Actions Taken
- Atualizado docs/api/endpoints.md com endpoints de Ledger e P&L.
- Atualizado schemas/cashflow.schema.json com definições de Ledger.
- Adicionado schemas/pl.schema.json para snapshots de P&L.
- Corrigido alinhamento dos schemas públicos com o comportamento atual do backend (P&L snapshot não suportado para `order`; ledger usa `hedge_contract_id`).
- Rodado pytest para evidência do gate.

## Files/Modules Affected
- docs/api/endpoints.md
- schemas/cashflow.schema.json
- schemas/pl.schema.json

## Governance Rules Enforced
- Append-only e idempotência explicitadas na documentação.
- Hard-fail para orders sem ledger (424/422) documentado.
- Sem fallback/heurística/FX/accrual; eventos restritos a HEDGE_CONTRACT_SETTLED.

## Gate Evidence
Command:
```
Set-Location D:\Projetos\Hedge-Control-New\backend
D:/Projetos/Hedge-Control-New/.venv/Scripts/python.exe -m pytest -q
```
Output:
```
75 passed, 3 warnings in 6.96s
```
Warnings:
- starlette.formparsers PendingDeprecationWarning (python_multipart)
- PydanticDeprecatedSince20 class-based config
- Pydantic v2 orm_mode renamed to from_attributes

## Acceptance Criteria
- Documentação descreve contratos e falhas determinísticas.
- Schemas públicos alinhados ao comportamento real.
- pytest -q passa.

READY FOR REVIEW