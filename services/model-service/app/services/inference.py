"""LLM inference service using Transformers."""

from typing import Optional
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig

from app.config import settings


class InferenceService:
    """
    Service for LLM inference using HuggingFace Transformers.
    
    Supports text generation with configurable parameters.
    """

    def __init__(self):
        """Initialize model and tokenizer."""
        self.model_name = settings.model_name
        self.device = settings.device
        self.max_model_len = settings.max_model_len
        
        # Check device availability
        if self.device == "cuda" and not torch.cuda.is_available():
            print("CUDA not available, falling back to CPU")
            self.device = "cpu"
        
        print(f"Loading model: {self.model_name} on {self.device}")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            revision=settings.model_revision,
            trust_remote_code=True,
        )
        
        # Load model
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            revision=settings.model_revision,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map="auto" if self.device == "cuda" else None,
            trust_remote_code=True,
        )
        
        if self.device == "cpu":
            self.model = self.model.to(self.device)
        
        self.model.eval()
        print(f"Model loaded successfully")

    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stop: Optional[list] = None,
    ) -> tuple[str, int, str]:
        """
        Generate text from prompt.
        
        Args:
            prompt: Input prompt
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling probability
            stop: Stop sequences
            
        Returns:
            Tuple of (generated_text, tokens_generated, finish_reason)
        """
        # Use defaults if not provided
        max_tokens = max_tokens or settings.default_max_tokens
        temperature = temperature if temperature is not None else settings.default_temperature
        top_p = top_p if top_p is not None else settings.default_top_p
        
        # Tokenize input
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        input_length = inputs.input_ids.shape[1]
        
        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=temperature > 0,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        
        # Decode output
        full_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract generated portion (remove prompt)
        generated_text = full_text[len(prompt):]
        tokens_generated = outputs.shape[1] - input_length
        
        # Determine finish reason
        finish_reason = "length" if tokens_generated >= max_tokens else "stop"
        
        return generated_text, tokens_generated, finish_reason

    def get_model_info(self) -> dict:
        """Get model information."""
        return {
            "name": self.model_name,
            "type": "transformers",
            "device": self.device,
            "max_length": self.max_model_len,
            "parameters": {
                "default_max_tokens": settings.default_max_tokens,
                "default_temperature": settings.default_temperature,
                "default_top_p": settings.default_top_p,
            },
        }


# Global inference service instance
_inference_service: InferenceService = None


def get_inference_service() -> InferenceService:
    """Get or create global inference service instance."""
    global _inference_service
    if _inference_service is None:
        _inference_service = InferenceService()
    return _inference_service
