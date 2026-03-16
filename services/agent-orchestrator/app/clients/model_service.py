"""HTTP client for model-service /classify/risk endpoint."""

from __future__ import annotations

import logging
from typing import Any, Dict

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)


async def classify_risk(diff_text: str) -> Dict[str, Any]:
    """Call model-service POST /classify/risk.

    Args:
        diff_text: PR diff text to classify.

    Returns:
        Dict with ``label`` (str) and ``score`` (float).

    Raises:
        RuntimeError: On HTTP or connection errors.
    """
    url = f"{settings.model_service_url}/classify/risk"
    payload = {"input": diff_text}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        msg = f"classify_risk HTTP error: {exc.response.status_code}"
        logger.error(msg)
        raise RuntimeError(msg) from exc
    except httpx.RequestError as exc:
        msg = f"classify_risk connection error: {exc}"
        logger.error(msg)
        raise RuntimeError(msg) from exc
