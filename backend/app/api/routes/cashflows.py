from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.schemas.cashflow import CashFlowCreate, CashFlowRead
from app.api.dependencies.audit import audit_event

router = APIRouter()


@router.post("", response_model=CashFlowRead, status_code=status.HTTP_201_CREATED)
def create_cashflow(
    payload: CashFlowCreate,
    request: Request,
    _: None = Depends(
        audit_event(
            entity_type="cashflow",
            event_type="created",
        )
    ),
) -> CashFlowRead:
    del payload
    del request
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not Implemented")


@router.get("", response_model=list[CashFlowRead])
def list_cashflows() -> list[CashFlowRead]:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not Implemented")


@router.get("/{cashflow_id}", response_model=CashFlowRead)
def get_cashflow(_: str) -> CashFlowRead:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not Implemented")
