from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.api.dependencies.audit import audit_event, mark_audit_success
from app.models.contracts import HedgeClassification, HedgeContract, HedgeContractStatus, HedgeLegSide
from app.schemas.contracts import (
    HedgeContractCreate,
    HedgeContractRead,
    HedgeLegPriceType,
    HedgeLegSide,
)

router = APIRouter()


@router.post("/hedge", response_model=HedgeContractRead, status_code=status.HTTP_201_CREATED)
def create_hedge_contract(
    payload: HedgeContractCreate,
    request: Request,
    _: None = Depends(
        audit_event(
            entity_type="hedge_contract",
            event_type="created",
        )
    ),
    session: Session = Depends(get_session),
) -> HedgeContractRead:
    fixed_leg = next(leg for leg in payload.legs if leg.price_type == HedgeLegPriceType.fixed)
    variable_leg = next(leg for leg in payload.legs if leg.price_type == HedgeLegPriceType.variable)
    classification = (
        HedgeClassification.long if fixed_leg.side == HedgeLegSide.buy else HedgeClassification.short
    )
    contract = HedgeContract(
        commodity=payload.commodity,
        quantity_mt=payload.quantity_mt,
        fixed_leg_side=HedgeLegSide(fixed_leg.side.value),
        variable_leg_side=HedgeLegSide(variable_leg.side.value),
        classification=classification,
        status=HedgeContractStatus.active,
    )
    session.add(contract)
    session.commit()
    session.refresh(contract)
    mark_audit_success(request, contract.id)
    request.state.audit_commit()
    return HedgeContractRead.model_validate(contract)


@router.get("/hedge/{contract_id}", response_model=HedgeContractRead)
def get_hedge_contract(contract_id: UUID, session: Session = Depends(get_session)) -> HedgeContractRead:
    contract = session.get(HedgeContract, contract_id)
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hedge contract not found")
    return HedgeContractRead.model_validate(contract)
