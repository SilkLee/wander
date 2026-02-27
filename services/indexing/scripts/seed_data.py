#!/usr/bin/env python3
"""
Seed data script for Indexing Service knowledge base.
Creates initial documents for testing and development.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.services.embeddings import EmbeddingService
from app.services.search import SearchService


# Sample knowledge base documents
SEED_DOCUMENTS = [
    {
        "doc_id": "doc-001",
        "title": "Python AsyncIO Best Practices",
        "content": """AsyncIO is Python's built-in library for writing concurrent code using async/await syntax. 
        Best practices include: 1) Always use async/await consistently throughout your async functions. 
        2) Use asyncio.gather() for concurrent operations. 3) Properly handle exceptions in async contexts. 
        4) Close resources with async context managers. 5) Use asyncio.create_task() for fire-and-forget operations.
        Common pitfalls: mixing sync and async code, forgetting to await coroutines, blocking the event loop with CPU-intensive tasks.""",
        "metadata": {
            "source": "internal-docs",
            "category": "programming",
            "language": "python",
            "tags": ["asyncio", "concurrency", "best-practices"],
            "difficulty": "intermediate"
        }
    },
    {
        "doc_id": "doc-002",
        "title": "Elasticsearch Index Mapping Guide",
        "content": """Elasticsearch mappings define how documents and their fields are stored and indexed. 
        Key concepts: 1) Field types (text, keyword, integer, float, date, etc.). 2) Analyzers for text processing. 
        3) Dynamic vs explicit mappings. 4) Index templates for consistent mapping across indices. 
        5) Field data types affect search behavior and storage requirements. Use 'keyword' for exact matches, 
        'text' for full-text search. Define mappings before indexing for optimal performance.""",
        "metadata": {
            "source": "elasticsearch-docs",
            "category": "database",
            "technology": "elasticsearch",
            "tags": ["elasticsearch", "mapping", "indexing"],
            "difficulty": "intermediate"
        }
    },
    {
        "doc_id": "doc-003",
        "title": "Docker Multi-Stage Build Optimization",
        "content": """Multi-stage Docker builds reduce image size and improve security by separating build and runtime environments.
        Best practices: 1) Use specific base image tags (not 'latest'). 2) Order layers from least to most frequently changing.
        3) Use .dockerignore to exclude unnecessary files. 4) Combine RUN commands to reduce layers. 
        5) Use COPY instead of ADD unless you need extraction. 6) Clean up package manager caches in same RUN command.
        Example: Install dependencies in build stage, copy only artifacts to final stage.""",
        "metadata": {
            "source": "docker-docs",
            "category": "devops",
            "technology": "docker",
            "tags": ["docker", "optimization", "container"],
            "difficulty": "intermediate"
        }
    },
    {
        "doc_id": "doc-004",
        "title": "FastAPI Dependency Injection System",
        "content": """FastAPI's dependency injection system provides a powerful way to manage dependencies and share logic.
        Features: 1) Automatic dependency resolution. 2) Dependency caching for performance. 3) Async and sync dependency support.
        4) Class-based dependencies for stateful logic. 5) Override dependencies for testing. 
        Common use cases: database sessions, authentication, configuration, request validation.
        Dependencies can be functions, classes, or generators. Use Depends() to declare dependencies in route handlers.""",
        "metadata": {
            "source": "fastapi-docs",
            "category": "framework",
            "technology": "fastapi",
            "language": "python",
            "tags": ["fastapi", "dependency-injection", "api"],
            "difficulty": "intermediate"
        }
    },
    {
        "doc_id": "doc-005",
        "title": "Common Error: NullPointerException in Java",
        "content": """NullPointerException (NPE) occurs when accessing methods or fields on a null object reference.
        Common causes: 1) Uninitialized object fields. 2) Method returns null unexpectedly. 3) Null values in collections.
        4) Chained method calls where intermediate result is null. 
        Solutions: 1) Check for null before accessing (if obj != null). 2) Use Optional<T> for methods that might return null.
        3) Initialize fields in constructor. 4) Use @NonNull/@Nullable annotations. 5) Enable null safety warnings in IDE.
        Prevention: design APIs to avoid returning null when possible, use Optional or default values.""",
        "metadata": {
            "source": "error-solutions",
            "category": "error-resolution",
            "language": "java",
            "error_type": "NullPointerException",
            "tags": ["java", "error", "null-safety"],
            "difficulty": "beginner"
        }
    },
    {
        "doc_id": "doc-006",
        "title": "Common Error: CORS Policy Blocking",
        "content": """CORS (Cross-Origin Resource Sharing) errors occur when browser blocks requests from different origins.
        Error message: 'Access-Control-Allow-Origin header is missing' or 'CORS policy blocked'.
        Causes: 1) API server doesn't set CORS headers. 2) Preflight OPTIONS request fails. 3) Credentials mode mismatch.
        Solutions: 1) Configure server to send Access-Control-Allow-Origin header. 2) Handle OPTIONS preflight requests.
        3) Set Access-Control-Allow-Methods for allowed HTTP methods. 4) Include credentials header if using cookies.
        For FastAPI: Use CORSMiddleware. For Express: Use cors middleware. Always configure allowed origins explicitly in production.""",
        "metadata": {
            "source": "error-solutions",
            "category": "error-resolution",
            "technology": "web",
            "error_type": "CORS",
            "tags": ["cors", "browser", "security", "api"],
            "difficulty": "intermediate"
        }
    },
    {
        "doc_id": "doc-007",
        "title": "Redis Connection Pool Best Practices",
        "content": """Connection pooling improves Redis client performance by reusing connections instead of creating new ones.
        Best practices: 1) Configure appropriate pool size (default: 10-50 connections). 2) Set connection timeout (5-10 seconds).
        3) Enable health checks to detect stale connections. 4) Use connection pool per application instance, not per request.
        5) Monitor pool utilization and connection errors. 6) Handle connection failures with retry logic and circuit breaker.
        For Python: Use redis-py with connection pool. For Node.js: Use ioredis with built-in pooling.""",
        "metadata": {
            "source": "redis-docs",
            "category": "database",
            "technology": "redis",
            "tags": ["redis", "connection-pool", "performance"],
            "difficulty": "intermediate"
        }
    },
    {
        "doc_id": "doc-008",
        "title": "JWT Token Security Best Practices",
        "content": """JSON Web Tokens (JWT) require careful handling to prevent security vulnerabilities.
        Best practices: 1) Use strong signing algorithms (RS256 or HS256 with 256+ bit secret). 2) Set short expiration times (15-30 minutes for access tokens).
        3) Store tokens in httpOnly cookies, not localStorage (prevents XSS attacks). 4) Implement token refresh mechanism.
        5) Validate issuer, audience, and expiration on every request. 6) Use HTTPS to prevent token interception.
        7) Implement token revocation for logout and security events. Avoid storing sensitive data in token payload (it's base64, not encrypted).""",
        "metadata": {
            "source": "security-docs",
            "category": "security",
            "technology": "jwt",
            "tags": ["jwt", "authentication", "security"],
            "difficulty": "advanced"
        }
    },
    {
        "doc_id": "doc-009",
        "title": "Microservices Health Check Patterns",
        "content": """Health checks enable orchestrators to monitor service health and route traffic appropriately.
        Three types: 1) Liveness probe - is service running? 2) Readiness probe - can service handle traffic? 3) Startup probe - has service finished initialization?
        Implementation: Create dedicated /health, /ready, /live endpoints. Liveness: basic ping response. Readiness: check dependencies (database, external APIs).
        Best practices: 1) Keep checks lightweight (< 1 second). 2) Don't restart on dependency failures (readiness only). 3) Include version info in health response.
        4) Use proper HTTP status codes (200 OK, 503 Service Unavailable). For Kubernetes: configure appropriate timeouts and thresholds.""",
        "metadata": {
            "source": "architecture-docs",
            "category": "architecture",
            "pattern": "microservices",
            "tags": ["microservices", "health-check", "kubernetes"],
            "difficulty": "intermediate"
        }
    },
    {
        "doc_id": "doc-010",
        "title": "Common Error: Database Connection Timeout",
        "content": """Connection timeout errors occur when application can't establish database connection within timeout period.
        Error messages: 'Connection timeout', 'Unable to connect to database', 'Connection refused'.
        Causes: 1) Database server down or unreachable. 2) Network issues or firewall blocking. 3) Connection pool exhausted.
        4) Database under heavy load. 5) DNS resolution failures. 6) Incorrect connection string or credentials.
        Solutions: 1) Verify database server is running. 2) Check network connectivity and firewall rules. 3) Increase connection timeout setting.
        4) Increase connection pool size if exhausted. 5) Implement retry logic with exponential backoff. 6) Monitor database performance and connection metrics.""",
        "metadata": {
            "source": "error-solutions",
            "category": "error-resolution",
            "technology": "database",
            "error_type": "ConnectionTimeout",
            "tags": ["database", "connection", "timeout", "error"],
            "difficulty": "intermediate"
        }
    },
    {
        "doc_id": "doc-011",
        "title": "Python Type Hints Best Practices",
        "content": """Type hints improve code readability and enable static type checking with tools like mypy.
        Best practices: 1) Use built-in generics (list[str], dict[str, int]) in Python 3.9+. 2) Import from typing for older versions.
        3) Use Optional[T] for nullable values. 4) Use Union[A, B] for multiple types. 5) Define TypedDict for dict structures.
        6) Use Protocol for structural subtyping. 7) Annotate function return types. 8) Use reveal_type() for debugging mypy.
        Advanced: Generic types, TypeVar for generic functions, Literal for literal values, Final for constants.""",
        "metadata": {
            "source": "python-docs",
            "category": "programming",
            "language": "python",
            "tags": ["python", "type-hints", "static-typing"],
            "difficulty": "intermediate"
        }
    },
    {
        "doc_id": "doc-012",
        "title": "Elasticsearch Aggregation Queries",
        "content": """Aggregations provide analytics and statistics over Elasticsearch data.
        Types: 1) Metric aggregations (avg, sum, min, max, stats). 2) Bucket aggregations (terms, date_histogram, range).
        3) Pipeline aggregations (derivative, moving_avg, cumulative_sum). 
        Best practices: 1) Use appropriate bucket sizes for date histograms. 2) Limit terms aggregation size (default 10).
        3) Use composite aggregations for pagination. 4) Combine aggregations with filters for targeted analysis.
        5) Use doc_values for better performance. Performance: Pre-filter documents, avoid deep aggregations, use caching.""",
        "metadata": {
            "source": "elasticsearch-docs",
            "category": "database",
            "technology": "elasticsearch",
            "tags": ["elasticsearch", "aggregation", "analytics"],
            "difficulty": "advanced"
        }
    },
    {
        "doc_id": "doc-013",
        "title": "Git Rebase vs Merge: When to Use Each",
        "content": """Git rebase and merge both integrate changes but work differently.
        Merge: Creates merge commit preserving branch history. Use for: 1) Feature branches merged to main. 2) Public branches.
        3) When history preservation is important. Pros: complete history. Cons: cluttered history with many merges.
        Rebase: Replays commits on top of target branch. Use for: 1) Updating feature branch with latest main. 2) Cleaning up local commits.
        3) Before creating PR. Pros: linear history. Cons: rewrites commit history (don't rebase public branches).
        Golden rule: Never rebase commits pushed to shared branches. For feature branches: rebase locally, merge to main.""",
        "metadata": {
            "source": "git-docs",
            "category": "version-control",
            "technology": "git",
            "tags": ["git", "rebase", "merge", "workflow"],
            "difficulty": "intermediate"
        }
    },
    {
        "doc_id": "doc-014",
        "title": "Common Error: Memory Leak in Node.js",
        "content": """Memory leaks in Node.js cause application memory usage to grow unbounded until crash.
        Symptoms: 1) Steadily increasing memory usage. 2) Slower performance over time. 3) Out of memory crashes.
        Common causes: 1) Global variables accumulating data. 2) Event listeners not removed. 3) Closures holding references.
        4) Cached data without expiration. 5) Unfinished timers or intervals. 6) Large objects in module scope.
        Solutions: 1) Use heap snapshots to find leaks. 2) Remove event listeners with removeListener(). 3) Use WeakMap/WeakSet for caches.
        4) Implement cache eviction policies. 5) Clear intervals/timeouts. Tools: node --inspect, Chrome DevTools, heapdump, clinic.js.""",
        "metadata": {
            "source": "error-solutions",
            "category": "error-resolution",
            "language": "javascript",
            "technology": "nodejs",
            "error_type": "MemoryLeak",
            "tags": ["nodejs", "memory-leak", "debugging", "performance"],
            "difficulty": "advanced"
        }
    },
    {
        "doc_id": "doc-015",
        "title": "RESTful API Design Best Practices",
        "content": """RESTful APIs should follow consistent patterns for usability and maintainability.
        Key principles: 1) Use nouns for resources, not verbs (GET /users, not GET /getUsers). 2) HTTP methods for operations (GET, POST, PUT, PATCH, DELETE).
        3) Hierarchical URLs for relationships (/users/123/posts). 4) Pluralize resource names. 5) Use HTTP status codes correctly (200, 201, 400, 404, 500).
        6) Version your API (/v1/users). 7) Support filtering, sorting, pagination query params. 8) Return consistent error formats.
        Best practices: Use HTTPS, implement rate limiting, provide clear documentation, follow HATEOAS for discoverability.""",
        "metadata": {
            "source": "api-design-docs",
            "category": "architecture",
            "technology": "rest",
            "tags": ["rest", "api", "design", "best-practices"],
            "difficulty": "intermediate"
        }
    },
    {
        "doc_id": "doc-016",
        "title": "Kubernetes Pod Scheduling and Resource Management",
        "content": """Kubernetes scheduler assigns pods to nodes based on resource requirements and constraints.
        Resource requests: Minimum guaranteed resources. Resource limits: Maximum allowed resources.
        Best practices: 1) Always set requests and limits. 2) Requests should match typical usage. 3) Limits prevent resource starvation.
        4) CPU is compressible (throttled), memory is not (OOMKilled). 5) Use quality of service classes (Guaranteed, Burstable, BestEffort).
        Node affinity and anti-affinity for advanced placement. Taints and tolerations for dedicated nodes.
        Monitor actual usage and adjust requests/limits. Use Vertical Pod Autoscaler for recommendations.""",
        "metadata": {
            "source": "kubernetes-docs",
            "category": "devops",
            "technology": "kubernetes",
            "tags": ["kubernetes", "scheduling", "resources", "pod"],
            "difficulty": "advanced"
        }
    },
    {
        "doc_id": "doc-017",
        "title": "SQL Query Performance Optimization",
        "content": """Slow SQL queries impact application performance and user experience.
        Optimization techniques: 1) Add indexes on frequently queried columns. 2) Use EXPLAIN to analyze query plans.
        3) Avoid SELECT * - specify needed columns. 4) Use WHERE clause to filter early. 5) Avoid functions on indexed columns.
        6) Use JOINs instead of subqueries when possible. 7) Batch operations instead of row-by-row. 8) Use appropriate data types.
        Common issues: N+1 query problem, missing indexes, full table scans, inefficient JOINs.
        Tools: EXPLAIN ANALYZE, query profiler, slow query log. Monitor query execution time and optimize top offenders.""",
        "metadata": {
            "source": "database-docs",
            "category": "database",
            "technology": "sql",
            "tags": ["sql", "performance", "optimization", "database"],
            "difficulty": "intermediate"
        }
    },
    {
        "doc_id": "doc-018",
        "title": "Common Error: Rate Limit Exceeded",
        "content": """Rate limit errors occur when client exceeds allowed request rate to API or service.
        Error codes: HTTP 429 Too Many Requests, 'Rate limit exceeded', 'Quota exceeded'.
        Causes: 1) Too many requests in time window. 2) Inefficient client implementation making redundant calls. 3) Missing caching.
        4) Retry storms after failures. 5) Burst traffic spikes.
        Solutions: 1) Implement exponential backoff on 429 responses. 2) Cache responses when appropriate. 3) Batch requests.
        4) Use connection pooling. 5) Respect Retry-After header. 6) Implement client-side rate limiting.
        For API providers: return clear rate limit headers (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset).""",
        "metadata": {
            "source": "error-solutions",
            "category": "error-resolution",
            "technology": "api",
            "error_type": "RateLimitExceeded",
            "tags": ["rate-limit", "api", "error", "429"],
            "difficulty": "intermediate"
        }
    },
    {
        "doc_id": "doc-019",
        "title": "Testing Strategies: Unit vs Integration vs E2E",
        "content": """Different testing levels serve different purposes in quality assurance.
        Unit tests: Test individual functions/classes in isolation. Fast, many tests, mock dependencies. Focus: business logic correctness.
        Integration tests: Test components working together. Test database interactions, API integrations. Slower than unit tests.
        E2E tests: Test complete user workflows. Simulate real user interactions. Slowest, fewest tests. Focus: critical user paths.
        Testing pyramid: Many unit tests, fewer integration tests, even fewer E2E tests. Ratio guideline: 70% unit, 20% integration, 10% E2E.
        Best practices: 1) Keep tests independent. 2) Use test fixtures and factories. 3) Mock external dependencies. 4) Test edge cases and errors.""",
        "metadata": {
            "source": "testing-docs",
            "category": "testing",
            "tags": ["testing", "unit-test", "integration-test", "e2e"],
            "difficulty": "intermediate"
        }
    },
    {
        "doc_id": "doc-020",
        "title": "Monitoring and Observability Best Practices",
        "content": """Observability enables understanding system behavior through metrics, logs, and traces.
        Three pillars: 1) Metrics - quantitative measurements over time (CPU, memory, request rate). 2) Logs - discrete events with context.
        3) Traces - request flow through distributed system.
        Best practices: 1) Implement structured logging (JSON format). 2) Use consistent log levels (DEBUG, INFO, WARN, ERROR).
        3) Add correlation IDs to trace requests. 4) Monitor golden signals (latency, traffic, errors, saturation).
        5) Set up alerts on SLIs (Service Level Indicators). 6) Use dashboards for visualization. 7) Implement health checks.
        Tools: Prometheus + Grafana for metrics, ELK/Loki for logs, Jaeger/Zipkin for tracing.""",
        "metadata": {
            "source": "devops-docs",
            "category": "devops",
            "technology": "monitoring",
            "tags": ["monitoring", "observability", "metrics", "logging"],
            "difficulty": "advanced"
        }
    }
]


