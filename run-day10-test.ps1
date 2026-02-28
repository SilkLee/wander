#!/usr/bin/env pwsh
# WorkflowAI - Day 10 RAG Integration Test Runner for WSL
# This script starts required services, runs tests, and cleans up

Write-Host "========================================"
Write-Host "Day 10 RAG Test - WSL Runner"
Write-Host "========================================"
Write-Host ""

# Step 1: Check WSL is available
Write-Host "[1/6] Checking WSL status..." -ForegroundColor Cyan
$wslCheck = wsl --list 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  X WSL not available. Please install WSL first." -ForegroundColor Red
    exit 1
}
Write-Host "  OK WSL is available" -ForegroundColor Green

# Step 2: Convert Windows path to WSL path
Write-Host ""
Write-Host "[2/6] Setting up paths..." -ForegroundColor Cyan
$windowsPath = "C:\develop\workflow-ai"
$wslPath = wsl wslpath -a "`"$windowsPath`""
Write-Host "  Windows path: $windowsPath" -ForegroundColor Gray
Write-Host "  WSL path: $wslPath" -ForegroundColor Gray

# Step 3: Start required Docker services
Write-Host ""
Write-Host "[3/6] Starting required Docker services..." -ForegroundColor Cyan
Write-Host "  Services: elasticsearch, indexing, agent-orchestrator, model-service" -ForegroundColor Gray
wsl -e bash -c "cd $wslPath; docker-compose up -d elasticsearch indexing agent-orchestrator model-service"

if ($LASTEXITCODE -ne 0) {
    Write-Host "  X Failed to start services" -ForegroundColor Red
    exit 1
}

Write-Host "  OK Services started" -ForegroundColor Green

# Step 4: Wait for services to be ready
Write-Host ""
Write-Host "[4/6] Waiting for services to be ready (30 seconds)..." -ForegroundColor Cyan
for ($i = 30; $i -gt 0; $i--) {
    Write-Host -NoNewline "`r  Waiting... $i seconds remaining   "
    Start-Sleep -Seconds 1
}
Write-Host "`r  OK Wait complete                       " -ForegroundColor Green

# Step 5: Run the test script
Write-Host ""
Write-Host "[5/6] Running Day 10 integration tests..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Yellow
wsl -e bash -c "cd $wslPath; bash test-day10-rag.sh"
$testExitCode = $LASTEXITCODE

Write-Host "========================================" -ForegroundColor Yellow

if ($testExitCode -eq 0) {
    Write-Host "  OK All tests passed!" -ForegroundColor Green
} else {
    Write-Host "  Warning: Some tests failed (exit code: $testExitCode)" -ForegroundColor Yellow
}

# Step 6: Stop Docker services to free resources
Write-Host ""
Write-Host "[6/6] Stopping Docker services to free resources..." -ForegroundColor Cyan
wsl -e bash -c "cd $wslPath; docker-compose stop"

if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK All services stopped" -ForegroundColor Green
} else {
    Write-Host "  Warning: Failed to stop some services" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Day 10 Test Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Summary
if ($testExitCode -eq 0) {
    Write-Host "OK Status: ALL TESTS PASSED" -ForegroundColor Green
} else {
    Write-Host "Warning: Status: SOME TESTS FAILED" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "To view running containers:" -ForegroundColor Gray
Write-Host "  wsl -d Ubuntu -e docker ps" -ForegroundColor Gray
Write-Host ""
Write-Host "To view logs:" -ForegroundColor Gray
Write-Host "  wsl -d Ubuntu -e bash -c 'cd $wslPath; docker-compose logs -f'" -ForegroundColor Gray
Write-Host ""

exit $testExitCode
