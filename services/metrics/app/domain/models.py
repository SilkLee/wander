from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import DORALevel


@dataclass(frozen=True)
class DeploymentEvent:
    id: str
    repository: str
    commit_sha: str
    deployed_at: datetime
    success: bool


@dataclass(frozen=True)
class ChangeEvent:
    id: str
    repository: str
    commit_sha: str
    first_commit_at: datetime
    merged_at: datetime | None = None
    deployed_at: datetime | None = None


@dataclass(frozen=True)
class IncidentEvent:
    id: str
    repository: str
    detected_at: datetime
    resolved_at: datetime | None = None
    caused_by_sha: str | None = None


@dataclass(frozen=True)
class DORASnapshot:
    deployment_frequency: float
    lead_time_hours: float
    change_failure_rate: float
    mttr_hours: float
    level: DORALevel
    period_start: datetime
    period_end: datetime