async def seed_knowledge_base():
    """Seed the knowledge base with initial documents."""
    print(f"Starting knowledge base seeding...")
    print(f"Elasticsearch URL: {settings.ELASTICSEARCH_URL}")
    print(f"Target index: {settings.ELASTICSEARCH_INDEX}")
    print(f"Embedding model: {settings.EMBEDDING_MODEL}")
    
    # Initialize services
    print("\nInitializing embedding service...")
    embedding_service = EmbeddingService()
    
    print("Initializing search service...")
    search_service = SearchService(embedding_service)
    await search_service.initialize()
    
    # Prepare documents for batch indexing
    print(f"\nPreparing {len(SEED_DOCUMENTS)} documents for indexing...")
    documents_to_index = []
    
    for doc in SEED_DOCUMENTS:
        # Generate embedding for the content
        full_text = f"{doc['title']} {doc['content']}"
        embedding = embedding_service.embed_text(full_text)
        
        documents_to_index.append({
            "doc_id": doc["doc_id"],
            "title": doc["title"],
            "content": doc["content"],
            "embedding": embedding,
            "metadata": doc["metadata"]
        })
        print(f"  Prepared: {doc['doc_id']} - {doc['title'][:50]}...")
    
    # Batch index documents
    print(f"\nIndexing {len(documents_to_index)} documents...")
    success_count, fail_count = await search_service.index_batch(documents_to_index)
    
    print(f"\n{'='*60}")
    print(f"Seeding completed!")
    print(f"  Successfully indexed: {success_count} documents")
    print(f"  Failed: {fail_count} documents")
    print(f"{'='*60}")
    
    # Close connections
    await search_service.close()


async def verify_seeding():
    """Verify that documents were indexed successfully."""
    print("\nVerifying indexed documents...")
    
    embedding_service = EmbeddingService()
    search_service = SearchService(embedding_service)
    await search_service.initialize()
    
    # Test semantic search
    test_query = "How do I fix connection timeout errors?"
    print(f"\nTest query: '{test_query}'")
    query_embedding = embedding_service.embed_text(test_query)
    
    results = await search_service.semantic_search(
        query_embedding=query_embedding,
        top_k=3
    )
    
    print(f"Found {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['title']} (score: {result['score']:.4f})")
        print(f"   ID: {result['doc_id']}")
        print(f"   Content: {result['content'][:100]}...")
    
    await search_service.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        asyncio.run(verify_seeding())
    else:
        asyncio.run(seed_knowledge_base())
