"""Knowledge base tool for RAG-based search."""

from typing import Optional, Type

from langchain.tools import BaseTool
from langchain.pydantic_v1 import BaseModel, Field
import httpx

from app.config import settings


class KnowledgeBaseInput(BaseModel):
    """Input schema for knowledge base search."""
    
    query: str = Field(description="Search query for finding similar issues or documentation")
    top_k: int = Field(default=5, description="Number of top results to return")


class KnowledgeBaseTool(BaseTool):
    """
    Tool for searching the knowledge base using RAG.
    
    Connects to the Indexing Service to perform hybrid search
    (semantic + keyword) over indexed documentation, issues, and logs.
    """
    
    name: str = "knowledge_base_search"
    description: str = """Search the knowledge base for similar failures, documentation, or solutions.
    
Use this tool when you need to:
- Find similar error messages or stack traces
- Look up documentation for specific errors
- Search for known issues and their fixes
- Retrieve relevant troubleshooting guides

Input should be a clear, specific search query describing the issue or information needed."""
    
    args_schema: Type[BaseModel] = KnowledgeBaseInput
    
    def _run(self, query: str, top_k: int = 5) -> str:
        """
        Synchronous search (not used in async context).
        
        Args:
            query: Search query
            top_k: Number of results
            
        Returns:
            Search results as formatted string
        """
        # Not implemented - use async version
        raise NotImplementedError("Use async version (arun)")
    
    async def _arun(self, query: str, top_k: int = 5) -> str:
        """
        Perform async search against knowledge base.
        
        Args:
            query: Search query
            top_k: Number of results
            
        Returns:
            Formatted search results
        """
        try:
            # Call Indexing Service search endpoint
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.elasticsearch_url}/search",
                    json={
                        "query": query,
                        "top_k": top_k,
                        "search_type": "hybrid",  # Semantic + keyword
                    },
                )
                response.raise_for_status()
                
                results = response.json()
                
                # Format results for agent consumption
                if not results.get("results"):
                    return f"No relevant results found for: {query}"
                
                formatted_results = [f"Search results for '{query}':\n"]
                
                for i, result in enumerate(results["results"], 1):
                    title = result.get("title", "Untitled")
                    content = result.get("content", "")[:300]  # Truncate
                    score = result.get("score", 0.0)
                    source = result.get("source", "unknown")
                    url = result.get("url", "")
                    
                    formatted_results.append(
                        f"{i}. **{title}** (score: {score:.2f}, source: {source})\n"
                        f"   {content}...\n"
                        f"   {url}\n"
                    )
                
                return "\n".join(formatted_results)
                
        except httpx.HTTPStatusError as e:
            # Handle 404 or other HTTP errors gracefully
            if e.response.status_code == 404:
                return self._fallback_elasticsearch_search(query, top_k)
            return f"Error searching knowledge base: {str(e)}"
            
        except httpx.RequestError as e:
            # Network errors - try direct Elasticsearch as fallback
            return self._fallback_elasticsearch_search(query, top_k)
            
        except Exception as e:
            return f"Unexpected error during search: {str(e)}"
    
    def _fallback_elasticsearch_search(self, query: str, top_k: int) -> str:
        """
        Fallback: Direct Elasticsearch search if Indexing Service unavailable.
        
        Args:
            query: Search query
            top_k: Number of results
            
        Returns:
            Search results or error message
        """
        try:
            import asyncio
            from elasticsearch import AsyncElasticsearch
            
            async def search():
                es = AsyncElasticsearch([settings.elasticsearch_url])
                
                # Simple match query
                result = await es.search(
                    index="knowledge_base",
                    body={
                        "query": {
                            "multi_match": {
                                "query": query,
                                "fields": ["title^2", "content", "error_message"],
                            }
                        },
                        "size": top_k,
                    }
                )
                
                await es.close()
                return result
            
            result = asyncio.create_task(search())
            
            if not result.get("hits", {}).get("hits"):
                return f"No results found for: {query}"
            
            formatted = [f"Search results for '{query}' (direct ES):\n"]
            for i, hit in enumerate(result["hits"]["hits"], 1):
                source = hit["_source"]
                title = source.get("title", "Untitled")
                content = source.get("content", "")[:300]
                score = hit.get("_score", 0.0)
                
                formatted.append(
                    f"{i}. {title} (score: {score:.2f})\n   {content}...\n"
                )
            
            return "\n".join(formatted)
            
        except Exception as e:
            return (
                f"Knowledge base currently unavailable. "
                f"Please analyze based on log content alone. Error: {str(e)}"
            )
