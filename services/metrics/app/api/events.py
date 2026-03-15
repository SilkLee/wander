from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from app.models.dora import (
    ChangeEventRequest,
    DeploymentEventRequest,
    EventListResponse,
    EventResponse,
    IncidentEventRequest,
)
from app.utils import parse_iso
from app.models.dora import (
    ChangeEventRequest,
    DeploymentEventRequest,
    EventListResponse,
    EventResponse,
    IncidentEventRequest,
)

router = APIRouter(prefix="/metrics", tags=["events"])


async def _get_repository():
    """Re-use the same repository resolution logic from dora module."""
    from app.api.dora import _get_repository as get_repo

    async for repo in get_repo():
        yield repo


@router.post("/events/deployment", response_model=EventResponse)
async def record_deployment(
    request: DeploymentEventRequest,
    repository=Depends(_get_repository),
) -> EventResponse:
    deployed_at = parse_iso(request.deployed_at)
    event_id = await repository.record_deployment(
        repo=request.repo,
        sha=request.sha,
        deployed_at=deployed_at,
        success=request.success,
    )
    return EventResponse(id=event_id)


@router.post("/events/change", response_model=EventResponse)
async def record_change(
    request: ChangeEventRequest,
    repository=Depends(_get_repository),
) -> EventResponse:
    first_commit_at = parse_iso(request.first_commit_at)
    merged_at = None
    if request.merged_at:
        merged_at = parse_iso(request.merged_at)
    deployed_at = None
    if request.deployed_at:
        deployed_at = parse_iso(request.deployed_at)
    event_id = await repository.record_change(
        repo=request.repo,
        sha=request.sha,
        first_commit_at=first_commit_at,
        merged_at=merged_at,
        deployed_at=deployed_at,
    )
    return EventResponse(id=event_id)


@router.post("/events/incident", response_model=EventResponse)
async def record_incident(
    request: IncidentEventRequest,
    repository=Depends(_get_repository),
) -> EventResponse:
    detected_at = parse_iso(request.detected_at)
    resolved_at = None
    if request.resolved_at:
        resolved_at = parse_iso(request.resolved_at)
    event_id = await repository.record_incident(
        repo=request.repo,
        detected_at=detected_at,
        resolved_at=resolved_at,
        caused_by_sha=request.caused_by_sha,
        severity=request.severity,
    )
    return EventResponse(id=event_id)


@router.get("/events", response_model=EventListResponse)
async def list_events(
    repo: str = Query("default"),
    event_type: str | None = Query(None, alias="type"),
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
    repository=Depends(_get_repository),
) -> EventListResponse:
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    start = parse_iso(from_date) if from_date else now - timedelta(days=30)
    end = parse_iso(to_date) if to_date else now

    events: list[dict] = []

    if event_type is None or event_type == "deployment":
        deploys = await repository.get_deployments(repo, start, end)
        for d in deploys:
            events.append(
                {
                    "type": "deployment",
                    "id": d.id,
                    "repository": d.repository,
                    "commit_sha": d.commit_sha,
                    "deployed_at": d.deployed_at.isoformat(),
                    "success": d.success,
                }
            )

    if event_type is None or event_type == "change":
        changes = await repository.get_changes(repo, start, end)
        for c in changes:
            events.append(
                {
                    "type": "change",
                    "id": c.id,
                    "repository": c.repository,
                    "commit_sha": c.commit_sha,
                    "first_commit_at": c.first_commit_at.isoformat(),
                    "merged_at": c.merged_at.isoformat() if c.merged_at else None,
                    "deployed_at": c.deployed_at.isoformat() if c.deployed_at else None,
                }
            )

    if event_type is None or event_type == "incident":
        incidents = await repository.get_incidents(repo, start, end)
        for i in incidents:
            events.append(
                {
                    "type": "incident",
                    "id": i.id,
                    "repository": i.repository,
                    "detected_at": i.detected_at.isoformat(),
                    "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
                    "caused_by_sha": i.caused_by_sha,
                }
            )

    return EventListResponse(events=events, total=len(events))
