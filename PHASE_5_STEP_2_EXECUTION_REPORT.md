# PHASE_5_STEP_2_EXECUTION_REPORT.md

## Scope
- Atualiza P&L para derivar realized_pl exclusivamente do CashFlow Ledger (HEDGE_CONTRACT_SETTLED).
- Mantém unrealized_mtm conforme regra D-1 para contratos ativos.
- Hard-fail para orders sem ledger de settlement.

## Actions Taken
- Atualizado serviço de cálculo de P&L para somar entradas do ledger no período.
- Adicionada regra de sinal (IN positivo, OUT negativo).
- Hard-fail para entity_type="order" sem ledger autorizado.
- Ajustado unrealized_mtm para contratos não ativos retornar 0.
- Atualizados testes de P&L para validar realized_pl, idempotência e hard-fail.
- Rodado pytest para evidência do gate.

## Files/Modules Affected
- backend/app/services/pl_calculation_service.py
- backend/tests/test_pl_calculation_service.py

## Governance Rules Enforced
- P&L deriva de cashflow realizado (ledger) conforme Constituição.
- Append-only e idempotente: sem update/delete de snapshots.
- Hard-fail para orders sem ledger autorizado.
- Sem heurísticas/fallbacks/FX/accrual.

## Gate Evidence
Command:
```
Set-Location D:\Projetos\Hedge-Control-New\backend
D:/Projetos/Hedge-Control-New/.venv/Scripts/python.exe -m pytest -q
```
Output:
```
72 passed, 3 warnings in 7.00s
```
Warnings:
- starlette.formparsers PendingDeprecationWarning (python_multipart)
- PydanticDeprecatedSince20 class-based config
- Pydantic v2 orm_mode renamed to from_attributes

## Final Constraints
- Não adicionar eventos adicionais além de HEDGE_CONTRACT_SETTLED.
- Não implementar contabilidade, accrual, FX ou BRL.

READY FOR REVIEW