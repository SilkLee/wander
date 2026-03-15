from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import ChangeEvent, DeploymentEvent, IncidentEvent


class DORARepository:
    """PostgreSQL-backed repository using raw SQL queries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_deployments(
        self, repo: str, start: datetime, end: datetime
    ) -> list[DeploymentEvent]:
        result = await self._session.execute(
            text(
                "SELECT id, repository, commit_sha, deployed_at, success "
                "FROM deployment_events "
                "WHERE repository = :repo AND deployed_at BETWEEN :start AND :end "
                "ORDER BY deployed_at DESC"
            ),
            {"repo": repo, "start": start, "end": end},
        )
        return [
            DeploymentEvent(
                id=str(row.id),
                repository=row.repository,
                commit_sha=row.commit_sha,
                deployed_at=row.deployed_at,
                success=row.success,
            )
            for row in result.fetchall()
        ]

    async def get_changes(
        self, repo: str, start: datetime, end: datetime
    ) -> list[ChangeEvent]:
        result = await self._session.execute(
            text(
                "SELECT id, repository, commit_sha, first_commit_at, merged_at, deployed_at "
                "FROM change_events "
                "WHERE repository = :repo AND first_commit_at BETWEEN :start AND :end "
                "ORDER BY first_commit_at DESC"
            ),
            {"repo": repo, "start": start, "end": end},
        )
        return [
            ChangeEvent(
                id=str(row.id),
                repository=row.repository,
                commit_sha=row.commit_sha,
                first_commit_at=row.first_commit_at,
                merged_at=row.merged_at,
                deployed_at=row.deployed_at,
            )
            for row in result.fetchall()
        ]

    async def get_incidents(
        self, repo: str, start: datetime, end: datetime
    ) -> list[IncidentEvent]:
        result = await self._session.execute(
            text(
                "SELECT id, repository, detected_at, resolved_at, caused_by_sha "
                "FROM incident_events "
                "WHERE repository = :repo AND detected_at BETWEEN :start AND :end "
                "ORDER BY detected_at DESC"
            ),
            {"repo": repo, "start": start, "end": end},
        )
        return [
            IncidentEvent(
                id=str(row.id),
                repository=row.repository,
                detected_at=row.detected_at,
                resolved_at=row.resolved_at,
                caused_by_sha=row.caused_by_sha,
            )
            for row in result.fetchall()
        ]

    async def record_deployment(
        self, repo: str, sha: str, deployed_at: datetime, success: bool = True
    ) -> str:
        event_id = str(uuid.uuid4())
        await self._session.execute(
            text(
                "INSERT INTO deployment_events (id, repository, commit_sha, deployed_at, success) "
                "VALUES (:id, :repo, :sha, :deployed_at, :success)"
            ),
            {
                "id": event_id,
                "repo": repo,
                "sha": sha,
                "deployed_at": deployed_at,
                "success": success,
            },
        )
        await self._session.commit()
        return event_id

    async def record_change(
        self,
        repo: str,
        sha: str,
        first_commit_at: datetime,
        merged_at: datetime | None = None,
        deployed_at: datetime | None = None,
    ) -> str:
        event_id = str(uuid.uuid4())
        await self._session.execute(
            text(
                "INSERT INTO change_events (id, repository, commit_sha, first_commit_at, merged_at, deployed_at) "
                "VALUES (:id, :repo, :sha, :first_commit_at, :merged_at, :deployed_at)"
            ),
            {
                "id": event_id,
                "repo": repo,
                "sha": sha,
                "first_commit_at": first_commit_at,
                "merged_at": merged_at,
                "deployed_at": deployed_at,
            },
        )
        await self._session.commit()
        return event_id

    async def record_incident(
        self,
        repo: str,
        detected_at: datetime,
        resolved_at: datetime | None = None,
        caused_by_sha: str | None = None,
        severity: str = "medium",
    ) -> str:
        event_id = str(uuid.uuid4())
        await self._session.execute(
            text(
                "INSERT INTO incident_events (id, repository, detected_at, resolved_at, caused_by_sha, severity) "
                "VALUES (:id, :repo, :detected_at, :resolved_at, :caused_by_sha, :severity)"
            ),
            {
                "id": event_id,
                "repo": repo,
                "detected_at": detected_at,
                "resolved_at": resolved_at,
                "caused_by_sha": caused_by_sha,
                "severity": severity,
            },
        )
        await self._session.commit()
        return event_id


class InMemoryDORARepository:
    """In-memory fallback repository for dev/testing without a database."""

    def __init__(self) -> None:
        self._deployments: list[DeploymentEvent] = []
        self._changes: list[ChangeEvent] = []
        self._incidents: list[IncidentEvent] = []

    async def get_deployments(
        self, repo: str, start: datetime, end: datetime
    ) -> list[DeploymentEvent]:
        return [
            e
            for e in self._deployments
            if e.repository == repo and start <= e.deployed_at <= end
        ]

    async def get_changes(
        self, repo: str, start: datetime, end: datetime
    ) -> list[ChangeEvent]:
        return [
            e
            for e in self._changes
            if e.repository == repo and start <= e.first_commit_at <= end
        ]

    async def get_incidents(
        self, repo: str, start: datetime, end: datetime
    ) -> list[IncidentEvent]:
        return [
            e
            for e in self._incidents
            if e.repository == repo and start <= e.detected_at <= end
        ]

    async def record_deployment(
        self, repo: str, sha: str, deployed_at: datetime, success: bool = True
    ) -> str:
        event_id = str(uuid.uuid4())
        self._deployments.append(
            DeploymentEvent(
                id=event_id,
                repository=repo,
                commit_sha=sha,
                deployed_at=deployed_at,
                success=success,
            )
        )
        return event_id

    async def record_change(
        self,
        repo: str,
        sha: str,
        first_commit_at: datetime,
        merged_at: datetime | None = None,
        deployed_at: datetime | None = None,
    ) -> str:
        event_id = str(uuid.uuid4())
        self._changes.append(
            ChangeEvent(
                id=event_id,
                repository=repo,
                commit_sha=sha,
                first_commit_at=first_commit_at,
                merged_at=merged_at,
                deployed_at=deployed_at,
            )
        )
        return event_id

    async def record_incident(
        self,
        repo: str,
        detected_at: datetime,
        resolved_at: datetime | None = None,
        caused_by_sha: str | None = None,
        severity: str = "medium",
    ) -> str:
        event_id = str(uuid.uuid4())
        self._incidents.append(
            IncidentEvent(
                id=event_id,
                repository=repo,
                detected_at=detected_at,
                resolved_at=resolved_at,
                caused_by_sha=caused_by_sha,
            )
        )
        return event_id
