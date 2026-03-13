"""Tests for LoRA adapter loading in model-service."""

from app.services.lora import load_lora_adapter


def test_loads_lora_adapter_when_path_exists(tmp_path):
    """load_lora_adapter returns True when the adapter file exists."""
    adapter_path = tmp_path / "adapter_model.safetensors"
    adapter_path.write_bytes(b"dummy")
    assert load_lora_adapter(str(adapter_path)) is True


def test_load_lora_adapter_returns_false_for_missing_path(tmp_path):
    """load_lora_adapter returns False when path does not exist."""
    missing = tmp_path / "nonexistent" / "adapter_model.safetensors"
    assert load_lora_adapter(str(missing)) is False
