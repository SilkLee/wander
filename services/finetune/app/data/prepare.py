"""Dataset preparation utilities for LoRA fine-tuning."""

from __future__ import annotations

from typing import Any


def prepare_sample(sample: dict[str, Any]) -> dict[str, Any]:
    """Validate and format a single training sample.

    Args:
        sample: Raw sample dict that must contain a non-empty ``label`` key.

    Returns:
        Formatted sample dict ready for training.

    Raises:
        ValueError: If ``label`` is missing, None, or empty string.
    """
    label = sample.get("label")
    if not label:
        raise ValueError("Sample is missing a required non-empty 'label' field")

    return {"text": sample.get("text", ""), "label": label}
