"""Custom LLM wrapper for local Model Service integration."""

from typing import Any, List, Optional, Mapping, Iterator, Dict
import httpx
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.llms import LLM
from langchain_core.outputs import GenerationChunk

from app.config import settings


class ModelServiceLLM(LLM):
    """
    Custom LangChain LLM wrapper for WorkflowAI Model Service.
    
    Allows LangChain agents to use the local Model Service (port 8004)
    instead of OpenAI API, enabling:
    - Offline operation
    - Custom model support (Qwen, Llama, etc.)
    - Cost reduction (no API fees)
    - Full control over inference
    """

    model_service_url: str = settings.model_service_url
    max_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    stop: Optional[List[str]] = None
    timeout: int = 60

    @property
    def _llm_type(self) -> str:
        """Return identifier for this LLM."""
        return "model_service"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """
        Call Model Service to generate text.
        
        Args:
            prompt: Input text prompt
            stop: Stop sequences (overrides default)
            run_manager: Callback manager for streaming
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text string
        """
        # Merge stop sequences
        stop_sequences = stop or self.stop

        # Build request payload
        payload = {
            "prompt": prompt,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", self.top_p),
            "stop": stop_sequences,
        }

        # Call Model Service
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.model_service_url}/generate",
                    json=payload,
                )
                response.raise_for_status()
                result = response.json()
                
                # Extract generated text
                generated_text = result.get("text", "")
                
                # Notify run_manager if streaming callbacks exist
                if run_manager:
                    run_manager.on_llm_new_token(generated_text)
                
                return generated_text

        except httpx.HTTPStatusError as e:
            error_msg = f"Model Service HTTP error: {e.response.status_code} - {e.response.text}"
            raise RuntimeError(error_msg) from e
        except httpx.RequestError as e:
            error_msg = f"Model Service connection error: {str(e)}"
            raise RuntimeError(error_msg) from e
        except Exception as e:
            error_msg = f"Model Service unexpected error: {str(e)}"
            raise RuntimeError(error_msg) from e

    async def _acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """
        Async version of _call for non-blocking execution.
        
        Args:
            prompt: Input text prompt
            stop: Stop sequences
            run_manager: Callback manager
            **kwargs: Additional parameters
            
        Returns:
            Generated text string
        """
        stop_sequences = stop or self.stop

        payload = {
            "prompt": prompt,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", self.top_p),
            "stop": stop_sequences,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.model_service_url}/generate",
                    json=payload,
                )
                response.raise_for_status()
                result = response.json()
                
                generated_text = result.get("text", "")
                
                if run_manager:
                    await run_manager.on_llm_new_token(generated_text)
                
                return generated_text

        except httpx.HTTPStatusError as e:
            error_msg = f"Model Service HTTP error: {e.response.status_code} - {e.response.text}"
            raise RuntimeError(error_msg) from e
        except httpx.RequestError as e:
            error_msg = f"Model Service connection error: {str(e)}"
            raise RuntimeError(error_msg) from e
        except Exception as e:
            error_msg = f"Model Service unexpected error: {str(e)}"
            raise RuntimeError(error_msg) from e

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        """Return identifying parameters for this LLM."""
        return {
            "model_service_url": self.model_service_url,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "timeout": self.timeout,
        }

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get model information from Model Service.
        
        Returns:
            Dictionary with model metadata
        """
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self.model_service_url}/model/info")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {"error": str(e), "model_service_url": self.model_service_url}

    async def aget_model_info(self) -> Dict[str, Any]:
        """Async version of get_model_info."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.model_service_url}/model/info")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {"error": str(e), "model_service_url": self.model_service_url}
