"""Base domain event class for all domain events.

This module provides the abstract base class for all domain events in the log analysis domain.
Domain events represent something important that has happened within the domain,
following Domain-Driven Design principles for the Observer pattern implementation.
"""

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DomainEvent(ABC):
    """Abstract base class for all domain events.

    Domain events represent immutable records of important events that occur
    within the domain. They are used to notify other bounded contexts and
    aggregates of significant state changes through the Observer pattern.

    All domain events are immutable (frozen dataclasses) to ensure they cannot
    be modified after creation, maintaining the integrity of the event log.

    Attributes:
        event_id: Unique identifier for this event (auto-generated UUID)
        occurred_at: UTC timestamp when the event occurred (auto-generated)
        aggregate_id: UUID of the LogAnalysis aggregate this event is associated with
        event_type: String identifier of the event type (defaults to class name)

    Business Context:
        Domain events serve as an asynchronous communication mechanism between
        the Agent Orchestrator and downstream systems (e.g., notification services,
        audit logs, analytics pipelines). Each event captures a point-in-time
        snapshot of what happened and why it matters to the business.

    Example:
        Typically subclassed, never instantiated directly:

        @dataclass(frozen=True)
        class AnalysisCompletedEvent(DomainEvent):
            severity: Severity
            confidence_score: float
    """

    aggregate_id: UUID
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str = field(default="")

    def __post_init__(self) -> None:
        """Initialize event_type to class name if not explicitly set.

        This ensures every event has a meaningful event_type even if subclasses
        don't explicitly set it. The event_type is used for event routing and
        filtering in event handlers and event stores.

        Raises:
            ValueError: If aggregate_id is None or invalid
        """
        if self.aggregate_id is None:
            raise ValueError("aggregate_id cannot be None")

        # Use object.__setattr__ for frozen dataclasses
        if not self.event_type:
            object.__setattr__(self, "event_type", self.__class__.__name__)

    def __str__(self) -> str:
        """Return human-readable representation of the event.

        Returns:
            Formatted string describing the event occurrence
        """
        return (
            f"{self.event_type}(aggregate_id={self.aggregate_id}, "
            f"occurred_at={self.occurred_at.isoformat()})"
        )

    def __repr__(self) -> str:
        """Return detailed representation of the event for debugging.

        Returns:
            Complete string representation including all fields
        """
        return (
            f"{self.__class__.__name__}("
            f"event_id={self.event_id}, "
            f"aggregate_id={self.aggregate_id}, "
            f"event_type={self.event_type!r}, "
            f"occurred_at={self.occurred_at.isoformat()})"
        )

    def get_occurred_timestamp(self) -> str:
        """Get ISO 8601 formatted timestamp of when the event occurred.

        Returns:
            ISO 8601 formatted UTC datetime string
        """
        return self.occurred_at.isoformat()
