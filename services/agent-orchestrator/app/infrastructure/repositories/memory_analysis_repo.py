"""In-memory analysis repository adapter implementing RepositoryPort.

Thread-safe implementation using asyncio.Lock for concurrent access.
"""

import asyncio
from typing import Optional
from uuid import UUID

from app.application.ports import RepositoryPort
from app.domain.models.log_analysis import LogAnalysis


class MemoryAnalysisRepository(RepositoryPort):
    """In-memory implementation of analysis repository.
    
    Provides thread-safe persistence for LogAnalysis aggregates using asyncio.Lock.
    Suitable for testing and development; replace with database implementation
    (PostgreSQL, MongoDB, etc.) for production.
    
    Thread Safety:
    - Uses asyncio.Lock to protect dictionary mutations
    - Safe for concurrent async access from multiple coroutines
    - Not safe for multi-process access (use database for that)
    """

    def __init__(self) -> None:
        """Initialize empty in-memory repository with lock."""
        self._storage: dict[str, LogAnalysis] = {}
        self._lock: asyncio.Lock = asyncio.Lock()
        self._lock = asyncio.Lock()

    async def save(self, analysis: LogAnalysis) -> None:
        """Persist a log analysis to in-memory storage.
        
        Thread-safe save operation using asyncio.Lock.
        Overwrites existing analysis with same ID.
        
        Args:
            analysis: LogAnalysis domain model to save
            
        Raises:
            TypeError: If analysis is not a LogAnalysis instance
            Exception: For unexpected errors during save
        """
        if not isinstance(analysis, LogAnalysis):
            raise TypeError(
                f"Expected LogAnalysis instance, got {type(analysis).__name__}"
            )

        try:
            async with self._lock:
                analysis_id = str(analysis.id)
                self._storage[analysis_id] = analysis
        except Exception as e:
            raise RuntimeError(f"Failed to save analysis: {type(e).__name__}: {e}")

    async def get_by_id(self, analysis_id: str) -> Optional[LogAnalysis]:
        """Retrieve a log analysis by ID from in-memory storage.
        
        Thread-safe retrieval operation using asyncio.Lock.
        Returns None if analysis not found (not an error).
        
        Args:
            analysis_id: Unique identifier of analysis (string or UUID)
            
        Returns:
            LogAnalysis if found, None if not found
            
        Raises:
            ValueError: If analysis_id format is invalid
            Exception: For unexpected errors during retrieval
        """
        if not analysis_id or not str(analysis_id).strip():
            raise ValueError("analysis_id cannot be empty")

        try:
            # Normalize ID to string
            normalized_id = str(analysis_id).strip()

            async with self._lock:
                return self._storage.get(normalized_id)

        except ValueError:
            raise
        except Exception as e:
            raise RuntimeError(
                f"Failed to retrieve analysis: {type(e).__name__}: {e}"
            )

    async def list_all(self) -> list[LogAnalysis]:
        """Get all analyses from storage (utility method for testing).
        
        Returns:
            List of all stored LogAnalysis objects
        """
        async with self._lock:
            return list(self._storage.values())

    async def delete_by_id(self, analysis_id: str) -> bool:
        """Delete analysis by ID (utility method).
        
        Args:
            analysis_id: ID of analysis to delete
            
        Returns:
            True if deleted, False if not found
        """
        normalized_id = str(analysis_id).strip()

        async with self._lock:
            if normalized_id in self._storage:
                del self._storage[normalized_id]
                return True
            return False

    async def clear(self) -> None:
        """Clear all analyses from storage (utility method for testing)."""
        async with self._lock:
            self._storage.clear()

    async def count(self) -> int:
        """Get count of stored analyses (utility method for testing)."""
        async with self._lock:
            return len(self._storage)
