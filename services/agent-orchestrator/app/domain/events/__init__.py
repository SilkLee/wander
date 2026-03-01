"""Domain events module for log analysis domain.

This module provides the event infrastructure for the log analysis domain,
enabling asynchronous notification of important domain events through the
Observer pattern (implemented by external event bus subscribers).

Exports:
    DomainEvent: Base class for all domain events
    AnalysisCompletedEvent: Event emitted when log analysis completes
"""

from app.domain.events.analysis_completed import AnalysisCompletedEvent
from app.domain.events.base import DomainEvent

__all__ = [
    "DomainEvent",
    "AnalysisCompletedEvent",
]
