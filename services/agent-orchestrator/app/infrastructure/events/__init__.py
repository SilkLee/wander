"""EventBus infrastructure layer for async event-driven architecture.

This package provides the Observer pattern implementation for handling domain events
asynchronously. It includes:

- EventBus Protocol: Abstract interface for event buses
- EventHandler Type: Type alias for event handler functions
- MemoryEventBus: In-memory implementation using asyncio primitives
- get_event_bus(): Singleton factory function for dependency injection

Architecture:
    The EventBus implements the Observer pattern, enabling loose coupling between
    publishers (domain models) and subscribers (application services). Events are
    processed asynchronously without blocking, and handler failures are isolated
    (one failure doesn't affect other handlers).

Usage:
    ```python
    from app.infrastructure.events import EventBus, MemoryEventBus, get_event_bus

    # Option 1: Use singleton factory
    event_bus = get_event_bus()

    # Option 2: Manually instantiate (for testing)
    event_bus = MemoryEventBus()

    # Subscribe to events
    async def on_analysis_completed(event: DomainEvent) -> None:
        if isinstance(event, AnalysisCompletedEvent):
            await send_notification(event)

    await event_bus.subscribe(AnalysisCompletedEvent, on_analysis_completed)

    # Publish an event
    event = AnalysisCompletedEvent(...)
    await event_bus.publish(event)

    # Unsubscribe when done
    await event_bus.unsubscribe(AnalysisCompletedEvent, on_analysis_completed)
    ```

Thread Safety:
    All EventBus implementations must be thread-safe for concurrent subscribe/unsubscribe
    operations. MemoryEventBus uses asyncio.Lock for synchronization.

Design Notes:
    - EventBus is NOT a message queue (events not persisted)
    - EventBus is NOT a service bus (no remote transport)
    - Handlers run concurrently and failures don't propagate
    - publish() is fire-and-forget (returns immediately)

For distributed event handling across services, consider a separate Redis EventBus
or message queue integration.
"""

from app.infrastructure.events.event_bus import EventBus, EventHandler
from app.infrastructure.events.memory_event_bus import MemoryEventBus, get_event_bus


__all__ = [
    "EventBus",
    "EventHandler",
    "MemoryEventBus",
    "get_event_bus",
]
