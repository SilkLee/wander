# Python Services Testing Guide

This guide provides comprehensive testing procedures for the three Python microservices.

## Quick Start

### Prerequisites
- Docker Desktop installed and running
- Docker Compose v2.x
- WSL2 (for Windows)
- At least 8GB RAM available
- OPENAI_API_KEY environment variable (optional, for agent tests)

### 1. Start All Services

```bash
cd /c/develop/workflow-ai

# Start infrastructure
docker compose up -d postgres redis elasticsearch

# Wait 30 seconds for infrastructure to be ready
sleep 30

# Build Python services
docker compose build agent-orchestrator indexing model-service

# Start Python services
docker compose up -d agent-orchestrator indexing model-service

# Wait 60 seconds for services to initialize
sleep 60
```

### 2. Run Automated Tests

```bash
# Make script executable
chmod +x test-services.sh

# Run tests
./test-services.sh
```

---

## Manual Testing

### Check Service Status

```bash
# View running containers
docker compose ps

# Expected output:
# workflowai-agent          running   0.0.0.0:8002->8002/tcp
# workflowai-indexing       running   0.0.0.0:8003->8003/tcp
# workflowai-model          running   0.0.0.0:8004->8004/tcp
```

### Health Checks

```bash
# Agent Orchestrator
curl http://localhost:8002/health
# Expected: {"status":"healthy","service":"agent-orchestrator",...}

# Indexing Service
curl http://localhost:8003/health
# Expected: {"status":"healthy","service":"indexing",...}

# Model Service
curl http://localhost:8004/health
# Expected: {"status":"healthy","service":"model-service",...}
```

### Readiness Probes

```bash
curl http://localhost:8002/ready
curl http://localhost:8003/ready
curl http://localhost:8004/ready
# Expected: {"ready":true}
```

---

## Service-Specific Tests

### Agent Orchestrator Tests

#### 1. Get Workflow Types
```bash
curl http://localhost:8002/workflows/types
```

**Expected Response**:
```json
{
  "workflows": [
    {
      "type": "log_analysis",
      "name": "Log Analysis",
      "status": "available"
    }
  ]
}
```

#### 2. Analyze Build Log (requires OPENAI_API_KEY)
```bash
curl -X POST http://localhost:8002/workflows/analyze-log \
  -H "Content-Type: application/json" \
  -d '{
    "log_content": "ERROR: NullPointerException at com.example.App.main(App.java:42)",
    "log_type": "build"
  }'
```

**Expected Response**:
```json
{
  "analysis_id": "uuid",
  "root_cause": "NullPointerException in main method",
  "severity": "high",
  "suggested_fixes": ["Check null values...", "..."],
  "confidence": 0.75
}
```

---

### Indexing Service Tests

#### 1. Index a Document
```bash
curl -X POST http://localhost:8003/index \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Python TypeError Fix",
    "content": "TypeError usually occurs when you try to perform an operation on incompatible types. Check your variable types and ensure type compatibility.",
    "metadata": {
      "source": "stackoverflow",
      "tags": ["python", "error", "type"]
    }
  }'
```

**Expected Response**:
```json
{
  "id": "uuid",
  "indexed": true,
  "embedding_dimension": 384
}
```

#### 2. Search Documents
```bash
curl -X POST http://localhost:8003/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "python type error",
    "top_k": 5,
    "search_type": "hybrid"
  }'
```

**Expected Response**:
```json
{
  "query": "python type error",
  "results": [
    {
      "id": "uuid",
      "title": "Python TypeError Fix",
      "content": "TypeError usually occurs...",
      "score": 0.85,
      "source": "stackoverflow"
    }
  ],
  "total": 1,
  "search_type": "hybrid"
}
```

