# PHASE_5_STEP_3_EXECUTION_REPORT.md

## Scope
- Persistir snapshots de P&L refletindo realized_pl do CashFlow Ledger (HEDGE_CONTRACT_SETTLED).
- Garantir idempotência/append-only e conflito em divergência.
- Expor criação e leitura via endpoints existentes sem fallback.

## Actions Taken
- Validada a chamada de compute_pl no snapshot service (realized do ledger).
- Criados testes para snapshot com realized_pl, idempotência, conflito e hard-fail para orders.
- Rodado pytest para evidência do gate.

## Files/Modules Affected
- backend/tests/test_pl_snapshot_realized_from_ledger.py

## Governance Rules Enforced
- Append-only: snapshot não é atualizado ou deletado.
- Idempotência: mesmos inputs retornam o snapshot existente.
- Hard-fail: orders sem ledger autorizado retornam 424/422.
- Sem fallback/heurística/FX/accrual.

## Gate Evidence
Command:
```
Set-Location D:\Projetos\Hedge-Control-New\backend
D:/Projetos/Hedge-Control-New/.venv/Scripts/python.exe -m pytest -q
```
Output:
```
75 passed, 3 warnings in 7.26s
```
Warnings:
- starlette.formparsers PendingDeprecationWarning (python_multipart)
- PydanticDeprecatedSince20 class-based config
- Pydantic v2 orm_mode renamed to from_attributes

## Acceptance Criteria
- Snapshot persistido reflete realized do ledger (hedge_contract).
- Idempotência e conflito (409) comprovados em teste.
- pytest -q passa.

READY FOR REVIEW