Prompt Completo de Implementação — Backend Phases 7-12
=====================================================

Utilize este documento como **especificação determinística** para executar as fases finais do backend do Hedge Control Platform.  
Cada fase deve gerar um *Execution Report* independente contendo: arquivos afetados, regras de governança aplicadas, antes/depois, evidência de testes e motivo de qualquer decisão de desenho.

----------------------------------------------------------------
PHASE 7 — Audit Trail & Evidence APIs
----------------------------------------------------------------
1. **Modelo & Migração**
   • Nova tabela `audit_events` (append-only)  
   ```
   id UUID (PK)                • timestamp_utc TIMESTAMP(timezone)  
   entity_type TEXT            • entity_id UUID  
   event_type TEXT             • payload JSONB  
   checksum CHAR(64)           • signature BYTEA  -- future use
   ```
   • Alembic revision `015_phase7_audit_events_table.py`

2. **Service**
   • `AuditTrailService.record(event_obj)`  
   • Calcula `checksum = sha256(payload_raw)`  
   • Insere linha; nenhuma atualização ou delete permitido (DB constraint).

3. **FastAPI Dependency**
   • Wrapper `audit_event(entity_type, entity_id, event_type)`  
   • Usado em **TODAS** rotas mutativas existentes (`orders`, `contracts`, etc.)  
   • Payload = request body bruto serializado (sem transformação).

4. **Endpoints**
   • `GET /audit/events` — filtros: `entity_type`, `entity_id`, `start`, `end`, paginação cursor.  
   • Response é **somente leitura**, ordenado asc por timestamp.

5. **Tests**
   • `test_audit_event_insert_idempotent.py` — id igual → 409  
   • `test_audit_query_filters.py` — combinações de filtros determinísticas.

----------------------------------------------------------------
PHASE 8 — Authentication / Authorization
----------------------------------------------------------------
1. **JWT Validation**
   • Dep `python-jose[cryptography]`  
   • Settings: `JWT_ISSUER`, `JWT_AUDIENCE`, `JWKS_URL`  
   • Function `get_current_user()` + cache de chaves 5 min.

2. **RBAC**
   • Roles: `trader`, `risk_manager`, `auditor`  
   • Mapping tabela `user_roles` (many-to-many) ou claims `roles` no token.

3. **Route Protection**
   • Decorator `@require_role("role_name")`  
   • Matriz de permissões:  
     – Mutative endpoints → `trader`  
     – Read risk metrics → `risk_manager`, `auditor`  
     – Audit API → `auditor`

4. **Tests**
   • `test_auth_invalid_token.py` — 401  
   • `test_rbac_forbidden.py` — 403 quando role ausente.

----------------------------------------------------------------
PHASE 9 — Operational Observability
----------------------------------------------------------------
1. **Logging**
   • `structlog` JSON renderer, key `trace_id` propagado via header `X-Trace-Id` (gerar se ausente).  
   • Log sample verificado em test.

2. **Metrics**
   • Add `prometheus_fastapi_instrumentator`: default buckets, endpoint `/metrics`.  
   • Custom counter `audit_events_total`, histogram `request_latency_seconds`.

3. **Health Endpoints**
   • `/health` (always 200)  
   • `/ready` (200 somente se DB e JWKS acessíveis).

----------------------------------------------------------------
PHASE 10 — OpenAPI Contract Hardening
----------------------------------------------------------------
1. **Generate Spec**
   ```
   python -m scripts.export_openapi > docs/api/openapi_v1.json
   ```
2. **CI Step**
   • On PR, run `swagger-diff` vs last `main` — breaking change => fail.

----------------------------------------------------------------
PHASE 11 — Performance & Stress Validation
----------------------------------------------------------------
1. **Locust Scenarios**
   • Scenario A: 10 k ledger entries fetch  
   • Scenario B: What-If with 1 k deltas  

2. **Success Criteria**
   • p95 latency < 500 ms for Scenario A  
   • Scenario B completes < 5 s  

3. **Tuning**
   • Add indices, batch queries, `asyncpg` pool tuning as needed.  
   • Record all changes in Execution Report.

----------------------------------------------------------------
PHASE 12 — Deployment Artefacts
----------------------------------------------------------------
1. **Docker**
   • Multi-stage: `python:3.11-slim` builder → runtime image < 150 MB  
   • Non-root user, `uvicorn gunicorn` worker class.

2. **Helm Chart**
   • Values: `image`, `db_url`, `jwt`, resource limits, replicas.  
   • Liveness/readiness probes wired to `/health` & `/ready`.

3. **CI Pipeline (GitHub Actions)**
   • Stages: lint → tests → build-image → push → helm-lint → helm-dry-run.

----------------------------------------------------------------
CONSTITUTIONAL GUARANTEES
----------------------------------------------------------------
• **No silent fallback** — every failure path returns explicit 4xx/5xx.  
• **Deterministic ordering** for audit retrieval.  
• **Immutability enforced** via DB constraints & checksum signature.  
• **No economic inference** introduced in these phases.

----------------------------------------------------------------
GATES DE SAÍDA
----------------------------------------------------------------
Phase considered complete only when:
1. All new unit/integration tests pass (`pytest -q`).  
2. Updated `docs/api/endpoints.md` lists new endpoints.  
3. Execution Report reviewed & approved.  
4. For Phase 12: successful helm dry-run output attached.

----------------------------------------------------------------
BLOQUEADORES
----------------------------------------------------------------
• Corporate JWKS URL & role taxonomy (Phase 8)  
• Prometheus / Grafana cluster availability (Phase 9)  
• Docker registry & k8s namespace (Phase 12)  
If absent → **`BLOCKED — requires governance decision`**

Siga estas instruções **à risca** para cada fase sequencialmente.  
Qualquer ambiguidade deve interromper o avanço com a mensagem acima.