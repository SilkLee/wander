from pydantic import BaseModel
from typing import Literal


class DORAResponse(BaseModel):
    deployment_frequency: float
    lead_time_hours: float
    change_failure_rate: float
    mttr_hours: float
    trend: Literal["improving", "stable", "declining"]
