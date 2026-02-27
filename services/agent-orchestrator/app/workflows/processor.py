"""Workflow processor for handling stream events."""

import asyncio
import logging
from typing import Dict, Optional
import uuid

from app.agents.analyzer import LogAnalyzerAgent
from app.consumers.stream_consumer import StreamConsumer

logger = logging.getLogger(__name__)


class WorkflowProcessor:
    """
    Processes log events from streams and triggers appropriate workflows.
    """

    def __init__(self, stream_consumer: StreamConsumer):
        """
        Initialize workflow processor.

        Args:
            stream_consumer: StreamConsumer instance
        """
        self.consumer = stream_consumer
        self.analyzer_agent = LogAnalyzerAgent()
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start processing workflows in background."""
        if self._task and not self._task.done():
            logger.warning("Workflow processor already running")
            return

        logger.info("Starting workflow processor...")
        self._task = asyncio.create_task(self._process_loop())

    async def stop(self):
        """Stop processing workflows."""
        logger.info("Stopping workflow processor...")
        self.consumer.stop()

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Workflow processor stopped")

    async def _process_loop(self):
        """Main processing loop."""
        try:
            async for event in self.consumer.consume():
                try:
                    await self._process_event(event)
                    
                    # Acknowledge message after successful processing
                    message_id = event.get("_message_id")
                    if message_id:
                        await self.consumer.acknowledge(message_id)

                except Exception as e:
                    logger.error(f"Error processing event: {e}", exc_info=True)
                    # Still acknowledge to prevent blocking
                    message_id = event.get("_message_id")
                    if message_id:
                        await self.consumer.acknowledge(message_id)

        except asyncio.CancelledError:
            logger.info("Processing loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Fatal error in processing loop: {e}", exc_info=True)

    async def _process_event(self, event: Dict):
        """
        Process a single log event.

        Args:
            event: Log event from stream
        """
        event_id = event.get("event_id", "unknown")
        log_type = event.get("log_type", "unknown")
        repository = event.get("repository", "unknown")

        logger.info(
            f"Processing event {event_id} (type: {log_type}, repo: {repository})"
        )

        # Extract log content
        log_content = event.get("log_content", "")
        if not log_content:
            logger.warning(f"Event {event_id} has no log content")
            return

        # Prepare agent inputs
        agent_inputs = {
            "log_content": log_content,
            "log_type": log_type,
            "context": {
                "repository": repository,
                "branch": event.get("branch", ""),
                "commit": event.get("commit", ""),
                "source": event.get("source", ""),
                "timestamp": event.get("timestamp", ""),
            },
        }

        # Execute analysis workflow
        try:
            logger.info(f"Starting log analysis for event {event_id}")
            result = await self.analyzer_agent.execute(agent_inputs)

            logger.info(
                f"Analysis complete for event {event_id}: "
                f"severity={result.get('severity')}, "
                f"root_cause={result.get('root_cause', 'N/A')[:50]}..."
            )

            # TODO: Store result in database or send to downstream services
            # For now, just log the result
            self._log_analysis_result(event_id, result)

        except Exception as e:
            logger.error(f"Error analyzing event {event_id}: {e}", exc_info=True)

    def _log_analysis_result(self, event_id: str, result: Dict):
        """
        Log analysis result (temporary until we have a database).

        Args:
            event_id: Event ID
            result: Analysis result
        """
        logger.info("=" * 80)
        logger.info(f"ANALYSIS RESULT FOR EVENT {event_id}")
        logger.info("=" * 80)
        logger.info(f"Analysis ID: {result.get('analysis_id')}")
        logger.info(f"Severity: {result.get('severity')}")
        logger.info(f"Root Cause: {result.get('root_cause')}")
        logger.info(f"Suggested Fixes:")
        for i, fix in enumerate(result.get("suggested_fixes", []), 1):
            logger.info(f"  {i}. {fix}")
        logger.info(f"References:")
        for i, ref in enumerate(result.get("references", []), 1):
            logger.info(f"  {i}. {ref}")
        logger.info(f"Confidence: {result.get('confidence_score')}")
        logger.info("=" * 80)
