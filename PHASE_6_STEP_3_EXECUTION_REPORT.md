# PHASE 6 — STEP 3 — Scenario What-if (contrato público + documentação + schema)

## Scope
- Consolidar o contrato público do endpoint de cenário what-if com JSON Schema explícito.
- Garantir restrições determinísticas (lista fechada de deltas/outputs, period_end >= period_start).
- Executar gate de testes completo e registrar evidências.

## Actions Taken
1. Atualizada a documentação de endpoints para incluir o contrato do cenário What-if (in-memory, lista fechada de deltas/outputs, erros determinísticos).
2. Ajustado o schema público `schemas/scenario.schema.json` para explicitar a restrição `period_end >= period_start` no request.
3. Executado o gate completo de testes (`pytest -q`) no backend.

## Files / Modules Affected
- `schemas/scenario.schema.json`
- `docs/api/endpoints.md`
- `PHASE_6_STEP_3_EXECUTION_REPORT.md`

## Governance Rules Enforced
- **No persistence**: o schema mantém cenário como execução in-memory (sem writes).
- **Closed list**: deltas e outputs permanecem fechados e explícitos (sem extensões futuras).
- **Hard-fail**: restrições determinísticas documentadas/implícitas no schema (ex.: período inválido, preço ausente → 424).

## Gate Evidence

Command:
```
Set-Location D:\Projetos\Hedge-Control-New\backend
D:/Projetos/Hedge-Control-New/.venv/Scripts/python.exe -m pytest -q
```

Output:
```
...................................................................................                                [100%]
==================================================== warnings summary =====================================================
..\.venv\Lib\site-packages\starlette\formparsers.py:12
  D:\Projetos\Hedge-Control-New\.venv\Lib\site-packages\starlette\formparsers.py:12: PendingDeprecationWarning: Please use `import python_multipart` instead.
    import multipart..\.venv\Lib\site-packages\pydantic\_internal\_config.py:323
  D:\Projetos\Hedge-Control-New\.venv\Lib\site-packages\pydantic\_internal\_config.py:323: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.11/migration/
    warnings.warn(DEPRECATION_MESSAGE, DeprecationWarning)..\.venv\Lib\site-packages\pydantic\_internal\_config.py:373
  D:\Projetos\Hedge-Control-New\.venv\Lib\site-packages\pydantic\_internal\_config.py:373: UserWarning: Valid config keys have changed in V2:
  * 'orm_mode' has been renamed to 'from_attributes'
    warnings.warn(message, UserWarning)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
85 passed, 3 warnings in 6.35s
```

## Notes
- Nenhuma migração ou alteração de runtime foi necessária.
- Schema público mantém P&L de cenário restrito a `hedge_contract` apenas, em linha com o comportamento atual.