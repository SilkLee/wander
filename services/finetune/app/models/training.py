"""Training run models and configuration schema for LoRA fine-tuning."""

from pydantic import BaseModel, Field


class TrainingConfig(BaseModel):
    """Configuration for a LoRA fine-tuning run."""

    lora_r: int = Field(default=16, description="LoRA rank")
    lora_alpha: int = Field(default=32, description="LoRA alpha scaling factor")
