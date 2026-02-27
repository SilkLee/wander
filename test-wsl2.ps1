# WSL2 Test Script for Day 5 Ingestion Pipeline

Write-Host "=================================================="
Write-Host "WorkflowAI Day 5 - WSL2 Environment Test"
Write-Host "=================================================="
Write-Host ""

Write-Host "[1] Checking WSL2 Environment..." -ForegroundColor Yellow
wsl --version

Write-Host ""
Write-Host "[2] Starting Docker Services in WSL2..." -ForegroundColor Yellow
wsl -e bash -c "cd /mnt/c/develop/workflow-ai && docker compose up -d redis ingestion agent-orchestrator 2>&1"

Write-Host ""
Write-Host "[3] Waiting for services to be ready (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host ""
Write-Host "[4] Checking Docker containers..." -ForegroundColor Yellow
wsl -e bash -c "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"

Write-Host ""
Write-Host "[5] Running E2E Test..." -ForegroundColor Yellow
wsl -e bash -c "cd /mnt/c/develop/workflow-ai && bash test-ingestion-e2e.sh"

Write-Host ""
Write-Host "=================================================="
Write-Host "Test Complete - Check output above"
Write-Host "=================================================="
