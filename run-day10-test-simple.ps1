#!/usr/bin/env pwsh
# WorkflowAI - Day 10 RAG Integration Test Runner (Simplified)
# Tests only Elasticsearch + Indexing Service (no model-service build needed)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Day 10 RAG Test - Simplified (Indexing Only)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Get WSL path
Write-Host "[1/5] Setting up paths..." -ForegroundColor Cyan
$windowsPath = "C:\develop\workflow-ai"
$wslPath = wsl wslpath -a "`"$windowsPath`""
Write-Host "  Windows path: $windowsPath" -ForegroundColor Gray
Write-Host "  WSL path: $wslPath" -ForegroundColor Gray

# Step 2: Start only Elasticsearch + Indexing Service  
Write-Host ""
Write-Host "[2/5] Starting Docker services (Elasticsearch + Indexing only)..." -ForegroundColor Cyan
Write-Host "  Note: Skipping model-service to avoid long build time" -ForegroundColor Gray
wsl -e bash -c "cd $wslPath; docker-compose up -d elasticsearch indexing"

if ($LASTEXITCODE -ne 0) {
    Write-Host "  X Failed to start services" -ForegroundColor Red
    exit 1
}

Write-Host "  OK Services started" -ForegroundColor Green

# Step 3: Wait for services to be ready
Write-Host ""
Write-Host "[3/5] Waiting for services to be ready (45 seconds)..." -ForegroundColor Cyan
Write-Host "  Elasticsearch needs time to start and Indexing needs to load embedding model..." -ForegroundColor Gray
for ($i = 45; $i -gt 0; $i--) {
    Write-Host -NoNewline "`r  Waiting... $i seconds remaining   "
    Start-Sleep -Seconds 1
}
Write-Host "`r  OK Wait complete                       " -ForegroundColor Green

# Step 4: Test Elasticsearch + Indexing Service + Knowledge Base
Write-Host ""
Write-Host "[4/5] Running simplified tests..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Yellow

$INDEXING_URL = "http://localhost:8003"
$ES_URL = "http://localhost:9200"
$allPassed = $true

# Test 1: Elasticsearch Health
Write-Host ""
Write-Host "Test 1: Elasticsearch Health..." -ForegroundColor White
try {
    $response = Invoke-WebRequest -Uri "$ES_URL/_cluster/health" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "  OK Elasticsearch is healthy (HTTP 200)" -ForegroundColor Green
    } else {
        Write-Host "  X Elasticsearch returned HTTP $($response.StatusCode)" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host "  X Elasticsearch not accessible: $($_.Exception.Message)" -ForegroundColor Red
    $allPassed = $false
}

# Test 2: Indexing Service Health
Write-Host ""
Write-Host "Test 2: Indexing Service Health..." -ForegroundColor White
try {
    $response = Invoke-WebRequest -Uri "$INDEXING_URL/health" -UseBasicParsing -TimeoutSec 5
    $health = $response.Content | ConvertFrom-Json
    if ($health.status -eq "healthy") {
        Write-Host "  OK Indexing Service is healthy" -ForegroundColor Green
        if ($health.elasticsearch_connected) {
            Write-Host "    - Elasticsearch connected: YES" -ForegroundColor Gray
        } else {
            Write-Host "    - Elasticsearch connected: NO" -ForegroundColor Yellow
        }
        if ($health.model_loaded) {
            Write-Host "    - Embedding model loaded: YES" -ForegroundColor Gray
        } else {
            Write-Host "    - Embedding model loaded: NO (still loading)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  X Indexing Service unhealthy" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host "  X Indexing Service not accessible: $($_.Exception.Message)" -ForegroundColor Red
    $allPassed = $false
}

# Test 3: Populate Knowledge Base
Write-Host ""
Write-Host "Test 3: Knowledge Base Population..." -ForegroundColor White
Write-Host "  Running populate_kb.py script..." -ForegroundColor Gray
wsl -e bash -c "cd $wslPath/services/indexing; python3 populate_kb.py"

if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK Knowledge base populated successfully" -ForegroundColor Green
} else {
    Write-Host "  X Failed to populate knowledge base (exit code: $LASTEXITCODE)" -ForegroundColor Red
    $allPassed = $false
}

# Test 4: Check Knowledge Base Stats
Write-Host ""
Write-Host "Test 4: Knowledge Base Statistics..." -ForegroundColor White
try {
    $response = Invoke-WebRequest -Uri "$INDEXING_URL/stats" -UseBasicParsing -TimeoutSec 5
    $stats = $response.Content | ConvertFrom-Json
    Write-Host "  OK Knowledge Base Stats:" -ForegroundColor Green
    Write-Host "    - Document count: $($stats.document_count)" -ForegroundColor Gray
    Write-Host "    - Index name: $($stats.index)" -ForegroundColor Gray
    Write-Host "    - Index size: $([math]::Round($stats.size_bytes/1MB, 2)) MB" -ForegroundColor Gray
    
    if ($stats.document_count -lt 10) {
        Write-Host "  Warning: Less than 10 documents in knowledge base" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  X Failed to get stats: $($_.Exception.Message)" -ForegroundColor Red
    $allPassed = $false
}

# Test 5: Test Hybrid Search
Write-Host ""
Write-Host "Test 5: Hybrid Search Test..." -ForegroundColor White
try {
    $searchBody = @{
        query = "NullPointerException error in Java"
        top_k = 3
        search_type = "hybrid"
    } | ConvertTo-Json
    
    $response = Invoke-WebRequest -Uri "$INDEXING_URL/search" -Method POST -Body $searchBody -ContentType "application/json" -UseBasicParsing -TimeoutSec 10
    $searchResults = $response.Content | ConvertFrom-Json
    
    if ($searchResults.results -and $searchResults.results.Count -gt 0) {
        Write-Host "  OK Hybrid search returned $($searchResults.results.Count) results" -ForegroundColor Green
        Write-Host "    - Top result: $($searchResults.results[0].title)" -ForegroundColor Gray
        Write-Host "    - Score: $([math]::Round($searchResults.results[0].score, 4))" -ForegroundColor Gray
    } else {
        Write-Host "  X Hybrid search returned no results" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host "  X Hybrid search failed: $($_.Exception.Message)" -ForegroundColor Red
    $allPassed = $false
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow

# Step 5: Stop services to free resources
Write-Host ""
Write-Host "[5/5] Stopping Docker services to free resources..." -ForegroundColor Cyan
wsl -e bash -c "cd $wslPath; docker-compose stop"

if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK All services stopped" -ForegroundColor Green
} else {
    Write-Host "  Warning: Failed to stop some services" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Day 10 Simplified Test Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Summary
if ($allPassed) {
    Write-Host "OK Status: ALL TESTS PASSED" -ForegroundColor Green
    Write-Host ""
    Write-Host "Note: This test only covered Elasticsearch + Indexing Service." -ForegroundColor Gray
    Write-Host "For full Agent + Model Service testing, run: ./test-day10-rag.sh" -ForegroundColor Gray
    exit 0
} else {
    Write-Host "FAIL Status: SOME TESTS FAILED" -ForegroundColor Red
    exit 1
}
