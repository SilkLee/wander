"""Tests for the finetune service training models."""

from app.models.training import TrainingConfig


def test_training_config_defaults():
    """TrainingConfig should have sensible LoRA defaults."""
    cfg = TrainingConfig()
    assert cfg.lora_r == 16
    assert cfg.lora_alpha == 32


def test_training_config_custom_values():
    """TrainingConfig should accept custom LoRA parameters."""
    cfg = TrainingConfig(lora_r=8, lora_alpha=16)
    assert cfg.lora_r == 8
    assert cfg.lora_alpha == 16


def test_training_config_exported_from_models_package():
    """TrainingConfig should be importable from the models package."""
    from app.models import TrainingConfig as ExportedConfig

    cfg = ExportedConfig()
    assert cfg.lora_r == 16


def test_training_config_is_pydantic_model():
    """TrainingConfig should be a Pydantic BaseModel for validation."""
    from pydantic import BaseModel

    assert issubclass(TrainingConfig, BaseModel)
