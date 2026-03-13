"""Tests for the LoRA trainer module."""

from app.models.training import TrainingConfig
from app.training.lora_trainer import build_trainer


class TestBuildTrainer:
    """build_trainer should return a trainer stub from a TrainingConfig."""

    def test_build_trainer_returns_object(self):
        """build_trainer(config) should return a non-None object."""
        config = TrainingConfig()
        trainer = build_trainer(config)
        assert trainer is not None

    def test_build_trainer_returns_object_with_config(self):
        """The returned trainer should expose the config it was built with."""
        config = TrainingConfig(lora_r=8, lora_alpha=16)
        trainer = build_trainer(config)
        assert trainer.config is config

    def test_build_trainer_with_default_config(self):
        """build_trainer with default TrainingConfig should preserve defaults."""
        config = TrainingConfig()
        trainer = build_trainer(config)
        assert trainer.config.lora_r == 16
        assert trainer.config.lora_alpha == 32
