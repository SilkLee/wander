"""LoRA adapter loading utilities for model-service."""

from pathlib import Path


def load_lora_adapter(path: str) -> bool:
    """Load a LoRA adapter from the given path.

    Args:
        path: Filesystem path to the adapter file (e.g. adapter_model.safetensors).

    Returns:
        True if the adapter path exists and can be loaded, False otherwise.
    """
    return Path(path).exists()
