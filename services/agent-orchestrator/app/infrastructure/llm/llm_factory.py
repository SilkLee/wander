"""LLM factory implementing Strategy pattern for model selection.

Supports multiple LLM backends:
- Model Service: Local inference service (default, CPU-friendly)
- OpenAI: Cloud-based gpt-4-turbo and other models
"""

from langchain_openai import ChatOpenAI
from langchain_core.language_models.llms import LLM

from app.config import settings
from app.llm import ModelServiceLLM


class LLMFactory:
    """Factory for creating LLM instances based on configuration.
    
    Implements Strategy pattern to abstract LLM creation logic.
    Selects implementation (Model Service vs OpenAI) based on app.config settings.
    
    Usage:
        factory = LLMFactory()
        llm = factory.create_llm()  # Returns LLM based on config
        
    Configuration (from app.config):
        - use_local_model: bool - Use local Model Service if True, OpenAI if False
        - model_service_url: str - URL for local Model Service
        - openai_model: str - OpenAI model name (e.g., gpt-4-turbo-preview)
        - openai_api_key: str - OpenAI API key
    """

    @staticmethod
    def create_llm(
        temperature: float = 0.0,
        max_tokens: int = 512,
        timeout: int = 300,
    ) -> LLM:
        """Create LLM instance based on configuration.
        
        Strategy selection:
        - If settings.use_local_model is True: Use ModelServiceLLM
        - If settings.use_local_model is False: Use ChatOpenAI
        
        Args:
            temperature: Model temperature (0.0 = deterministic, 1.0 = creative)
                        Used by both strategies
            max_tokens: Maximum output tokens (used by Model Service strategy)
            timeout: Request timeout in seconds (used by both strategies)
            
        Returns:
            LLM instance configured for the selected backend
            
        Raises:
            ValueError: If configuration is invalid or missing required credentials
            Exception: If LLM initialization fails
        """
        try:
            if settings.use_local_model:
                return LLMFactory._create_model_service_llm(
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                )
            else:
                return LLMFactory._create_openai_llm(
                    temperature=temperature,
                    timeout=timeout,
                )

        except Exception as e:
            raise RuntimeError(
                f"Failed to create LLM instance: {type(e).__name__}: {e}"
            )

    @staticmethod
    def _create_model_service_llm(
        temperature: float = 0.0,
        max_tokens: int = 512,
        timeout: int = 300,
    ) -> ModelServiceLLM:
        """Create Model Service LLM strategy.
        
        Connects to local Model Service for inference.
        Suitable for CPU-based models (e.g., Qwen2.5-1.5B).
        
        Args:
            temperature: Model temperature parameter
            max_tokens: Maximum tokens for response
            timeout: Request timeout in seconds
            
        Returns:
            ModelServiceLLM instance
            
        Raises:
            ValueError: If model_service_url is not configured
            Exception: If initialization fails
        """
        if not settings.model_service_url:
            raise ValueError(
                "model_service_url not configured. "
                "Set MODELSERVICE_URL environment variable or config"
            )

        try:
            llm = ModelServiceLLM(
                model_service_url=settings.model_service_url,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            return llm

        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize ModelServiceLLM: {type(e).__name__}: {e}"
            )

    @staticmethod
    def _create_openai_llm(
        temperature: float = 0.0,
        timeout: int = 300,
    ) -> ChatOpenAI:
        """Create OpenAI LLM strategy.
        
        Connects to OpenAI API for inference.
        Requires valid API key and supports all OpenAI models.
        
        Args:
            temperature: Model temperature parameter
            timeout: Request timeout in seconds
            
        Returns:
            ChatOpenAI instance
            
        Raises:
            ValueError: If API key is not configured
            Exception: If initialization fails
        """
        if not settings.openai_api_key:
            raise ValueError(
                "openai_api_key not configured. "
                "Set OPENAI_API_KEY environment variable"
            )

        if not settings.openai_model:
            raise ValueError(
                "openai_model not configured. "
                "Set OPENAI_MODEL environment variable"
            )

        try:
            llm = ChatOpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                temperature=temperature,
                request_timeout=timeout,
            )
            return llm

        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize ChatOpenAI: {type(e).__name__}: {e}"
            )

    @staticmethod
    def get_current_backend() -> str:
        """Get name of currently configured LLM backend.
        
        Returns:
            "model_service" if use_local_model is True, "openai" otherwise
        """
        return "model_service" if settings.use_local_model else "openai"

    @staticmethod
    def get_backend_info() -> dict[str, object]:
        """Get detailed information about configured LLM backend.
        
        Returns:
            Dict with backend configuration details:
            - backend: Name of LLM backend (model_service|openai)
            - model: Model name or service URL
            - configured: Whether required credentials are set
        """
        backend = LLMFactory.get_current_backend()

        if settings.use_local_model:
            return {
                "backend": backend,
                "service_url": settings.model_service_url,
                "configured": bool(settings.model_service_url),
            }
        else:
            return {
                "backend": backend,
                "model": settings.openai_model,
                "configured": bool(settings.openai_api_key),
            }
