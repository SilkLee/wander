from fastapi import APIRouter
from app.models.dora import DORAResponse

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/dora", response_model=DORAResponse)
async def get_dora_metrics() -> DORAResponse:
    return DORAResponse(
        deployment_frequency=3.2,
        lead_time_hours=24.5,
        change_failure_rate=0.12,
        mttr_hours=1.8,
        trend="improving",
    )
