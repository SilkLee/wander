from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

logger = logging.getLogger(__name__)

_DATABASE_URL = os.getenv("DATABASE_URL", "")
_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _init_engine() -> None:
    global _engine, _session_factory  # noqa: PLW0603
    if not _DATABASE_URL:
        logger.warning("DATABASE_URL not set — database features disabled")
        return
    _engine = create_async_engine(
        _DATABASE_URL, echo=False, pool_size=5, max_overflow=10
    )
    _session_factory = async_sessionmaker(
        _engine, class_=AsyncSession, expire_on_commit=False
    )


_init_engine()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for FastAPI Depends."""
    if _session_factory is None:
        raise RuntimeError("Database not configured (DATABASE_URL not set)")
    async with _session_factory() as session:
        yield session
