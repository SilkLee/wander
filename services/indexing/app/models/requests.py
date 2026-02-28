"""Request and response models for Indexing service."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(description="Service status")
    service: str = Field(description="Service name")
    version: str = Field(description="Service version")
    elasticsearch_connected: bool = Field(description="Elasticsearch connection status")
    model_loaded: bool = Field(description="Embedding model loaded status")


class DocumentIndexRequest(BaseModel):
    """Request to index a document."""

    id: Optional[str] = Field(default=None, description="Document ID (auto-generated if not provided)")
    title: str = Field(description="Document title")
    content: str = Field(description="Document content")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata (source, url, tags, etc.)",
    )


class DocumentIndexResponse(BaseModel):
    """Response from document indexing."""

    id: str = Field(description="Document ID")
    indexed: bool = Field(description="Successfully indexed")
    embedding_dimension: int = Field(description="Embedding vector dimension")


class BatchIndexRequest(BaseModel):
    """Request to index multiple documents."""

    documents: List[DocumentIndexRequest] = Field(description="List of documents to index")


class BatchIndexResponse(BaseModel):
    """Response from batch indexing."""

    indexed_count: int = Field(description="Number of successfully indexed documents")
    failed_count: int = Field(description="Number of failed documents")
    document_ids: List[str] = Field(description="List of indexed document IDs")


class SearchRequest(BaseModel):
    """Request for hybrid search."""

    query: str = Field(description="Search query")
    top_k: int = Field(default=10, description="Number of results to return")
    search_type: str = Field(
        default="hybrid",
        description="Search type: semantic, keyword, or hybrid",
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional filters (source, tags, etc.)",
    )


class SearchResult(BaseModel):
    """Single search result."""

    id: str = Field(description="Document ID")
    title: str = Field(description="Document title")
    content: str = Field(description="Document content (truncated)")
    score: float = Field(description="Relevance score")
    source: Optional[str] = Field(default=None, description="Document source")
    url: Optional[str] = Field(default=None, description="Document URL")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata",
    )


class SearchResponse(BaseModel):
    """Response from search."""

    query: str = Field(description="Original query")
    results: List[SearchResult] = Field(description="Search results")
    total: int = Field(description="Total number of matches")
    search_type: str = Field(description="Search type used")
