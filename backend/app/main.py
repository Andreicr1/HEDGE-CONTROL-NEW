import time
import uuid

import httpx
from fastapi import FastAPI, HTTPException, Request
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.auth import get_auth_settings
from app.core.database import engine
from app.core.logging import configure_logging, get_logger
from app.core.metrics import request_latency_seconds

from app.api.routes import audit, cashflow, cashflow_ledger, cashflows, contracts, exposures, linkages, mtm, orders, pl, rfqs, scenario, westmetall

configure_logging()
logger = get_logger()

app = FastAPI(title="Hedge Control Platform", version="0.3.0-phase3-step2")

instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app, endpoint="/metrics")

@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
    request.state.trace_id = trace_id
    start_time = time.monotonic()
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    if not request.url.path.startswith("/metrics"):
        duration = max(time.monotonic() - start_time, 0.0)
        request_latency_seconds.labels(
            method=request.method,
            path=request.url.path,
            status=str(response.status_code),
        ).observe(duration)
        logger.info(
            "request",
            trace_id=trace_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        )
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def readiness() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
    except Exception as exc:  # pragma: no cover - explicit readiness failure path
        logger.error("readiness_db_failed", error=str(exc))
        raise HTTPException(status_code=503, detail="db_unavailable") from exc

    try:
        settings = get_auth_settings()
        response = httpx.get(settings.jwks_url, timeout=5.0)
        response.raise_for_status()
    except Exception as exc:  # pragma: no cover - explicit readiness failure path
        logger.error("readiness_jwks_failed", error=str(exc))
        raise HTTPException(status_code=503, detail="jwks_unavailable") from exc

    return {"status": "ready"}

app.include_router(orders.router, prefix="/orders", tags=["Orders"])
app.include_router(exposures.router, prefix="/exposures", tags=["Exposures"])
app.include_router(contracts.router, prefix="/contracts", tags=["Contracts"])
app.include_router(linkages.router, prefix="/linkages", tags=["Linkages"])
app.include_router(rfqs.router, prefix="/rfqs", tags=["RFQs"])
app.include_router(cashflows.router, prefix="/cashflows", tags=["CashFlows"])
app.include_router(cashflow.router, prefix="/cashflow", tags=["CashFlow"])
app.include_router(cashflow_ledger.router, prefix="/cashflow", tags=["CashFlowLedger"])
app.include_router(pl.router, prefix="/pl", tags=["P&L"])
app.include_router(scenario.router, prefix="/scenario", tags=["Scenario"])
app.include_router(audit.router, prefix="/audit", tags=["Audit"])
app.include_router(westmetall.router, prefix="/market-data/westmetall", tags=["MarketData"])
app.include_router(mtm.router, prefix="/mtm", tags=["MTM"])
