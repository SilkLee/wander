"""Test configuration."""

import pytest


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    from app.config import Settings
    return Settings(
        port=8002,
        debug=True,
        redis_url="redis://localhost:6379/0",
        elasticsearch_url="http://localhost:9200",
        openai_api_key="test-key",
        openai_model="gpt-4-turbo-preview",
    )
