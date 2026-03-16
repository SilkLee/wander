from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# Ensure DATABASE_URL is available before importing app modules
# (the database module reads it at import time via _init_engine)
@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    """Create DORA tables and seed test data in CI PostgreSQL (sync, session-scoped).

    This runs once before all tests.  It uses synchronous SQLAlchemy so that
    we don't interfere with the async engine used by the application.
    """
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        # No real database — tests will use InMemoryDORARepository
        yield
        return

    # Convert async URL to sync for table setup
    sync_url = db_url.replace("+asyncpg", "")
    import sqlalchemy

    engine = sqlalchemy.create_engine(sync_url)
    with engine.begin() as conn:
        # Enable uuid-ossp extension for uuid_generate_v4()
        conn.execute(sqlalchemy.text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))

        conn.execute(
            sqlalchemy.text(
                """
                CREATE TABLE IF NOT EXISTS deployment_events (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    repository VARCHAR(255) NOT NULL,
                    commit_sha VARCHAR(64) NOT NULL,
                    deployed_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    success BOOLEAN NOT NULL DEFAULT true,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            sqlalchemy.text(
                """
                CREATE TABLE IF NOT EXISTS change_events (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    repository VARCHAR(255) NOT NULL,
                    commit_sha VARCHAR(64) NOT NULL,
                    first_commit_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    merged_at TIMESTAMP WITH TIME ZONE,
                    deployed_at TIMESTAMP WITH TIME ZONE,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            sqlalchemy.text(
                """
                CREATE TABLE IF NOT EXISTS incident_events (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    repository VARCHAR(255) NOT NULL,
                    detected_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    resolved_at TIMESTAMP WITH TIME ZONE,
                    caused_by_sha VARCHAR(64),
                    severity VARCHAR(20) DEFAULT 'medium',
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )

        # Seed test data so DORA metric tests have non-zero results
        now = datetime.now(timezone.utc)
        for i in range(30):
            ts = now - timedelta(days=30 - i)
            conn.execute(
                sqlalchemy.text(
                    "INSERT INTO deployment_events (id, repository, commit_sha, deployed_at, success) "
                    "VALUES (:id, :repo, :sha, :deployed_at, :success)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "repo": "default",
                    "sha": f"abc{i:04d}",
                    "deployed_at": ts,
                    "success": i % 8 != 0,
                },
            )
            conn.execute(
                sqlalchemy.text(
                    "INSERT INTO change_events (id, repository, commit_sha, first_commit_at, merged_at, deployed_at) "
                    "VALUES (:id, :repo, :sha, :first_commit_at, :merged_at, :deployed_at)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "repo": "default",
                    "sha": f"abc{i:04d}",
                    "first_commit_at": ts - timedelta(hours=18),
                    "merged_at": ts - timedelta(hours=2),
                    "deployed_at": ts,
                },
            )
        for i in range(4):
            ts = now - timedelta(days=25 - i * 7)
            conn.execute(
                sqlalchemy.text(
                    "INSERT INTO incident_events (id, repository, detected_at, resolved_at, caused_by_sha, severity) "
                    "VALUES (:id, :repo, :detected_at, :resolved_at, :caused_by_sha, :severity)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "repo": "default",
                    "sha": f"abc{i:04d}",
                    "detected_at": ts,
                    "resolved_at": ts + timedelta(hours=3),
                    "caused_by_sha": f"abc{i:04d}",
                    "severity": "medium",
                },
            )
    engine.dispose()
    yield
    # Teardown: drop tables after all tests
    engine = sqlalchemy.create_engine(sync_url)
    with engine.begin() as conn:
        conn.execute(sqlalchemy.text("DROP TABLE IF EXISTS incident_events"))
        conn.execute(sqlalchemy.text("DROP TABLE IF EXISTS change_events"))
        conn.execute(sqlalchemy.text("DROP TABLE IF EXISTS deployment_events"))
    engine.dispose()


from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _reinit_db_engine():
    """Re-create the async engine inside the current event loop.

    The database module creates the async engine at import time (outside any
    event loop).  asyncpg connection pools are bound to the event loop that
    was running when they were created; if the pool was created outside a
    loop (or on a different loop) asyncpg raises "Future attached to a
    different loop" errors.

    This fixture disposes the stale engine and re-creates it so that the
    pool is bound to the test's event loop.
    """
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        yield
        return

    import app.infrastructure.database as db_mod
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    # Dispose the old engine (created at import time)
    if db_mod._engine is not None:
        # dispose() on async engine is sync-safe (doesn't need await)
        db_mod._engine.sync_engine.dispose(close=False)

    # Re-create engine — the asyncpg pool will bind to the current event loop
    db_mod._engine = create_async_engine(
        db_url, echo=False, pool_size=5, max_overflow=10
    )
    db_mod._session_factory = async_sessionmaker(
        db_mod._engine, class_=AsyncSession, expire_on_commit=False
    )
    yield
    # Dispose after each test to avoid cross-test loop leaks
    if db_mod._engine is not None:
        db_mod._engine.sync_engine.dispose(close=False)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
