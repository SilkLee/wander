"""PR risk agent – wires PR risk flow to model-service classifier."""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.clients.model_service import classify_risk
from app.config import settings
from app.services.rerank import secondary_rerank, should_rerank

logger = logging.getLogger(__name__)

_FALLBACK_LABEL = "medium"


async def run_pr_risk_agent(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Assess PR risk using the fine-tuned classifier.

    Calls model-service ``/classify/risk`` with the PR diff and returns
    the predicted ``risk_label``.  On classifier failure, falls back to
    ``\"medium\"`` and sets ``degraded=True``.

    Args:
        inputs: Dict with at minimum ``diff`` (str).

    Returns:
        Dict with ``risk_label`` (str), and on error ``degraded`` (bool)
        and ``error`` (str).
    """
    diff_text: str = inputs.get("diff", "")

    try:
        result = await classify_risk(diff_text)
        response: Dict[str, Any] = {"risk_label": result["label"]}

        # Apply secondary rerank when enabled for pr_risk
        if should_rerank(
            "pr_risk",
            enabled=settings.secondary_rerank_enabled,
            targets=settings.secondary_rerank_targets,
        ):
            await secondary_rerank([{"content": diff_text, "score": 1.0}], query=diff_text)
            response["reranked"] = True

        return response
    except Exception as exc:
        logger.warning("classify_risk failed, using fallback: %s", exc)
        return {
            "risk_label": _FALLBACK_LABEL,
            "degraded": True,
            "error": str(exc),
        }
