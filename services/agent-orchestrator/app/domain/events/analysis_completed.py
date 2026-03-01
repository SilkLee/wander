"""Analysis completed domain event.

This module defines the AnalysisCompletedEvent that is emitted when a log analysis
completes successfully and produces actionable results for downstream systems.
"""

from dataclasses import dataclass, field
from uuid import UUID

from app.domain.events.base import DomainEvent
from app.domain.models.severity import Severity


@dataclass(frozen=True)
class AnalysisCompletedEvent(DomainEvent):
    """Domain event emitted when log analysis completes successfully.

    This event represents a completed analysis of logs with determined severity,
    confidence, and identified root causes. It signals to subscribers that a
    LogAnalysis aggregate has reached a terminal state and action may be needed.

    Business Significance:
        This event triggers downstream workflows such as:
        - Notification service: Alert on-call engineers if critical
        - Audit service: Record the analysis for compliance tracking
        - Analytics service: Update DORA metrics and trend data
        - Remediation service: Initiate automated fixes if available

    The event captures the analysis outcome snapshot to allow subscribers to
    react without querying the original LogAnalysis aggregate (eventual
    consistency pattern).

    Attributes:
        severity: The determined severity level of identified issues
            (LOW, MEDIUM, HIGH, or CRITICAL)
        is_critical: Derived boolean indicating if severity >= HIGH,
            provided for convenience to subscribers
        confidence_score: The confidence level of the analysis result
            (range [0.0, 1.0]) - can be used by subscribers for filtering
        root_cause_count: Number of root causes identified during analysis
            (provides cardinality for subscribers without full event body)

    Example:
        ```python
        event = AnalysisCompletedEvent(
            aggregate_id=analysis.id,
            severity=Severity.CRITICAL,
            is_critical=True,
            confidence_score=0.92,
            root_cause_count=2
        )
        event_bus.publish(event)
        ```

    Immutability:
        As a frozen dataclass, this event cannot be modified after creation.
        This ensures the historical record of what happened remains accurate
        and prevents accidental corruption of event logs.
    """

    severity: Severity = field(default_factory=lambda: Severity.LOW)
    is_critical: bool = field(default=False)
    confidence_score: float = field(default=0.0)
    root_cause_count: int = field(default=0)

    def __post_init__(self) -> None:
        """Validate analysis completed event fields.

        Performs validation of confidence score and root cause count ranges.
        Calls parent __post_init__ to set event_type if needed.

        Raises:
            ValueError: If confidence_score not in [0.0, 1.0]
            ValueError: If root_cause_count is negative
            ValueError: If is_critical doesn't match severity level
            ValueError: If aggregate_id is None
        """
        # Call parent initialization first (validates aggregate_id, sets event_type)
        super().__post_init__()

        # Validate confidence score range
        if not (0.0 <= self.confidence_score <= 1.0):
            raise ValueError(
                f"confidence_score must be between 0.0 and 1.0, "
                f"got {self.confidence_score}"
            )

        # Validate root cause count
        if self.root_cause_count < 0:
            raise ValueError(
                f"root_cause_count cannot be negative, got {self.root_cause_count}"
            )

        # Validate is_critical matches severity
        expected_is_critical = self.severity >= Severity.HIGH
        if self.is_critical != expected_is_critical:
            raise ValueError(
                f"is_critical must be {expected_is_critical} for "
                f"severity {self.severity.name}, got {self.is_critical}"
            )

    def __str__(self) -> str:
        """Return human-readable representation of the analysis completion event.

        Returns:
            Formatted string describing the analysis completion
        """
        return (
            f"AnalysisCompletedEvent(aggregate_id={self.aggregate_id}, "
            f"severity={self.severity.name}, critical={self.is_critical}, "
            f"confidence={self.confidence_score:.1%})"
        )

    def get_summary(self) -> str:
        """Get a concise summary of the analysis completion for subscribers.

        Returns:
            Brief description of the analysis outcome
        """
        return (
            f"{self.severity.name} severity analysis with "
            f"{self.confidence_score:.1%} confidence and "
            f"{self.root_cause_count} identified cause(s)"
        )

    def should_alert_on_call(self) -> bool:
        """Determine if this event warrants immediate on-call engineer notification.

        Returns:
            True if severity is CRITICAL and confidence is high, False otherwise
        """
        return self.is_critical and self.confidence_score > 0.8
