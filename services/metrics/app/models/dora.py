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
    level: str = "unknown"
    trend: list[DORATrendPoint]


class DeploymentEventRequest(BaseModel):
    repo: str
    sha: str
    deployed_at: str
    success: bool = True


class ChangeEventRequest(BaseModel):
    repo: str
    sha: str
    first_commit_at: str
    merged_at: str | None = None
    deployed_at: str | None = None


class IncidentEventRequest(BaseModel):
    repo: str
    detected_at: str
    resolved_at: str | None = None
    caused_by_sha: str | None = None
    severity: str = "medium"


class EventResponse(BaseModel):
    id: str
    status: str = "created"


class EventListResponse(BaseModel):
    events: list[dict]
    total: int
