from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from fastapi import APIRouter, Depends, Query

from app.domain.calculator import calculate_dora
from app.domain.models import ChangeEvent, DeploymentEvent, IncidentEvent
from app.infrastructure.repository import DORARepository, InMemoryDORARepository
from app.models.dora import DORAResponse, DORATrendPoint

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/metrics", tags=["metrics"])


def _has_database() -> bool:
    return bool(os.getenv("DATABASE_URL", ""))


@lru_cache(maxsize=1)
def _get_in_memory_repo() -> InMemoryDORARepository:
    repo = InMemoryDORARepository()
    return repo


async def _get_repository():
    """Provide the appropriate repository based on DATABASE_URL availability."""
    if _has_database():
        from app.infrastructure.database import get_session

        async for session in get_session():
            yield DORARepository(session)
    else:
        yield _get_in_memory_repo()


def _seed_demo_data(repo: InMemoryDORARepository) -> None:
    """Seed the in-memory repo with sample data on first request."""
    import uuid

    now = datetime.now(timezone.utc)

    for i in range(30):
        ts = now - timedelta(days=30 - i)
        deploy_id = str(uuid.uuid4())
        repo._deployments.append(
            DeploymentEvent(
                id=deploy_id,
                repository="default",
                commit_sha=f"abc{i:04d}",
                deployed_at=ts,
                success=i % 8 != 0,
            )
        )
        repo._changes.append(
            ChangeEvent(
                id=str(uuid.uuid4()),
                repository="default",
                commit_sha=f"abc{i:04d}",
                first_commit_at=ts - timedelta(hours=18),
                merged_at=ts - timedelta(hours=2),
                deployed_at=ts,
            )
        )

    for i in range(4):
        ts = now - timedelta(days=25 - i * 7)
        repo._incidents.append(
            IncidentEvent(
                id=str(uuid.uuid4()),
                repository="default",
                detected_at=ts,
                resolved_at=ts + timedelta(hours=3),
                caused_by_sha=f"abc{i:04d}",
            )
        )


_demo_seeded = False


@router.get("/dora", response_model=DORAResponse)
async def get_dora_metrics(
    repo: str = Query("default", description="Repository name"),
    from_date: str | None = Query(None, alias="from", description="Start date ISO8601"),
    to_date: str | None = Query(None, alias="to", description="End date ISO8601"),
    repository=Depends(_get_repository),
) -> DORAResponse:
    global _demo_seeded  # noqa: PLW0603

    now = datetime.now(timezone.utc)
    start = datetime.fromisoformat(from_date) if from_date else now - timedelta(days=30)
    end = datetime.fromisoformat(to_date) if to_date else now

    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    # Seed demo data for in-memory repo on first request
    if isinstance(repository, InMemoryDORARepository) and not _demo_seeded:
        _seed_demo_data(repository)
        _demo_seeded = True

    deploys = await repository.get_deployments(repo, start, end)
    changes = await repository.get_changes(repo, start, end)
    incidents = await repository.get_incidents(repo, start, end)

    snapshot = calculate_dora(deploys, changes, incidents, start, end)

    # Build weekly trend data
    trend: list[DORATrendPoint] = []
    period = start
    while period < end:
        week_end = min(period + timedelta(days=7), end)
        week_deploys = [d for d in deploys if period <= d.deployed_at <= week_end]
        week_changes = [
            c for c in changes if c.deployed_at and period <= c.deployed_at <= week_end
        ]
        week_incidents = [i for i in incidents if period <= i.detected_at <= week_end]
        week_snap = calculate_dora(
            week_deploys, week_changes, week_incidents, period, week_end
        )
        trend.append(
            DORATrendPoint(
                timestamp=period.date().isoformat(),
                deployment_frequency=week_snap.deployment_frequency,
                lead_time=week_snap.lead_time_hours,
                change_failure_rate=week_snap.change_failure_rate,
                mttr=week_snap.mttr_hours,
            )
        )
        period = week_end

    return DORAResponse(
        deployment_frequency=snapshot.deployment_frequency,
        lead_time=snapshot.lead_time_hours,
        change_failure_rate=snapshot.change_failure_rate,
        mttr=snapshot.mttr_hours,
        level=snapshot.level.value,
        trend=trend,
    )
