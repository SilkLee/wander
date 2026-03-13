"""LoRA trainer module – builds a trainer stub from TrainingConfig."""

from __future__ import annotations

from app.models.training import TrainingConfig


class LoRATrainerStub:
    """Stub trainer returned by build_trainer.

    Holds the config for downstream use; actual training logic
    will be added when PEFT/Transformers integration lands.
    """

    def __init__(self, config: TrainingConfig) -> None:
        self.config: TrainingConfig = config


def build_trainer(config: TrainingConfig) -> LoRATrainerStub:
    """Build a LoRA trainer stub from the given configuration.

    Args:
        config: LoRA fine-tuning configuration.

    Returns:
        A trainer stub holding the configuration.
    """
    return LoRATrainerStub(config)
