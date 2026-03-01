"""Request DTO for log analysis endpoint.

DTOs provide the API contract, separate from domain models to allow
independent evolution of API and domain layers.
"""

from pydantic import BaseModel, Field, field_validator


class LogAnalysisRequest(BaseModel):
    """Request DTO for log analysis endpoint.
    
    Validates incoming API requests before passing to use case.
    Provides clear separation between HTTP layer concerns and
    application/domain logic.
    
    Attributes:
        log_content: Raw log text to analyze (required, non-empty)
        
    Validators:
        - Ensures log_content is not empty after stripping whitespace
        - Ensures log_content has reasonable length (> 10, < 100,000 chars)
    """

    log_content: str = Field(
        ...,
        min_length=1,
        description="Raw log content to analyze",
        example="ERROR [2025-03-01 10:15:22] Connection timeout in database pool\n"
        "Stack: at DB.connect() line 45\n"
        "WARN [2025-03-01 10:15:23] Retrying connection...",
    )

    @field_validator("log_content")
    @classmethod
    def validate_log_content(cls, v: str) -> str:
        """Validate log content is meaningful and reasonable length.
        
        Args:
            v: Log content string
            
        Returns:
            Validated log content
            
        Raises:
            ValueError: If content is empty after strip or exceeds max length
        """
        if not v.strip():
            raise ValueError("Log content cannot be empty or whitespace-only")

        if len(v) > 100_000:
            raise ValueError(
                "Log content exceeds maximum length of 100,000 characters"
            )

        if len(v) < 10:
            raise ValueError(
                "Log content must be at least 10 characters (minimum meaningful log)"
            )

        return v

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "log_content": "[ERROR] Database connection failed. "
                "Retry attempts: 3. Last error: timeout after 30s"
            }
        }
