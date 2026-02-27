"""Embedding service using Sentence Transformers."""

from typing import List
import torch
from sentence_transformers import SentenceTransformer

from app.config import settings


class EmbeddingService:
    """
    Service for generating text embeddings using Sentence Transformers.
    
    Wraps sentence-transformers with batching and device management.
    """

    def __init__(self):
        """Initialize embedding model."""
        self.model_name = settings.embedding_model
        self.device = settings.device
        self.batch_size = settings.batch_size
        
        # Check device availability
        if self.device == "cuda" and not torch.cuda.is_available():
            print("CUDA not available, falling back to CPU")
            self.device = "cpu"
        
        print(f"Loading embedding model: {self.model_name} on {self.device}")
        self.model = SentenceTransformer(self.model_name, device=self.device)
        print(f"Model loaded. Embedding dimension: {self.model.get_sentence_embedding_dimension()}")

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector as list of floats
        """
        embedding = self.model.encode(
            text,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batched).
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 100,  # Show progress for large batches
        )
        return [emb.tolist() for emb in embeddings]

    def get_dimension(self) -> int:
        """
        Get embedding dimension.
        
        Returns:
            Embedding vector dimension
        """
        return self.model.get_sentence_embedding_dimension()


# Global embedding service instance (lazy loaded)
_embedding_service: EmbeddingService = None


def get_embedding_service() -> EmbeddingService:
    """
    Get or create global embedding service instance.
    
    Returns:
        Embedding service instance
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
