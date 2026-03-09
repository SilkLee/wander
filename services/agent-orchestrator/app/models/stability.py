from pydantic import BaseModel, Field


class StabilityError(BaseModel):
    node: str = Field(description="LangGraph node name")
    error_type: str = Field(pattern="^(timeout|dependency|validation|unknown)$")
    message: str = Field(description="Short error description")
    retry_attempts: int = Field(ge=0, description="Number of retries attempted")
    degraded: bool = Field(description="Whether response was degraded")


class RetrySummary(BaseModel):
    retries: dict[str, int] = Field(default_factory=dict)
