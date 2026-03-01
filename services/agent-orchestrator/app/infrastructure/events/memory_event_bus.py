"""In-memory async event bus implementation using Observer pattern.

Thread-safe implementation using asyncio.Lock for concurrent subscribe/unsubscribe operations.
Suitable for single-service event handling; use Redis EventBus for distributed systems.
"""

import asyncio
import logging
from functools import lru_cache
from typing import Type

from app.domain.events.base import DomainEvent
from app.infrastructure.events.event_bus import EventBus, EventHandler


logger = logging.getLogger(__name__)


class MemoryEventBus(EventBus):
    """In-memory implementation of EventBus using asyncio primitives.

    Provides thread-safe event publishing and subscription using asyncio.Lock
    to protect the handler registry. All operations are asynchronous and non-blocking.

    Thread Safety:
        - Uses asyncio.Lock to protect concurrent subscribe/unsubscribe operations
        - Safe for concurrent calls from multiple async tasks
        - Not safe for multi-process access (use distributed event bus for that)

    Handler Registry:
        - Stored as dict[Type[DomainEvent], list[EventHandler]]
        - Each event type maps to a list of registered handlers
        - Multiple registrations of the same handler are allowed
        - Unsubscribe removes only one occurrence

    Error Handling:
        - Handler exceptions are logged but do not propagate
        - Other handlers are still invoked if one fails (isolation)
        - Failures logged at ERROR level with full exception details

    Performance Notes:
        - O(n) lookup for unsubscribe (linear scan of handlers list)
        - publish() is O(n) where n = number of handlers for event type
        - asyncio.gather() runs all handlers concurrently (non-blocking)

    Example:
        ```python
        # Create instance (singleton recommended via @lru_cache)
        event_bus = MemoryEventBus()

        # Define handlers
        async def notify_team(event: DomainEvent) -> None:
            if isinstance(event, AnalysisCompletedEvent):
                await send_slack_notification(event)

        async def update_analytics(event: DomainEvent) -> None:
            if isinstance(event, AnalysisCompletedEvent):
                await update_metrics(event)

        # Subscribe multiple handlers to same event
        await event_bus.subscribe(AnalysisCompletedEvent, notify_team)
        await event_bus.subscribe(AnalysisCompletedEvent, update_analytics)

        # Publish event - both handlers run concurrently
        event = AnalysisCompletedEvent(
            aggregate_id=analysis_id,
            severity=Severity.CRITICAL,
            is_critical=True,
            confidence_score=0.92,
            root_cause_count=2
        )
        await event_bus.publish(event)
        ```

    Testing Utilities:
        - clear_all_handlers(): Reset registry for testing
        - get_handler_count(event_type): Query handler count
    """

    def __init__(self) -> None:
        """Initialize empty handler registry with asyncio.Lock."""
        self._handlers: dict[Type[DomainEvent], list[EventHandler]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def subscribe(
        self, event_type: Type[DomainEvent], handler: EventHandler
    ) -> None:
        """Register a handler to receive events of a specific type.

        Thread-safe operation using asyncio.Lock. The same handler can be
        registered multiple times; each registration is independent.

        Args:
            event_type: The DomainEvent subclass to subscribe to
            handler: Async callable to invoke when event is published

        Raises:
            TypeError: If event_type is not a subclass of DomainEvent
            TypeError: If handler is not callable

        Example:
            ```python
            async def on_analysis_completed(event: DomainEvent) -> None:
                print(f"Event: {event.event_type}")

            await event_bus.subscribe(AnalysisCompletedEvent, on_analysis_completed)
            ```
        """
        # Validate event_type
        if not (isinstance(event_type, type) and issubclass(event_type, DomainEvent)):
            raise TypeError(
                f"event_type must be a subclass of DomainEvent, got {event_type}"
            )

        # Validate handler is callable
        if not callable(handler):
            raise TypeError(f"handler must be callable, got {type(handler).__name__}")

        async with self._lock:
            # Create event type entry if not exists
            if event_type not in self._handlers:
                self._handlers[event_type] = []

            # Add handler to registry
            self._handlers[event_type].append(handler)
            logger.debug(
                f"Handler {handler.__name__} subscribed to {event_type.__name__} "
                f"(total: {len(self._handlers[event_type])})"
            )

    async def unsubscribe(
        self, event_type: Type[DomainEvent], handler: EventHandler
    ) -> None:
        """Unregister a handler so it no longer receives events.

        Thread-safe operation using asyncio.Lock. Removes one occurrence of the
        handler from the registry. If the handler is not registered or is registered
        multiple times, only one registration is removed (no error if not found).

        Args:
            event_type: The DomainEvent subclass to unsubscribe from
            handler: The exact handler function to remove

        Example:
            ```python
            await event_bus.unsubscribe(AnalysisCompletedEvent, on_analysis_completed)
            ```
        """
        async with self._lock:
            # If event type has no handlers, nothing to do
            if event_type not in self._handlers:
                logger.debug(
                    f"No handlers registered for {event_type.__name__}, "
                    f"unsubscribe is no-op"
                )
                return

            handlers = self._handlers[event_type]

            # Try to remove handler by reference (identity)
            try:
                handlers.remove(handler)
                logger.debug(
                    f"Handler {handler.__name__} unsubscribed from {event_type.__name__} "
                    f"(remaining: {len(handlers)})"
                )
            except ValueError:
                # Handler not in list, which is fine (idempotent)
                logger.debug(
                    f"Handler {handler.__name__} not found for {event_type.__name__}, "
                    f"unsubscribe is no-op"
                )

            # Clean up empty event type entries
            if not handlers:
                del self._handlers[event_type]

    async def publish(self, event: DomainEvent) -> None:
        """Emit an event to all registered handlers for that event type.

        Retrieves all handlers for the event's type and invokes them concurrently
        using asyncio.gather(). Handler exceptions are logged but do not propagate.
        Other handlers are still invoked if one fails (isolation).

        This method is fire-and-forget: returns immediately and handlers run
        asynchronously in the background.

        Args:
            event: The DomainEvent instance to publish

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
            ```

        Handler Isolation:
            If a handler raises an exception, it is logged but does not affect
            other handlers. This ensures one broken handler doesn't bring down
            the entire event processing pipeline.
        """
        # Validate event
        if not isinstance(event, DomainEvent):
            raise TypeError(
                f"event must be a DomainEvent instance, got {type(event).__name__}"
            )

        # Get handlers for this event type (copy to avoid lock contention)
        async with self._lock:
            event_type = type(event)
            handlers = self._handlers.get(event_type, []).copy()

        if not handlers:
            logger.debug(f"No handlers registered for {event_type.__name__}")
            return

        logger.debug(
            f"Publishing {event_type.__name__} to {len(handlers)} handler(s)"
        )

        # Schedule handlers to run concurrently in background (fire-and-forget)
        # Use create_task to schedule without waiting
        for handler in handlers:
            asyncio.create_task(self._invoke_handler(handler, event))

    async def _invoke_handler(
        self, handler: EventHandler, event: DomainEvent
    ) -> None:
        """Invoke a single handler and log any exceptions (internal utility).

        Args:
            handler: The handler coroutine to invoke
            event: The event to pass to the handler
        """
        try:
            await handler(event)
        except Exception as e:
            logger.error(
                f"Handler {handler.__name__} failed for {type(event).__name__}: "
                f"{type(e).__name__}: {e}",
                exc_info=True,
            )

    async def clear_all_handlers(self) -> None:
        """Clear all handlers from registry (testing utility).

        Useful for resetting state between tests to ensure test isolation.

        Example:
            ```python
            @pytest.fixture
            async def event_bus():
                bus = MemoryEventBus()
                yield bus
                await bus.clear_all_handlers()
            ```
        """
        async with self._lock:
            self._handlers.clear()
            logger.debug("Cleared all handlers from registry")

    async def get_handler_count(self, event_type: Type[DomainEvent]) -> int:
        """Get count of handlers registered for an event type (testing utility).

        Args:
            event_type: The DomainEvent subclass to query

        Returns:
            Number of handlers registered for this event type (0 if none)

        Example:
            ```python
            count = await event_bus.get_handler_count(AnalysisCompletedEvent)
            assert count == 2  # Two handlers registered
            ```
        """
        async with self._lock:
            return len(self._handlers.get(event_type, []))


@lru_cache(maxsize=1)
def get_event_bus() -> MemoryEventBus:
    """Get singleton instance of MemoryEventBus (recommended for dependency injection).

    Uses functools.lru_cache to ensure only one instance is created throughout
    the application lifecycle. This is the recommended pattern for obtaining
    the event bus instance.

    Returns:
        Singleton MemoryEventBus instance

    Example:
        ```python
        # In dependency container
        event_bus = get_event_bus()

        # Same instance is returned on all subsequent calls
        assert get_event_bus() is event_bus
        ```

    Design Note:
        The singleton pattern ensures all components in the application share
        the same event bus instance, so subscriptions are centralized.
    """
    return MemoryEventBus()
