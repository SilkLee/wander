"""Redis Streams consumer for log events."""

import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Optional

from redis.asyncio import Redis
from redis.exceptions import ResponseError

logger = logging.getLogger(__name__)


class StreamConsumer:
    """
    Consumes log events from Redis Streams and triggers analysis workflows.
    """

    def __init__(
        self,
        redis_client: Redis,
        stream_name: str,
        consumer_group: str,
        consumer_name: str,
        block_ms: int = 5000,
        count: int = 10,
    ):
        """
        Initialize stream consumer.

        Args:
            redis_client: Redis async client
            stream_name: Name of the stream to consume from
            consumer_group: Name of the consumer group
            consumer_name: Name of this consumer instance
            block_ms: Blocking timeout in milliseconds
            count: Max number of messages to read at once
        """
        self.redis = redis_client
        self.stream_name = stream_name
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name
        self.block_ms = block_ms
        self.count = count
        self._running = False

    async def ensure_consumer_group(self) -> bool:
        """
        Ensure consumer group exists.

        Returns:
            True if group exists or was created successfully
        """
        try:
            await self.redis.xgroup_create(
                name=self.stream_name,
                groupname=self.consumer_group,
                id="0",
                mkstream=True,
            )
            logger.info(
                f"Created consumer group '{self.consumer_group}' for stream '{self.stream_name}'"
            )
            return True
        except ResponseError as e:
            if "BUSYGROUP" in str(e):
                # Group already exists
                logger.info(
                    f"Consumer group '{self.consumer_group}' already exists"
                )
                return True
            logger.error(f"Failed to create consumer group: {e}")
            return False

    async def consume(self) -> AsyncGenerator[Dict, None]:
        """
        Consume messages from the stream.

        Yields:
            Parsed log event dictionaries
        """
        # Ensure consumer group exists
        if not await self.ensure_consumer_group():
            logger.error("Cannot start consumer without consumer group")
            return

        self._running = True
        logger.info(
            f"Starting consumer '{self.consumer_name}' for group '{self.consumer_group}'"
        )

        # Start from last unacknowledged or new messages
        last_id = ">"

        while self._running:
            try:
                # Read from stream
                messages = await self.redis.xreadgroup(
                    groupname=self.consumer_group,
                    consumername=self.consumer_name,
                    streams={self.stream_name: last_id},
                    count=self.count,
                    block=self.block_ms,
                )

                if not messages:
                    # No new messages within timeout
                    continue

                # Process each message
                for stream, stream_messages in messages:
                    for message_id, fields in stream_messages:
                        try:
                            # Parse message
                            event = self._parse_message(fields)
                            event["_message_id"] = message_id.decode()
                            event["_stream"] = stream.decode()

                            yield event

                        except Exception as e:
                            logger.error(
                                f"Error parsing message {message_id}: {e}"
                            )
                            # Acknowledge failed message to prevent blocking
                            await self.acknowledge(message_id)

            except asyncio.CancelledError:
                logger.info("Consumer cancelled")
                self._running = False
                break
            except Exception as e:
                logger.error(f"Error consuming from stream: {e}")
                await asyncio.sleep(1)  # Avoid tight loop on errors

    def _parse_message(self, fields: Dict[bytes, bytes]) -> Dict:
        """
        Parse stream message fields.

        Args:
            fields: Raw message fields from Redis

        Returns:
            Parsed event dictionary
        """
        # Decode bytes to strings
        decoded = {k.decode(): v.decode() for k, v in fields.items()}

        # Parse JSON data field if present
        if "data" in decoded:
            try:
                data = json.loads(decoded["data"])
                # Merge data into event
                decoded.update(data)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON data: {e}")

        return decoded

    async def acknowledge(self, message_id: str) -> bool:
        """
        Acknowledge a message as processed.

        Args:
            message_id: ID of the message to acknowledge

        Returns:
            True if acknowledgment successful
        """
        try:
            await self.redis.xack(
                self.stream_name, self.consumer_group, message_id
            )
            logger.debug(f"Acknowledged message {message_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to acknowledge message {message_id}: {e}")
            return False

    async def get_pending_count(self) -> int:
        """
        Get count of pending (unacknowledged) messages.

        Returns:
            Number of pending messages
        """
        try:
            info = await self.redis.xpending(
                self.stream_name, self.consumer_group
            )
            return info["pending"]
        except Exception as e:
            logger.error(f"Failed to get pending count: {e}")
            return 0

    def stop(self):
        """Stop the consumer."""
        logger.info("Stopping consumer...")
        self._running = False
