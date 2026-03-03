import time
import uuid
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi.errors import RateLimitExceeded

from app.core.auth import get_auth_settings
from app.core.database import engine
from app.core.logging import configure_logging, get_logger
from app.core.metrics import request_latency_seconds
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.tasks.scheduler import start_scheduler, stop_scheduler

from app.api.routes import (
    audit,
    cashflow,
    cashflow_ledger,
    contracts,
    counterparties,
    deals,
    exposures,
    finance_pipeline,
    hedges,
    linkages,
    mtm,
    orders,
    pl,
    rfqs,
    scenario,
    webhooks,
    westmetall,
)

configure_logging()
logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Hedge Control Platform",
    version=os.getenv("APP_VERSION", "0.8.0"),
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

cors_allow_origins_raw = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
if cors_allow_origins_raw:
    cors_allow_origins = [
        origin.strip() for origin in cors_allow_origins_raw.split(",") if origin.strip()
    ]
else:
    cors_allow_origins = [
        "http://localhost:5173",
        "http://localhost:8080",
        "https://happy-sand-0b5701c0f.1.azurestaticapps.net",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

    if os.getenv("JWT_ISSUER"):
        try:
            settings = get_auth_settings()
            response = httpx.get(settings.jwks_url, timeout=5.0)
            response.raise_for_status()
        except Exception as exc:  # pragma: no cover
            logger.error("readiness_jwks_failed", error=str(exc))
            raise HTTPException(status_code=503, detail="jwks_unavailable") from exc

    return {"status": "ready"}


app.include_router(
    counterparties.router, prefix="/counterparties", tags=["Counterparties"]
)
app.include_router(orders.router, prefix="/orders", tags=["Orders"])
app.include_router(exposures.router, prefix="/exposures", tags=["Exposures"])
app.include_router(hedges.router, prefix="/hedges", tags=["Hedges"])
app.include_router(deals.router, prefix="/deals", tags=["Deals"])
app.include_router(contracts.router, prefix="/contracts", tags=["Contracts"])
app.include_router(linkages.router, prefix="/linkages", tags=["Linkages"])
app.include_router(rfqs.router, prefix="/rfqs", tags=["RFQs"])
app.include_router(cashflow.router, prefix="/cashflow", tags=["CashFlow"])
app.include_router(cashflow_ledger.router, prefix="/cashflow", tags=["CashFlowLedger"])
app.include_router(pl.router, prefix="/pl", tags=["P&L"])
app.include_router(scenario.router, prefix="/scenario", tags=["Scenario"])
app.include_router(audit.router, prefix="/audit", tags=["Audit"])
app.include_router(
    westmetall.router, prefix="/market-data/westmetall", tags=["MarketData"]
)
app.include_router(mtm.router, prefix="/mtm", tags=["MTM"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(
    finance_pipeline.router, prefix="/finance/pipeline", tags=["FinancePipeline"]
)
