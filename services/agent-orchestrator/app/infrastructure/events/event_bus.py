"""EventBus Protocol interface defining the Observer pattern for async event handling.

This module provides the abstract interface for event buses implementing the Observer pattern
for asynchronous event-driven architecture. All EventBus implementations must conform to
this protocol.

Observer Pattern Overview:
    - Subscribers (handlers) register interest in specific event types
    - Publishers emit events when state changes occur
    - EventBus routes events to all interested subscribers
    - Subscribers are decoupled from publishers (loose coupling)
    - Event handling is asynchronous (non-blocking)
"""

from typing import Protocol, Type, Callable, Awaitable
from app.domain.events.base import DomainEvent


# Type alias for event handler functions: async callable taking DomainEvent and returning None
EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBus(Protocol):
    """Protocol defining the interface for event buses in event-driven architecture.

    The EventBus implements the Observer pattern, allowing subscribers to react to
    events without direct coupling to event publishers. All operations are asynchronous
    to support high-throughput, non-blocking event processing.

    Semantics:
        - subscribe(): Register a handler to react to all events of a specific type
        - unsubscribe(): Remove a handler so it no longer receives events
        - publish(): Emit an event to all registered handlers for that event type
        - Handler failures do not propagate or affect other handlers (isolation)
        - publish() returns immediately (fire-and-forget); handlers run concurrently

    Thread Safety:
        - Safe for concurrent subscribe/unsubscribe operations (thread-safe registration)
        - Safe for concurrent publish operations
        - Uses asyncio.Lock internally for handler registry mutations

    Example Usage:
        ```python
        # Instantiate concrete implementation
        event_bus = MemoryEventBus()

        # Define a handler
        async def on_analysis_completed(event: DomainEvent) -> None:
            if isinstance(event, AnalysisCompletedEvent):
                print(f"Analysis completed with severity: {event.severity}")
                # Send notification, update database, etc.

        # Subscribe to events
        await event_bus.subscribe(AnalysisCompletedEvent, on_analysis_completed)

        # Publish an event
        event = AnalysisCompletedEvent(
            aggregate_id=analysis_id,
            severity=Severity.CRITICAL,
            is_critical=True,
            confidence_score=0.92,
            root_cause_count=2
        )
        await event_bus.publish(event)

        # Handler is invoked asynchronously
        # Unsubscribe when no longer interested
        await event_bus.unsubscribe(AnalysisCompletedEvent, on_analysis_completed)
        ```

    Design Notes:
        - EventBus is NOT a message queue: events are not persisted
        - EventBus is NOT a service bus: no remote transport (see Redis EventBus for that)
        - All handlers for an event type are called concurrently via asyncio.gather()
        - Handler order is not guaranteed
        - A handler may be registered multiple times; each invocation is independent
    """

    async def subscribe(
        self, event_type: Type[DomainEvent], handler: EventHandler
    ) -> None:
        """Register a handler to receive events of a specific type.

        The handler will be called asynchronously each time an event of the specified
        type is published. The same handler can be registered multiple times; each
        registration is independent.

        Args:
            event_type: The DomainEvent subclass to subscribe to (e.g., AnalysisCompletedEvent)
            handler: Async callable with signature: async def handler(event: DomainEvent) -> None

        Returns:
            None

        Raises:
            TypeError: If event_type is not a subclass of DomainEvent
            TypeError: If handler is not a callable Awaitable

        Example:
            ```python
            async def handle_critical_analysis(event: DomainEvent) -> None:
                if isinstance(event, AnalysisCompletedEvent) and event.is_critical:
                    await send_alert(event)

            await event_bus.subscribe(AnalysisCompletedEvent, handle_critical_analysis)
            ```

        Thread Safety:
            Safe for concurrent calls. Handler registry is protected by asyncio.Lock.
        """
        ...

    async def unsubscribe(
        self, event_type: Type[DomainEvent], handler: EventHandler
    ) -> None:
        """Unregister a handler so it no longer receives events.

        Removes one occurrence of the handler from the registry for the specified
        event type. If the handler is registered multiple times, only one registration
        is removed. If the handler is not registered, this is a no-op (no error).

        Args:
            event_type: The DomainEvent subclass to unsubscribe from
            handler: The exact handler function to remove

        Returns:
            None

        Example:
            ```python
            async def temporary_handler(event: DomainEvent) -> None:
                print("Temporary event processing")

            await event_bus.subscribe(AnalysisCompletedEvent, temporary_handler)
            # ... later ...
            await event_bus.unsubscribe(AnalysisCompletedEvent, temporary_handler)
            ```

        Thread Safety:
            Safe for concurrent calls. Handler registry is protected by asyncio.Lock.
        """
        ...

    async def publish(self, event: DomainEvent) -> None:
        """Emit an event to all registered handlers for that event type.

        Retrieves all handlers registered for the event's type and invokes them
        concurrently using asyncio.gather(). Handler failures are logged but do
        not propagate to the caller or affect other handlers.

        This method is fire-and-forget: it returns immediately and handlers run
        concurrently. The caller does not wait for handlers to complete.

        Args:
            event: The DomainEvent instance to publish

        Returns:
            None (immediately; handlers run concurrently)

        Raises:
            TypeError: If event is not a DomainEvent instance

        Example:
            ```python
            event = AnalysisCompletedEvent(
                aggregate_id=analysis_id,
                severity=Severity.CRITICAL,
                is_critical=True,
                confidence_score=0.92,
                root_cause_count=2
            )

            # Returns immediately; handlers run asynchronously
            await event_bus.publish(event)

            # Any handler failures are logged, not raised
            ```

        Handler Isolation:
            If one handler raises an exception, it is logged but other handlers
            are still invoked. Exception details are logged for debugging.

        Concurrency:
            All handlers for the event type are invoked concurrently.
            If no handlers are registered for this event type, this is a no-op.

        Thread Safety:
            Safe for concurrent calls. Internal operations are thread-safe.
        """
        ...
