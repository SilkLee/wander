"""Configuration management for Model service."""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server Configuration
    port: int = Field(default=8004, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    host: str = Field(default="0.0.0.0", description="Server host")

    # Model Configuration
    model_name: str = Field(
        default="Qwen/Qwen2.5-1.5B-Instruct",
        description="HuggingFace model ID",
    )
    model_revision: str = Field(
        default="main",
        description="Model revision/branch",
    )
    device: str = Field(
        default="cpu",
        description="Device for inference (cuda/cpu)",
    )
    max_model_len: int = Field(
        default=4096,
        description="Maximum model sequence length",
    )

    # Generation Parameters
    default_max_tokens: int = Field(
        default=512,
        description="Default max tokens to generate",
    )
    default_temperature: float = Field(
        default=0.7,
        description="Default sampling temperature",
    )
    default_top_p: float = Field(
        default=0.9,
        description="Default nucleus sampling probability",
    )

    # vLLM Configuration
    use_vllm: bool = Field(
        default=False,
        description="Use vLLM for inference (faster)",
    )
    vllm_tensor_parallel_size: int = Field(
        default=1,
        description="Tensor parallelism size for vLLM",
    )
    vllm_gpu_memory_utilization: float = Field(
        default=0.9,
        description="GPU memory utilization for vLLM",
    )

    # Cache Configuration
    hf_home: str = Field(
        default="/app/cache/huggingface",
        description="HuggingFace cache directory",
    )
    transformers_cache: str = Field(
        default="/app/cache/transformers",
        description="Transformers cache directory",
    )
    local_model_path: Optional[str] = Field(
        default=None,
        description="Local model directory path (overrides model_name)",
    )


# Global settings instance
settings = Settings()
