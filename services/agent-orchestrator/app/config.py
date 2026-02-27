"""Configuration management using pydantic-settings."""

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
    port: int = Field(default=8002, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    host: str = Field(default="0.0.0.0", description="Server host")

    # External Services
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    elasticsearch_url: str = Field(
        default="http://localhost:9200",
        description="Elasticsearch connection URL",
    )
    model_service_url: str = Field(
        default="http://localhost:8004",
        description="Model service base URL",
    )

    # OpenAI Configuration
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(
        default="gpt-4-turbo-preview",
        description="Default OpenAI model",
    )

    # LangChain Configuration
    langchain_tracing_v2: bool = Field(
        default=False,
        description="Enable LangChain tracing",
    )
    langchain_api_key: str = Field(default="", description="LangChain API key")

    # Agent Configuration
    agent_max_iterations: int = Field(
        default=10,
        description="Maximum agent iterations",
    )
    agent_timeout_seconds: int = Field(
        default=300,
        description="Agent execution timeout",
    )


# Global settings instance
settings = Settings()
