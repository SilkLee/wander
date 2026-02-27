# Day 7 - Model Service Build and Test Script
# Run this in PowerShell to build, start, and test the Model Service

$ErrorActionPreference = "Stop"

Write-Host "`n========================================" -ForegroundColor Blue
Write-Host "Day 7: Model Service - Build & Test" -ForegroundColor Blue
Write-Host "========================================`n" -ForegroundColor Blue

# Step 1: Build Model Service
Write-Host "[Step 1/5] Building Model Service Docker image..." -ForegroundColor Yellow
Write-Host "Using gpt2 model (~500MB download during first run)" -ForegroundColor Cyan
Write-Host ""

cd C:\develop\workflow-ai

try {
    docker compose build model-service
    if ($LASTEXITCODE -ne 0) {
        throw "Docker build failed"
    }
    Write-Host "`n✓ Model Service image built successfully" -ForegroundColor Green
} catch {
    Write-Host "`n✗ Build failed: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Start Model Service
Write-Host "`n[Step 2/5] Starting Model Service container..." -ForegroundColor Yellow
Write-Host "This will download gpt2 model on first run (may take 2-3 minutes)" -ForegroundColor Cyan
Write-Host ""

try {
    docker compose up -d model-service
    if ($LASTEXITCODE -ne 0) {
        throw "Docker start failed"
    }
    Write-Host "✓ Container started" -ForegroundColor Green
} catch {
    Write-Host "✗ Start failed: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Wait for model loading
Write-Host "`n[Step 3/5] Waiting for model to load..." -ForegroundColor Yellow
Write-Host "Checking health every 10 seconds..." -ForegroundColor Cyan

$maxAttempts = 30  # 5 minutes
$attempt = 0
$healthy = $false

while ($attempt -lt $maxAttempts) {
    $attempt++
    Write-Host "  Attempt $attempt/$maxAttempts..." -NoNewline
    
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8004/health" -Method Get -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($response.model_loaded -eq $true) {
            Write-Host " ✓ Model loaded!" -ForegroundColor Green
            $healthy = $true
            break
        } else {
            Write-Host " Model loading..." -ForegroundColor Yellow
        }
    } catch {
        Write-Host " Service not ready yet" -ForegroundColor Yellow
    }
    
    Start-Sleep -Seconds 10
}

if (-not $healthy) {
    Write-Host "`n✗ Model failed to load within 5 minutes" -ForegroundColor Red
    Write-Host "Check logs: docker compose logs model-service" -ForegroundColor Yellow
    exit 1
}

# Step 4: Run health checks
Write-Host "`n[Step 4/5] Running health checks..." -ForegroundColor Yellow

try {
    # Health check
    Write-Host "`n  Testing /health endpoint..." -NoNewline
    $health = Invoke-RestMethod -Uri "http://localhost:8004/health" -Method Get
    if ($health.status -eq "healthy") {
        Write-Host " ✓" -ForegroundColor Green
        Write-Host "    Status: $($health.status)"
        Write-Host "    Model: $($health.model_name)"
        Write-Host "    Loaded: $($health.model_loaded)"
    } else {
        throw "Health check failed"
    }
    
    # Model info
    Write-Host "`n  Testing /model/info endpoint..." -NoNewline
    $info = Invoke-RestMethod -Uri "http://localhost:8004/model/info" -Method Get
    Write-Host " ✓" -ForegroundColor Green
    Write-Host "    Name: $($info.name)"
    Write-Host "    Type: $($info.type)"
    Write-Host "    Device: $($info.device)"
    
    # Liveness
    Write-Host "`n  Testing /live endpoint..." -NoNewline
    $live = Invoke-RestMethod -Uri "http://localhost:8004/live" -Method Get
    if ($live.alive -eq $true) {
        Write-Host " ✓" -ForegroundColor Green
    }
    
    # Readiness
    Write-Host "  Testing /ready endpoint..." -NoNewline
    $ready = Invoke-RestMethod -Uri "http://localhost:8004/ready" -Method Get
    if ($ready.ready -eq $true) {
        Write-Host " ✓" -ForegroundColor Green
    }
    
} catch {
    Write-Host " ✗" -ForegroundColor Red
    Write-Host "Health check failed: $_" -ForegroundColor Red
    exit 1
}

# Step 5: Test text generation
Write-Host "`n[Step 5/5] Testing text generation..." -ForegroundColor Yellow

try {
    $body = @{
        prompt = "Hello, how are you?"
        max_tokens = 30
        temperature = 0.7
    } | ConvertTo-Json
    
    Write-Host "`n  Generating text..." -NoNewline
    $result = Invoke-RestMethod -Uri "http://localhost:8004/generate" `
        -Method Post `
        -ContentType "application/json" `
        -Body $body `
        -TimeoutSec 30
    
    Write-Host " ✓" -ForegroundColor Green
    Write-Host "`n  Prompt: $($result.prompt)"
    Write-Host "  Generated: $($result.text)"
    Write-Host "  Tokens: $($result.tokens_generated)"
    Write-Host "  Finish: $($result.finish_reason)"
    
} catch {
    Write-Host " ✗" -ForegroundColor Red
    Write-Host "Generation failed: $_" -ForegroundColor Red
    exit 1
}

# Success summary
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "✓ All tests passed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Write-Host "`nModel Service is running on http://localhost:8004" -ForegroundColor Cyan
Write-Host ""
Write-Host "Available endpoints:" -ForegroundColor Yellow
Write-Host "  GET  /health         - Health check"
Write-Host "  GET  /model/info     - Model information"
Write-Host "  POST /generate       - Text generation"
Write-Host "  GET  /live           - Liveness probe"
Write-Host "  GET  /ready          - Readiness probe"
Write-Host ""

Write-Host "Via API Gateway (requires JWT):" -ForegroundColor Yellow
Write-Host "  POST http://localhost:8000/api/v1/generate"
Write-Host "  GET  http://localhost:8000/api/v1/model/info"
Write-Host ""

Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. To use Qwen2.5-7B instead of gpt2:"
Write-Host "   - Download model to C:\develop\Qwen2.5-7B-Instruct"
Write-Host "   - Uncomment volume mount in docker-compose.yml"
Write-Host "   - Set MODEL_NAME=Qwen/Qwen2.5-7B-Instruct"
Write-Host "   - Set LOCAL_MODEL_PATH=/app/models/qwen"
Write-Host "   - Rebuild: docker compose build model-service"
Write-Host "   - Restart: docker compose up -d model-service"
Write-Host ""
Write-Host "2. View logs: docker compose logs -f model-service"
Write-Host "3. Stop service: docker compose stop model-service"
Write-Host ""