#### 3. Batch Index
```bash
curl -X POST http://localhost:8003/index/batch \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "title": "Java NullPointerException",
        "content": "NPE occurs when dereferencing a null object reference.",
        "metadata": {"source": "docs", "tags": ["java", "error"]}
      },
      {
        "title": "Go nil pointer",
        "content": "Nil pointer dereference in Go causes panic.",
        "metadata": {"source": "docs", "tags": ["go", "error"]}
      }
    ]
  }'
```

**Expected Response**:
```json
{
  "indexed_count": 2,
  "failed_count": 0,
  "document_ids": ["uuid1", "uuid2"]
}
```

#### 4. Get Statistics
```bash
curl http://localhost:8003/stats
```

**Expected Response**:
```json
{
  "index": "knowledge_base",
  "document_count": 3,
  "size_bytes": 12345,
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "embedding_dimension": 384
}
```

---

### Model Service Tests

#### 1. Get Model Info
```bash
curl http://localhost:8004/model/info
```

**Expected Response**:
```json
{
  "name": "Qwen/Qwen2.5-7B-Instruct",
  "type": "transformers",
  "device": "cpu",
  "max_length": 4096,
  "parameters": {
    "default_max_tokens": 512,
    "default_temperature": 0.7,
    "default_top_p": 0.9
  }
}
```

#### 2. Generate Text
```bash
curl -X POST http://localhost:8004/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Hello, how are you",
    "max_tokens": 20,
    "temperature": 0.7
  }'
```

**Expected Response**:
```json
{
  "text": " today? I hope you're having a great day!",
  "prompt": "Hello, how are you",
  "tokens_generated": 12,
  "finish_reason": "stop"
}
```

**Note**: Model loading can take 1-5 minutes depending on hardware. First request will be slow.

---

## Troubleshooting

### Service Won't Start

#### Check Logs
```bash
# View recent logs
docker compose logs agent-orchestrator
docker compose logs indexing
docker compose logs model-service

# Follow live logs
docker compose logs -f agent-orchestrator
```

#### Common Issues

**1. Port Already in Use**
```bash
# Check what's using the port
netstat -ano | findstr :8002

# Kill the process or change port in docker-compose.yml
```

**2. Out of Memory**
```bash
# Check Docker memory allocation
docker stats

# Reduce model size in .env:
# MODEL_NAME=gpt2  # Use smaller model for testing
```

**3. Elasticsearch Not Ready**
```bash
# Check Elasticsearch health
curl http://localhost:9200/_cluster/health

# Restart if unhealthy
docker compose restart elasticsearch
```

**4. Model Download Failure**
```bash
# Model service logs will show download progress
docker compose logs model-service

# Manual download (in container):
docker compose exec model-service python -c "from transformers import AutoModel; AutoModel.from_pretrained('Qwen/Qwen2.5-7B-Instruct')"
```

### Service Starts But Not Responding

#### Increase Timeouts
Services need time to load models. Wait 2-3 minutes after startup.

#### Check Health Endpoints
```bash
# All should return 200 OK
curl -I http://localhost:8002/health
curl -I http://localhost:8003/health
curl -I http://localhost:8004/health
```

#### Restart Service
```bash
docker compose restart agent-orchestrator
```

### Agent Orchestrator Errors

**OpenAI API Key Missing**
```bash
# Set environment variable
export OPENAI_API_KEY=sk-your-key-here

# Restart service
docker compose restart agent-orchestrator
```

**Redis Connection Failed**
```bash
# Check Redis
docker compose logs redis

# Restart Redis
docker compose restart redis
```

### Indexing Service Errors

**Elasticsearch Connection Failed**
```bash
# Check Elasticsearch
curl http://localhost:9200

# Restart Elasticsearch
docker compose restart elasticsearch
```

**Model Loading Error**
```bash
# Check available disk space (models need 1-2GB)
df -h

# Use smaller embedding model in .env:
# EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### Model Service Errors

**CUDA Not Available**
```bash
# Expected on CPU-only systems
# Service will automatically fall back to CPU

