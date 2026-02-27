#
# Quick PowerShell Test Script for WorkflowAI Python Services
# Usage: .\test-services-quick.ps1
#

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "WorkflowAI Python Services - Quick Test" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Continue"

# Test configuration
$services = @(
    @{Name="Agent Orchestrator"; Port=8002; Url="http://localhost:8002"},
    @{Name="Indexing Service"; Port=8003; Url="http://localhost:8003"},
    @{Name="Model Service"; Port=8004; Url="http://localhost:8004"}
)

# Function to test endpoint
function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url
    )
    
    Write-Host "Testing $Name..." -NoNewline
    try {
        $response = Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec 5 -ErrorAction Stop
        Write-Host " ✓ PASS" -ForegroundColor Green
        return $true
    } catch {
        Write-Host " ✗ FAIL" -ForegroundColor Red
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Gray
        return $false
    }
}

# Function to test POST endpoint
function Test-PostEndpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string]$Body
    )
    
    Write-Host "Testing $Name..." -NoNewline
    try {
        $response = Invoke-RestMethod -Uri $Url -Method Post -Body $Body -ContentType "application/json" -TimeoutSec 10 -ErrorAction Stop
        Write-Host " ✓ PASS" -ForegroundColor Green
        Write-Host "  Response: $($response | ConvertTo-Json -Compress -Depth 2)" -ForegroundColor Gray
        return $true
    } catch {
        Write-Host " ✗ FAIL" -ForegroundColor Red
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Gray
        return $false
    }
}

# Step 1: Check Docker status
Write-Host "Step 1: Checking Docker status" -ForegroundColor Yellow
Write-Host "================================" -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    Write-Host "  Docker: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "  Docker not found or not running!" -ForegroundColor Red
    Write-Host "  Please ensure Docker Desktop is installed and running." -ForegroundColor Yellow
    exit 1
}

# Step 2: Check services
Write-Host ""
Write-Host "Step 2: Checking service containers" -ForegroundColor Yellow
Write-Host "====================================" -ForegroundColor Yellow
try {
    docker compose ps --format json | ConvertFrom-Json | ForEach-Object {
        $status = if ($_.State -eq "running") { "✓" } else { "✗" }
        $color = if ($_.State -eq "running") { "Green" } else { "Red" }
        Write-Host "  $status $($_.Service): $($_.State)" -ForegroundColor $color
    }
} catch {
    Write-Host "  Unable to get service status" -ForegroundColor Red
}

# Step 3: Health checks
Write-Host ""
Write-Host "Step 3: Running health checks" -ForegroundColor Yellow
Write-Host "==============================" -ForegroundColor Yellow

$healthResults = @()
foreach ($service in $services) {
    $result = Test-Endpoint -Name "$($service.Name) - Health" -Url "$($service.Url)/health"
    $healthResults += $result
}

# Step 4: Readiness probes
Write-Host ""
Write-Host "Step 4: Testing readiness probes" -ForegroundColor Yellow
Write-Host "=================================" -ForegroundColor Yellow

$readyResults = @()
foreach ($service in $services) {
    $result = Test-Endpoint -Name "$($service.Name) - Ready" -Url "$($service.Url)/ready"
    $readyResults += $result
}

# Step 5: API endpoints
Write-Host ""
Write-Host "Step 5: Testing API endpoints" -ForegroundColor Yellow
Write-Host "==============================" -ForegroundColor Yellow

# Agent Orchestrator - Workflow types
Test-Endpoint -Name "Agent Orchestrator - Workflow Types" -Url "http://localhost:8002/workflows/types"

# Indexing - Stats
Test-Endpoint -Name "Indexing Service - Stats" -Url "http://localhost:8003/stats"

# Model Service - Model Info
Test-Endpoint -Name "Model Service - Model Info" -Url "http://localhost:8004/model/info"

# Step 6: Functional tests
Write-Host ""
Write-Host "Step 6: Functional tests" -ForegroundColor Yellow
Write-Host "========================" -ForegroundColor Yellow

# Test indexing
$indexBody = @{
    title = "Test Document"
    content = "This is a test document for verification"
} | ConvertTo-Json

Test-PostEndpoint -Name "Indexing - Document Index" -Url "http://localhost:8003/index" -Body $indexBody

# Test search
$searchBody = @{
    query = "test document"
    top_k = 5
} | ConvertTo-Json

Test-PostEndpoint -Name "Indexing - Search" -Url "http://localhost:8003/search" -Body $searchBody

# Test generation (may timeout if model not loaded)
Write-Host "Testing Model Service - Text Generation (may take time)..." -NoNewline
$genBody = @{
    prompt = "Hello, how are"
    max_tokens = 10
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8004/generate" -Method Post -Body $genBody -ContentType "application/json" -TimeoutSec 60 -ErrorAction Stop
    Write-Host " ✓ PASS" -ForegroundColor Green
    Write-Host "  Generated: $($response.text)" -ForegroundColor Gray
} catch {
    Write-Host " ✗ FAIL (expected if model too large)" -ForegroundColor Yellow
    Write-Host "  Note: Qwen2.5-7B may be too large for testing" -ForegroundColor Gray
}

# Summary
Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$totalTests = $healthResults.Count + $readyResults.Count
$passedTests = ($healthResults | Where-Object { $_ -eq $true }).Count + ($readyResults | Where-Object { $_ -eq $true }).Count

Write-Host ""
Write-Host "Health Checks: $($healthResults | Where-Object { $_ -eq $true }).Count/$($healthResults.Count) passed" -ForegroundColor $(if ($healthResults | Where-Object { $_ -eq $true }).Count -eq $healthResults.Count) { "Green" } else { "Yellow" })
Write-Host "Readiness Probes: $($readyResults | Where-Object { $_ -eq $true }).Count/$($readyResults.Count) passed" -ForegroundColor $(if ($readyResults | Where-Object { $_ -eq $true }).Count -eq $readyResults.Count) { "Green" } else { "Yellow" })
Write-Host ""

if ($passedTests -eq $totalTests) {
    Write-Host "✓ All critical tests passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Services are healthy and ready for use." -ForegroundColor Green
} else {
    Write-Host "⚠ Some tests failed" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Check service logs:" -ForegroundColor Yellow
    Write-Host "  docker compose logs agent-orchestrator" -ForegroundColor Gray
    Write-Host "  docker compose logs indexing" -ForegroundColor Gray
    Write-Host "  docker compose logs model-service" -ForegroundColor Gray
}

Write-Host ""
Write-Host "To view live logs:" -ForegroundColor Cyan
Write-Host "  docker compose logs -f agent-orchestrator" -ForegroundColor Gray
Write-Host "  docker compose logs -f indexing" -ForegroundColor Gray
Write-Host "  docker compose logs -f model-service" -ForegroundColor Gray
Write-Host ""
