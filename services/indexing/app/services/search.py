"""Elasticsearch client for indexing and search."""

from typing import List, Dict, Any, Optional
import uuid
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk

from app.config import settings


class SearchService:
    """
    Service for Elasticsearch indexing and hybrid search.
    
    Combines dense vector (semantic) and sparse (keyword) retrieval.
    """

    def __init__(self):
        """Initialize Elasticsearch client."""
        self.es = AsyncElasticsearch([settings.elasticsearch_url])
        self.index = settings.elasticsearch_index

    async def ensure_index(self):
        """
        Ensure index exists with proper mappings.
        
        Creates index with dense_vector field for semantic search
        and text fields for keyword search.
        """
        if await self.es.indices.exists(index=self.index):
            return

        # Index mapping with dense vector
        mapping = {
            "mappings": {
                "properties": {
                    "title": {"type": "text", "analyzer": "standard"},
                    "content": {"type": "text", "analyzer": "standard"},
                    "embedding": {
                        "type": "dense_vector",
                        "dims": settings.embedding_dimension,
                        "index": True,
                        "similarity": "cosine",
                    },
                    "metadata": {"type": "object", "enabled": True},
                    "source": {"type": "keyword"},
                    "url": {"type": "keyword"},
                    "tags": {"type": "keyword"},
                    "indexed_at": {"type": "date"},
                }
            }
        }

        await self.es.indices.create(index=self.index, body=mapping)
        print(f"Created index: {self.index}")

    async def index_document(
        self,
        doc_id: str,
        title: str,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Index a single document.
        
        Args:
            doc_id: Document ID
            title: Document title
            content: Document content
            embedding: Embedding vector
            metadata: Optional metadata
            
        Returns:
            True if indexed successfully
        """
        from datetime import datetime

        doc = {
            "title": title,
            "content": content,
            "embedding": embedding,
            "metadata": metadata or {},
            "source": metadata.get("source", "unknown") if metadata else "unknown",
            "url": metadata.get("url", "") if metadata else "",
            "tags": metadata.get("tags", []) if metadata else [],
            "indexed_at": datetime.utcnow().isoformat(),
        }

        result = await self.es.index(index=self.index, id=doc_id, document=doc)
        return result["result"] in ["created", "updated"]

    async def index_batch(
        self,
        documents: List[Dict[str, Any]],
    ) -> tuple[int, int]:
        """
        Index multiple documents in bulk.
        
        Args:
            documents: List of documents with id, title, content, embedding, metadata
            
        Returns:
            Tuple of (success_count, error_count)
        """
        from datetime import datetime

        actions = []
        for doc in documents:
            action = {
                "_index": self.index,
                "_id": doc["id"],
                "_source": {
                    "title": doc["title"],
                    "content": doc["content"],
                    "embedding": doc["embedding"],
                    "metadata": doc.get("metadata", {}),
                    "source": doc.get("metadata", {}).get("source", "unknown"),
                    "url": doc.get("metadata", {}).get("url", ""),
                    "tags": doc.get("metadata", {}).get("tags", []),
                    "indexed_at": datetime.utcnow().isoformat(),
                },
            }
            actions.append(action)

        success, errors = await async_bulk(self.es, actions, raise_on_error=False)
        return success, len(errors)

    async def semantic_search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search using vector similarity.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results
            filters: Optional metadata filters
            
        Returns:
            List of search results
        """
        # Build query
        query = {
            "script_score": {
                "query": self._build_filter_query(filters) if filters else {"match_all": {}},
                "script": {
                    "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                    "params": {"query_vector": query_embedding},
                },
            }
        }

        result = await self.es.search(
            index=self.index,
            query=query,
            size=top_k,
            _source=["title", "content", "source", "url", "metadata"],
        )

        return self._format_results(result)

    async def keyword_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform keyword search using BM25.
        
        Args:
            query: Search query
            top_k: Number of results
            filters: Optional metadata filters
            
        Returns:
            List of search results
        """
        # Multi-match query
        query_body = {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^2", "content"],
                            "type": "best_fields",
                        }
                    }
                ],
                "filter": self._build_filters(filters) if filters else [],
            }
        }

        result = await self.es.search(
            index=self.index,
            query=query_body,
            size=top_k,
            _source=["title", "content", "source", "url", "metadata"],
        )

        return self._format_results(result)

    async def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        semantic_weight: float = 0.6,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining semantic and keyword search.
        
        Uses weighted score fusion (semantic 60%, keyword 40% by default).
        
        Args:
            query: Search query
            query_embedding: Query embedding vector
            top_k: Number of results
            filters: Optional metadata filters
            semantic_weight: Weight for semantic search (0-1)
            
        Returns:
            List of search results ranked by combined score
        """
        # Get both result sets
        semantic_results = await self.semantic_search(query_embedding, top_k * 2, filters)
        keyword_results = await self.keyword_search(query, top_k * 2, filters)

        # Merge and re-rank
        combined = {}
        keyword_weight = 1.0 - semantic_weight

        for result in semantic_results:
            doc_id = result["id"]
            combined[doc_id] = {
                **result,
                "score": result["score"] * semantic_weight,
            }

        for result in keyword_results:
            doc_id = result["id"]
            if doc_id in combined:
                combined[doc_id]["score"] += result["score"] * keyword_weight
            else:
                combined[doc_id] = {
                    **result,
                    "score": result["score"] * keyword_weight,
                }

        # Sort by combined score
        sorted_results = sorted(combined.values(), key=lambda x: x["score"], reverse=True)
        return sorted_results[:top_k]

    def _build_filter_query(self, filters: Dict[str, Any]) -> Dict:
        """Build Elasticsearch filter query from filters dict."""
        return {"bool": {"filter": self._build_filters(filters)}}

    def _build_filters(self, filters: Dict[str, Any]) -> List[Dict]:
        """Build list of filter clauses."""
        filter_clauses = []
        for key, value in filters.items():
            if isinstance(value, list):
                filter_clauses.append({"terms": {key: value}})
            else:
                filter_clauses.append({"term": {key: value}})
        return filter_clauses

    def _format_results(self, es_result: Dict) -> List[Dict[str, Any]]:
        """Format Elasticsearch results to standard format."""
        results = []
        for hit in es_result["hits"]["hits"]:
            source = hit["_source"]
            results.append({
                "id": hit["_id"],
                "title": source.get("title", ""),
                "content": source.get("content", "")[:500],  # Truncate
                "score": hit["_score"],
                "source": source.get("source"),
                "url": source.get("url"),
                "metadata": source.get("metadata", {}),
            })
        return results

    async def close(self):
        """Close Elasticsearch connection."""
        await self.es.close()


# Global search service instance (lazy loaded)
_search_service: SearchService = None


async def get_search_service() -> SearchService:
    """
    Get or create global search service instance.
    
    Returns:
        Search service instance
    """
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
        await _search_service.ensure_index()
    return _search_service
