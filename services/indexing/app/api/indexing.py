"""Indexing and search API endpoints."""

import uuid
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status

from app.models.requests import (
    DocumentIndexRequest,
    DocumentIndexResponse,
    BatchIndexRequest,
    BatchIndexResponse,
    SearchRequest,
    SearchResponse,
)
from app.services import get_embedding_service, get_search_service

router = APIRouter(tags=["indexing"])


@router.post("/index", response_model=DocumentIndexResponse)
async def index_document(request: DocumentIndexRequest) -> DocumentIndexResponse:
    """
    Index a single document with embeddings.
    
    Args:
        request: Document to index
        
    Returns:
        Index response with document ID
        
    Raises:
        HTTPException: If indexing fails
    """
    try:
        # Generate document ID if not provided
        doc_id = request.id or str(uuid.uuid4())
        
        # Get services
        embedding_service = get_embedding_service()
        search_service = await get_search_service()
        
        # Generate embedding
        embedding = embedding_service.embed_text(f"{request.title} {request.content}")
        
        # Index document
        success = await search_service.index_document(
            doc_id=doc_id,
            title=request.title,
            content=request.content,
            embedding=embedding,
            metadata=request.metadata,
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to index document",
            )
        
        return DocumentIndexResponse(
            id=doc_id,
            indexed=True,
            embedding_dimension=embedding_service.get_dimension(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Indexing error: {str(e)}",
        )


@router.post("/index/batch", response_model=BatchIndexResponse)
async def index_batch(request: BatchIndexRequest) -> BatchIndexResponse:
    """
    Index multiple documents in batch.
    
    Args:
        request: Batch of documents to index
        
    Returns:
        Batch index response with counts
    """
    try:
        # Get services
        embedding_service = get_embedding_service()
        search_service = await get_search_service()
        
        # Prepare documents
        documents = []
        for doc_req in request.documents:
            doc_id = doc_req.id or str(uuid.uuid4())
            
            # Generate embedding
            text = f"{doc_req.title} {doc_req.content}"
            embedding = embedding_service.embed_text(text)
            
            documents.append({
                "id": doc_id,
                "title": doc_req.title,
                "content": doc_req.content,
                "embedding": embedding,
                "metadata": doc_req.metadata,
            })
        
        # Batch index
        success_count, error_count = await search_service.index_batch(documents)
        
        return BatchIndexResponse(
            indexed_count=success_count,
            failed_count=error_count,
            document_ids=[doc["id"] for doc in documents],
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch indexing error: {str(e)}",
        )


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    """
    Search indexed documents using hybrid (semantic + keyword) retrieval.
    
    Args:
        request: Search request
        
    Returns:
        Search results
    """
    try:
        # Validate top_k
        from app.config import settings
        top_k = min(request.top_k, settings.max_top_k)
        
        # Get services
        embedding_service = get_embedding_service()
        search_service = await get_search_service()
        
        # Execute search based on type
        if request.search_type == "semantic":
            # Semantic search only
            query_embedding = embedding_service.embed_text(request.query)
            results = await search_service.semantic_search(
                query_embedding,
                top_k,
                request.filters,
            )
            
        elif request.search_type == "keyword":
            # Keyword search only
            results = await search_service.keyword_search(
                request.query,
                top_k,
                request.filters,
            )
            
        else:  # hybrid (default)
            # Hybrid search
            query_embedding = embedding_service.embed_text(request.query)
            results = await search_service.hybrid_search(
                request.query,
                query_embedding,
                top_k,
                request.filters,
            )
        
        # Format response
        from app.models.requests import SearchResult
        
        search_results = [
            SearchResult(
                id=r["id"],
                title=r["title"],
                content=r["content"],
                score=r["score"],
                source=r.get("source"),
                url=r.get("url"),
                metadata=r.get("metadata"),
            )
            for r in results
        ]
        
        return SearchResponse(
            query=request.query,
            results=search_results,
            total=len(search_results),
            search_type=request.search_type,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search error: {str(e)}",
        )


@router.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """
    Get indexing statistics.
    
    Returns:
        Index statistics (document count, size, etc.)
    """
    try:
        search_service = await get_search_service()
        
        # Get index stats
        stats = await search_service.es.indices.stats(index=search_service.index)
        
        index_stats = stats["indices"].get(search_service.index, {})
        
        return {
            "index": search_service.index,
            "document_count": index_stats.get("total", {}).get("docs", {}).get("count", 0),
            "size_bytes": index_stats.get("total", {}).get("store", {}).get("size_in_bytes", 0),
            "embedding_model": get_embedding_service().model_name,
            "embedding_dimension": get_embedding_service().get_dimension(),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stats error: {str(e)}",
        )
