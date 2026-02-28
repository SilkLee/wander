# WorkflowAI - Day 10 Integration Test Runner (Docker Internal Network)
# Bypasses corporate proxy by running tests inside Docker network

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Blue
Write-Host "Day 10 RAG Integration Test (Internal)" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

# Step 1: Ensure we're in the correct directory
$projectRoot = "C:\develop\workflow-ai"
if (-not (Test-Path $projectRoot)) {
    Write-Host "ERROR: Project directory not found: $projectRoot" -ForegroundColor Red
    exit 1
}

Set-Location $projectRoot

# Step 2: Check if test script exists
if (-not (Test-Path "test-day10-internal.sh")) {
    Write-Host "ERROR: test-day10-internal.sh not found" -ForegroundColor Red
    exit 1
}

# Step 3: Build and start services
Write-Host "[1/5] Building Docker images..." -ForegroundColor Cyan
wsl -d xde-22 -e bash -c "cd /mnt/c/develop/workflow-ai && docker-compose build indexing agent-orchestrator"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker build failed" -ForegroundColor Red
    exit 1
}

Write-Host "[2/5] Starting services (elasticsearch, redis, indexing, agent-orchestrator)..." -ForegroundColor Cyan
wsl -d xde-22 -e bash -c "cd /mnt/c/develop/workflow-ai && docker-compose up -d elasticsearch redis indexing agent-orchestrator"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker compose up failed" -ForegroundColor Red
    exit 1
}

# Step 4: Wait for services to initialize
Write-Host "[3/5] Waiting 30 seconds for services to initialize..." -ForegroundColor Cyan
Write-Host "  (Embedding model needs to load - this is normal)" -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Step 5: Run tests inside Docker network
Write-Host "[4/5] Running integration tests..." -ForegroundColor Cyan
Write-Host ""

# Copy test script to a container and execute it
$testResult = wsl -d xde-22 -e bash -c "cd /mnt/c/develop/workflow-ai && docker cp test-day10-internal.sh workflowai-indexing:/tmp/test.sh && docker exec workflowai-indexing bash /tmp/test.sh"

$exitCode = $LASTEXITCODE

Write-Host ""

# Step 6: Stop services
Write-Host "[5/5] Stopping Docker services..." -ForegroundColor Cyan
wsl -d xde-22 -e bash -c "cd /mnt/c/develop/workflow-ai && docker-compose stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Blue
Write-Host "Test Complete - Services Stopped" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

if ($exitCode -eq 0) {
    Write-Host "SUCCESS: All tests passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Day 10 RAG Implementation Verified:" -ForegroundColor Green
    Write-Host "  - Elasticsearch knowledge base operational" -ForegroundColor White
    Write-Host "  - Hybrid search (semantic + keyword) working" -ForegroundColor White
    Write-Host "  - RAG pipeline integrated with Agent" -ForegroundColor White
    Write-Host "  - Context-aware log analysis functional" -ForegroundColor White
    Write-Host ""
    exit 0
} else {
    Write-Host "FAILED: Some tests failed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Check logs: docker-compose logs" -ForegroundColor White
    Write-Host "  2. Verify build: docker-compose build --no-cache indexing" -ForegroundColor White
    Write-Host "  3. Manual test: docker exec workflowai-indexing bash" -ForegroundColor White
    Write-Host ""
    exit 1
}
