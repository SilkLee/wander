"""Secondary rerank service stub.

Provides a passthrough ``secondary_rerank`` that will be replaced with a
cross-encoder reranker in a later iteration.  Also exposes ``should_rerank``
to check whether secondary reranking is enabled for a given workflow target.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def secondary_rerank(
    documents: List[Dict[str, Any]],
    query: str,
    *,
    top_k: Optional[int] = None,
    model_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Re-rank *documents* by relevance to *query* (stub – passthrough).

    In the future this will call a cross-encoder model.  For now it returns
    *documents* unchanged so callers can be wired without side-effects.

    Args:
        documents: Retrieved documents, each a dict with at least ``content``.
        query: The user query / context string.
        top_k: Optional limit on returned documents (ignored in stub).
        model_name: Optional model identifier (ignored in stub).

    Returns:
        The same *documents* list, unmodified.
    """
    logger.debug(
        "secondary_rerank stub called with %d docs (top_k=%s, model=%s)",
        len(documents),
        top_k,
        model_name,
    )
    return documents


def should_rerank(
    target: str,
    *,
    enabled: bool,
    targets: List[str],
) -> bool:
    """Return ``True`` if secondary reranking should run for *target*.

    Args:
        target: Workflow name (e.g. ``"pr_risk"``, ``"code_review"``).
        enabled: Whether secondary reranking is globally enabled.
        targets: List of workflow names that should use reranking.

    Returns:
        ``True`` only when *enabled* is ``True`` **and** *target* appears in
        *targets*.
    """
    return enabled and target in targets
