"""Configuration management for Indexing service."""

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
    port: int = Field(default=8003, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    host: str = Field(default="0.0.0.0", description="Server host")

    # Elasticsearch Configuration
    elasticsearch_url: str = Field(
        default="http://localhost:9200",
        description="Elasticsearch connection URL",
    )
    elasticsearch_index: str = Field(
        default="knowledge_base",
        description="Default Elasticsearch index",
    )

    # Embedding Model Configuration
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Sentence Transformers model name",
    )
    embedding_dimension: int = Field(
        default=384,
        description="Embedding vector dimension",
    )
    device: str = Field(
        default="cpu",
        description="Device for inference (cuda/cpu)",
    )
    batch_size: int = Field(
        default=32,
        description="Batch size for embedding generation",
    )

    # Search Configuration
    default_top_k: int = Field(
        default=10,
        description="Default number of search results",
    )
    max_top_k: int = Field(
        default=100,
        description="Maximum number of search results",
    )


# Global settings instance
settings = Settings()
