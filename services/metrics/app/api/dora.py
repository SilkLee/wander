from fastapi import APIRouter
from app.models.dora import DORAResponse

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/dora", response_model=DORAResponse)
async def get_dora_metrics() -> DORAResponse:
    return DORAResponse(
        deployment_frequency=1.2,
        lead_time=18.4,
        change_failure_rate=0.12,
        mttr=3.6,
        trend=[
            {
                "timestamp": "2026-03-01",
                "deployment_frequency": 1.1,
                "lead_time": 20.0,
                "change_failure_rate": 0.1,
                "mttr": 4.0,
            }
        ],
    )
