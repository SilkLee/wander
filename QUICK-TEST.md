# Quick Test Commands for Python Services

## One-Line Health Checks

```bash
# Test all health endpoints
curl http://localhost:8002/health && curl http://localhost:8003/health && curl http://localhost:8004/health
```

## Quick Verification Script (Windows PowerShell)

```powershell
# test-services-quick.ps1
Write-Host "Testing WorkflowAI Python Services..." -ForegroundColor Green

# Test Agent Orchestrator
Write-Host "`nAgent Orchestrator:" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8002/health"
    Write-Host "  Status: $($response.status)" -ForegroundColor Green
    Write-Host "  Service: $($response.service)"
} catch {
    Write-Host "  Failed: $_" -ForegroundColor Red
}

# Test Indexing
Write-Host "`nIndexing Service:" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8003/health"
    Write-Host "  Status: $($response.status)" -ForegroundColor Green
    Write-Host "  Service: $($response.service)"
    Write-Host "  Model Loaded: $($response.model_loaded)"
} catch {
    Write-Host "  Failed: $_" -ForegroundColor Red
}

# Test Model Service
Write-Host "`nModel Service:" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8004/health"
    Write-Host "  Status: $($response.status)" -ForegroundColor Green
    Write-Host "  Service: $($response.service)"
    Write-Host "  Model: $($response.model_name)"
} catch {
    Write-Host "  Failed: $_" -ForegroundColor Red
}

Write-Host "`nTest complete!" -ForegroundColor Green
```

## Quick Test: Indexing

```bash
# Index a document
curl -X POST http://localhost:8003/index \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","content":"Hello world"}'

# Search
curl -X POST http://localhost:8003/search \
  -H "Content-Type: application/json" \
  -d '{"query":"hello","top_k":5}'
```

## Quick Test: Model Service

```bash
# Generate text
curl -X POST http://localhost:8004/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Hello","max_tokens":10}'
```

## Docker Compose Commands

```bash
# Start services
cd /c/develop/workflow-ai
docker compose up -d agent-orchestrator indexing model-service

# Check status
docker compose ps

# View logs
docker compose logs -f agent-orchestrator
docker compose logs -f indexing
docker compose logs -f model-service

# Restart a service
docker compose restart agent-orchestrator

# Stop all
docker compose down
```

## Verification Checklist

Run these commands and check for success:

```bash
# 1. Health checks (should return status: healthy)
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health

# 2. Readiness (should return ready: true)
curl http://localhost:8002/ready
curl http://localhost:8003/ready
curl http://localhost:8004/ready

# 3. Basic functionality
curl http://localhost:8002/workflows/types
curl http://localhost:8003/stats
curl http://localhost:8004/model/info
```

All commands should return JSON responses without errors.