# Check logs for confirmation
docker compose logs model-service | grep "CUDA"
```

**Model Too Large**
```bash
# Use smaller model for testing
# Edit services/model-service/.env:
# MODEL_NAME=gpt2

# Rebuild and restart
docker compose build model-service
docker compose restart model-service
```

---

## Performance Benchmarks

### Expected Response Times (CPU)

| Service | Endpoint | Expected Time |
|---------|----------|---------------|
| Agent Orchestrator | /health | < 100ms |
| Agent Orchestrator | /workflows/analyze-log | 2-5s (with OpenAI) |
| Indexing | /health | < 100ms |
| Indexing | /index | 200-500ms |
| Indexing | /search | 100-300ms |
| Model Service | /health | < 100ms |
| Model Service | /generate (20 tokens) | 5-30s (CPU) |

### Expected Startup Times

| Service | First Start | Restart |
|---------|-------------|---------|
| Agent Orchestrator | 30-60s | 10-20s |
| Indexing | 60-120s (model download) | 20-30s |
| Model Service | 120-300s (model download) | 30-60s |

---

## Integration Test Suite

### End-to-End Workflow Test

```bash
#!/bin/bash

echo "1. Index knowledge base"
curl -X POST http://localhost:8003/index \
  -H "Content-Type: application/json" \
  -d '{"title":"NPE Fix","content":"NullPointerException: check for null before dereferencing"}'

echo -e "\n2. Search knowledge base"
curl -X POST http://localhost:8003/search \
  -H "Content-Type: application/json" \
  -d '{"query":"null pointer exception","top_k":1}'

echo -e "\n3. Analyze log (requires OpenAI)"
curl -X POST http://localhost:8002/workflows/analyze-log \
  -H "Content-Type: application/json" \
  -d '{"log_content":"ERROR: NullPointerException at line 42","log_type":"build"}'

echo -e "\n4. Generate text"
curl -X POST http://localhost:8004/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Fix NullPointerException by","max_tokens":30}'

echo -e "\nAll tests complete!"
```

Save as `test-integration.sh`, make executable, and run:
```bash
chmod +x test-integration.sh
./test-integration.sh
```

---

## Cleanup

### Stop Services
```bash
# Stop all services
docker compose down

# Stop and remove volumes
docker compose down -v
```

### Remove Images
```bash
# Remove Python service images
docker rmi workflowai-agent:latest
docker rmi workflowai-indexing:latest
docker rmi workflowai-model:latest
```

### Free Up Space
```bash
# Remove unused Docker resources
docker system prune -a --volumes
```

---

## Success Criteria

✅ **All services must:**
1. Start without errors
2. Respond to health checks within 100ms
3. Pass readiness probes
4. Accept and process API requests
5. Return valid JSON responses

✅ **Indexing Service must:**
1. Successfully index documents
2. Generate embeddings (384-dimensional)
3. Perform hybrid search with results
4. Report correct statistics

✅ **Model Service must:**
1. Load model successfully
2. Generate coherent text
3. Respect max_tokens parameter
4. Complete generation within timeout

✅ **Agent Orchestrator must:**
1. List available workflows
2. Execute log analysis (with OpenAI key)
3. Return structured analysis results
4. Use KB tool for similar issues

---

## Verification Checklist

```
[ ] All services start without errors
[ ] Health endpoints return 200 OK
[ ] Readiness probes return true
[ ] Agent Orchestrator lists workflows
[ ] Indexing service indexes documents
[ ] Indexing service searches successfully
[ ] Model service generates text
[ ] No error messages in logs
[ ] Services restart successfully
[ ] Integration test passes
```

---

## Next Steps After Testing

1. **If all tests pass**: Mark Day 4 complete, proceed to Day 5
2. **If issues found**: Debug using logs and troubleshooting guide
3. **If critical failures**: Report issues with logs attached

**Completion Report**: `docs/day4-python-services-completion.md`
