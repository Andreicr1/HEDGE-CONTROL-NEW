# PHASE_6_STEP_2_EXECUTION_REPORT.md

## Scope
- Harden Scenario What-if invariantes: determinismo, validações e consistência.
- Garantir falhas determinísticas para deltas inválidos.
- Manter P&L do cenário restrito a hedge_contracts.

## Actions Taken
- Removido uso de timestamps dinâmicos (derivados de as_of_date).
- Validações adicionadas para colisão de contract_id e sides inválidos.
- adjust_order_quantity_mt agora valida existência do order_id (404).
- Testes adicionados para determinismo e validações de delta.
- Rodado pytest para evidência do gate.

## Files/Modules Affected
- backend/app/services/scenario_whatif_service.py
- backend/tests/test_scenario_whatif_run.py

## Governance Rules Enforced
- Determinismo: mesma entrada → mesma saída.
- Hard-fail: deltas inválidos retornam 409/404/422.
- Sem fallback/heurística; ausência de preço segue 424.
- P&L do cenário apenas para hedge_contracts.

## Gate Evidence
Command:
```
Set-Location D:\Projetos\Hedge-Control-New\backend
D:/Projetos/Hedge-Control-New/.venv/Scripts/python.exe -m pytest -q
```
Output:
```
85 passed, 3 warnings in 7.07s
```
Warnings:
- starlette.formparsers PendingDeprecationWarning (python_multipart)
- PydanticDeprecatedSince20 class-based config
- Pydantic v2 orm_mode renamed to from_attributes

## Final Constraints
- Não persistir dados nem adicionar deltas/outputs.

READY FOR REVIEW