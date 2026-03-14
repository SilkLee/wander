from pydantic import BaseModel


class DORATrendPoint(BaseModel):
    timestamp: str
    deployment_frequency: float
    lead_time: float
    change_failure_rate: float
    mttr: float


class DORAResponse(BaseModel):
    deployment_frequency: float
    lead_time: float
    change_failure_rate: float
    mttr: float
    trend: list[DORATrendPoint]
