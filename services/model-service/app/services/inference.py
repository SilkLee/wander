"""LLM inference service using Transformers."""

from typing import Optional, Generator, Iterator, List, Dict
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
        # Use local path if provided, otherwise use HuggingFace model ID
        self.model_path = settings.local_model_path or settings.model_name
        self.is_local = settings.local_model_path is not None and len(settings.local_model_path.strip()) > 0
        self.model_name = settings.model_name
        self.device = settings.device
        self.max_model_len = settings.max_model_len
        
        # Check device availability
        if self.device == "cuda" and not torch.cuda.is_available():
            print("CUDA not available, falling back to CPU")
            self.device = "cpu"
        
        print(f"Loading model from: {self.model_path}")
        print(f"Device: {self.device}")
        print(f"Local model: {self.is_local}")
        
        # Load tokenizer
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                revision=None if self.is_local else settings.model_revision,
                trust_remote_code=True,
                local_files_only=self.is_local,  # Only disable downloads if using local path
            )
        except Exception as e:
            print(f"Error loading tokenizer: {e}")
            raise
        
        # Load model
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                revision=None if self.is_local else settings.model_revision,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None,
                trust_remote_code=True,
                local_files_only=self.is_local,  # Only disable downloads if using local path
                low_cpu_mem_usage=True,  # Reduce memory usage during loading
            )
        except Exception as e:
            print(f"Error loading model: {e}")
            raise
        
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
        stop: Optional[List[str]] = None,
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

    def generate_stream(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stop: Optional[List[str]] = None,
    ) -> Iterator[tuple[str, bool]]:
        """
        Generate text from prompt with streaming (token-by-token).
        
        Args:
            prompt: Input prompt
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling probability
            stop: Stop sequences
            
        Yields:
            Tuple of (token_text, is_final)
        """
        # Use defaults if not provided
        max_tokens = max_tokens or settings.default_max_tokens
        temperature = temperature if temperature is not None else settings.default_temperature
        top_p = top_p if top_p is not None else settings.default_top_p
        
        # Tokenize input
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        input_ids = inputs.input_ids
        input_length = input_ids.shape[1]
        
        # Generation config
        gen_config = GenerationConfig(
            max_new_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=temperature > 0,
            pad_token_id=self.tokenizer.eos_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
        )
        
        # Track generated tokens
        generated_tokens = []
        token_count = 0
        
        # Generate token by token
        with torch.no_grad():
            current_ids = input_ids
            
            for _ in range(max_tokens):
                # Generate next token
                outputs = self.model(
                    input_ids=current_ids,
                    use_cache=True,
                )
                
                # Get logits for next token
                next_token_logits = outputs.logits[:, -1, :]
                
                # Apply temperature
                if temperature > 0:
                    next_token_logits = next_token_logits / temperature
                    
                    # Apply top-p (nucleus) sampling
                    if top_p < 1.0:
                        sorted_logits, sorted_indices = torch.sort(next_token_logits, descending=True)
                        cumulative_probs = torch.cumsum(torch.softmax(sorted_logits, dim=-1), dim=-1)
                        
                        # Remove tokens with cumulative probability above the threshold
                        sorted_indices_to_remove = cumulative_probs > top_p
                        # Keep at least one token
                        sorted_indices_to_remove[..., 0] = False
                        
                        indices_to_remove = sorted_indices[sorted_indices_to_remove]
                        next_token_logits[:, indices_to_remove] = float('-inf')
                    
                    # Sample from distribution
                    probs = torch.softmax(next_token_logits, dim=-1)
                    next_token = torch.multinomial(probs, num_samples=1)
                else:
                    # Greedy decoding
                    next_token = torch.argmax(next_token_logits, dim=-1, keepdim=True)
                
                # Check if EOS token
                if next_token.item() == self.tokenizer.eos_token_id:
                    break
                
                # Decode token
                token_text = self.tokenizer.decode(next_token[0], skip_special_tokens=True)
                generated_tokens.append(token_text)
                token_count += 1
                
                # Yield token (not final)
                yield (token_text, False)
                
                # Append to current sequence
                current_ids = torch.cat([current_ids, next_token], dim=-1)
                
                # Check if reached max tokens
                if token_count >= max_tokens:
                    break
        
        # Yield final marker
        yield ("", True)

    def get_model_info(self) -> Dict[str, any]:
        """Get model information."""
        return {
            "name": self.model_name,
            "path": self.model_path,
            "is_local": self.is_local,
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
_inference_service: Optional[InferenceService] = None


def get_inference_service() -> InferenceService:
    """Get or create global inference service instance."""
    global _inference_service
    if _inference_service is None:
        _inference_service = InferenceService()
    return _inference_service
