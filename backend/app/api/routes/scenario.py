from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.scenario import ScenarioWhatIfRunRequest, ScenarioWhatIfRunResponse
from app.services.scenario_whatif_service import run_what_if


router = APIRouter()


@router.post("/what-if/run", response_model=ScenarioWhatIfRunResponse, status_code=status.HTTP_200_OK)
def run_what_if_scenario(
    payload: ScenarioWhatIfRunRequest,
    session: Session = Depends(get_session),
) -> ScenarioWhatIfRunResponse:
    return run_what_if(session, payload)