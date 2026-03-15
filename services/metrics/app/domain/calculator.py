from __future__ import annotations

from datetime import datetime
from statistics import median

from app.domain.enums import DORALevel
from app.domain.models import ChangeEvent, DeploymentEvent, DORASnapshot, IncidentEvent


def calc_deployment_frequency(
    events: list[DeploymentEvent], start: datetime, end: datetime
) -> float:
    """Successful deploys per day in the period."""
    successful = [e for e in events if e.success and start <= e.deployed_at <= end]
    days = max((end - start).total_seconds() / 86400, 1)
    return round(len(successful) / days, 2)


def calc_lead_time(changes: list[ChangeEvent], start: datetime, end: datetime) -> float:
    """Median hours from first commit to deployment."""
    deltas: list[float] = []
    for c in changes:
        if c.deployed_at and c.first_commit_at and start <= c.deployed_at <= end:
            hours = (c.deployed_at - c.first_commit_at).total_seconds() / 3600
            deltas.append(hours)
    return round(median(deltas), 1) if deltas else 0.0


def calc_change_failure_rate(
    deploys: list[DeploymentEvent], incidents: list[IncidentEvent]
) -> float:
    """Ratio of incidents to deployments (0.0-1.0)."""
    if not deploys:
        return 0.0
    return round(len(incidents) / len(deploys), 3)


def calc_mttr(incidents: list[IncidentEvent]) -> float:
    """Mean hours to recovery (detected_at -> resolved_at)."""
    resolved = [i for i in incidents if i.resolved_at]
    if not resolved:
        return 0.0
    total = sum(
        (i.resolved_at - i.detected_at).total_seconds() / 3600  # type: ignore[operator]
        for i in resolved
    )
    return round(total / len(resolved), 1)


def classify_level(df: float, lt: float, cfr: float, mttr: float) -> DORALevel:
    """Classify per Google DORA benchmarks."""
    if df >= 1.0 and lt < 24 and cfr < 0.05 and mttr < 1:
        return DORALevel.ELITE
    if df >= 0.14 and lt < 168 and cfr < 0.15 and mttr < 24:
        return DORALevel.HIGH
    if df >= 0.033 and lt < 720 and cfr < 0.30 and mttr < 168:
        return DORALevel.MEDIUM
    return DORALevel.LOW


def calculate_dora(
    deploys: list[DeploymentEvent],
    changes: list[ChangeEvent],
    incidents: list[IncidentEvent],
    start: datetime,
    end: datetime,
) -> DORASnapshot:
    """Calculate all four DORA metrics and classify the overall level."""
    df = calc_deployment_frequency(deploys, start, end)
    lt = calc_lead_time(changes, start, end)
    cfr = calc_change_failure_rate(deploys, incidents)
    mttr_val = calc_mttr(incidents)
    level = classify_level(df, lt, cfr, mttr_val)
    return DORASnapshot(
        deployment_frequency=df,
        lead_time_hours=lt,
        change_failure_rate=cfr,
        mttr_hours=mttr_val,
        level=level,
        period_start=start,
        period_end=end,
    )
