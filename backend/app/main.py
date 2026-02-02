from fastapi import FastAPI

from app.api.routes import audit, cashflow, cashflow_ledger, cashflows, contracts, exposures, linkages, mtm, orders, pl, rfqs, scenario, westmetall

app = FastAPI(title="Hedge Control Platform", version="0.3.0-phase3-step2")

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
