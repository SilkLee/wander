# Day 4 Testing - Execution Guide

**Date**: 2026-02-27  
**Status**: ✅ Testing Infrastructure Complete  
**Action Required**: User execution in Docker-enabled environment

---

## Testing Infrastructure Summary

All testing infrastructure has been created and is ready for execution:

### Files Created
1. **`test-services.sh`** (246 lines) - Comprehensive Bash test suite
2. **`test-services-quick.ps1`** (192 lines) - PowerShell quick test script (NEW)
3. **`docs/TESTING.md`** (557 lines) - Complete testing documentation
4. **`QUICK-TEST.md`** (118 lines) - Quick reference guide
5. **`docs/TEST-RESULTS.md`** (340 lines) - Expected results documentation

### Services Ready
- ✅ **Agent Orchestrator** (Port 8002) - 13 files, ~1,100 LOC
- ✅ **Indexing Service** (Port 8003) - 11 files, ~1,000 LOC
- ✅ **Model Service** (Port 8004) - 7 files, ~420 LOC

### Docker Configuration
- ✅ All services configured in `docker-compose.yml`
- ✅ Environment variables set
- ✅ Health checks defined
- ✅ Cache volumes created
- ✅ Service dependencies mapped

---

## Execution Options

### Option 1: Automated Bash Test (Recommended)

**Requirements**: WSL2 or Git Bash with Docker access

```bash
# Navigate to project
cd /c/develop/workflow-ai

# Make script executable
chmod +x test-services.sh

# Run full test suite
./test-services.sh
```

**Features**:
- ✅ Starts all infrastructure (PostgreSQL, Redis, Elasticsearch)
- ✅ Builds Python services with uv
- ✅ Waits for services to be ready (with retries)
- ✅ Runs health checks
- ✅ Tests all API endpoints
- ✅ Performs functional tests (index, search, generate)
- ✅ Displays service logs
- ✅ Reports pass/fail with colored output

**Expected Duration**: 5-10 minutes (includes model loading)

---

### Option 2: PowerShell Quick Test (Windows)

**Requirements**: PowerShell + Docker Desktop running

```powershell
# Navigate to project
cd C:\develop\workflow-ai

# Start infrastructure services first
docker compose up -d postgres redis elasticsearch
Start-Sleep -Seconds 30

# Build and start Python services
docker compose build agent-orchestrator indexing model-service
docker compose up -d agent-orchestrator indexing model-service

# Wait for services to load (especially model service)
Start-Sleep -Seconds 120

# Run quick test script
.\test-services-quick.ps1
```

**Features**:
- ✅ Quick health checks (all 3 services)
- ✅ Readiness probe tests
- ✅ API endpoint verification
- ✅ Basic functional tests
- ✅ Colored pass/fail output
- ✅ Service status summary

**Expected Duration**: 3-5 minutes (after services are running)

---

### Option 3: Manual Testing

**Requirements**: curl or PowerShell Invoke-RestMethod

#### Step 1: Start Services
```bash
# Start infrastructure
docker compose up -d postgres redis elasticsearch
sleep 30

# Start Python services
docker compose up -d agent-orchestrator indexing model-service
sleep 60
```

#### Step 2: Health Checks
```bash
# Test each service
curl http://localhost:8002/health  # Agent Orchestrator
curl http://localhost:8003/health  # Indexing
curl http://localhost:8004/health  # Model Service
```

**Expected Response** (all services):
```json
{
  "status": "healthy",
  "service": "agent-orchestrator|indexing|model-service",
  "version": "0.1.0",
  ...
}
```

#### Step 3: Readiness Checks
```bash
curl http://localhost:8002/ready
curl http://localhost:8003/ready
curl http://localhost:8004/ready
```

**Expected Response**:
```json
{
  "ready": true,
  "service": "..."
}
```

#### Step 4: Functional Tests

**Test Indexing**:
```bash
# Index a document
curl -X POST http://localhost:8003/index \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","content":"Test document for verification"}'

# Expected: {"id":"uuid","indexed":true,"embedding_dimension":384}

# Search
curl -X POST http://localhost:8003/search \
  -H "Content-Type: application/json" \
  -d '{"query":"test","top_k":5}'

# Expected: {"query":"test","results":[...],"total":1}
```

**Test Model Service**:
```bash
# Get model info
curl http://localhost:8004/model/info

# Expected: {"model_name":"Qwen/Qwen2.5-7B-Instruct","device":"cpu",...}

# Generate text (may timeout if model too large)
curl -X POST http://localhost:8004/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Hello","max_tokens":10}'

# Expected: {"text":"...","tokens_generated":10,...}
```

**Test Agent Orchestrator**:
```bash
# List workflow types
curl http://localhost:8002/workflows/types

# Expected: {"workflows":["log-analysis"]}
```

---

## Current Environment Limitation

**Issue**: Docker is not available in the current Git Bash environment.

**Detection**:
```bash
$ docker --version
/usr/bin/bash: line 1: docker: command not found
```

**Impact**: 
- ❌ Cannot execute automated tests from current shell
- ✅ All test scripts and services are ready
- ✅ User can execute tests in Docker-enabled environment

**Solution**:
1. Open WSL2 terminal, OR
2. Open PowerShell with Docker Desktop running
3. Execute one of the test options above

---

## Verification Checklist

To mark Day 4 testing as complete, verify:

- [ ] **Infrastructure Services**:
  - [ ] PostgreSQL responding on port 5432
  - [ ] Redis responding on port 6379
  - [ ] Elasticsearch responding on port 9200

- [ ] **Python Services**:
  - [ ] Agent Orchestrator healthy on port 8002
  - [ ] Indexing Service healthy on port 8003
  - [ ] Model Service healthy on port 8004

- [ ] **Health Checks**:
  - [ ] All `/health` endpoints return `status: "healthy"`
  - [ ] All `/ready` endpoints return `ready: true`
  - [ ] All `/live` endpoints return `alive: true`

- [ ] **API Functionality**:
  - [ ] Agent Orchestrator lists workflow types
  - [ ] Indexing Service can index documents
  - [ ] Indexing Service can search documents
  - [ ] Model Service returns model info
  - [ ] Model Service can generate text (optional if model too large)

- [ ] **Service Stability**:
  - [ ] No critical errors in logs
  - [ ] Services can restart successfully
  - [ ] Docker Compose shows all services as "running"

---

## Troubleshooting

### Services Not Starting

**Check logs**:
```bash
docker compose logs agent-orchestrator
docker compose logs indexing
docker compose logs model-service
```

**Common issues**:
1. **Port conflicts**: Ensure ports 8002, 8003, 8004 are free
2. **Memory issues**: Model Service needs ~8GB RAM for Qwen2.5-7B
3. **Dependency issues**: Ensure PostgreSQL, Redis, Elasticsearch are healthy first

**Solutions**:
```bash
# Restart a service
docker compose restart agent-orchestrator

# Rebuild from scratch
docker compose down
docker compose build --no-cache agent-orchestrator
docker compose up -d agent-orchestrator
```

### Health Checks Failing

**Check service logs** for specific errors:
```bash
docker compose logs --tail=50 [service-name]
```

**Common issues**:
1. **Elasticsearch not ready**: Wait 30s more, or check ES logs
2. **Redis not connected**: Verify Redis container is running
3. **Model not loaded**: First load takes 2-5 minutes, check logs

### Model Service Timeout

**Expected behavior**: Qwen2.5-7B (7 billion parameters) is large and may:
- Take 2-5 minutes to load
- Require significant RAM (8GB+)
- Run slowly on CPU

**Alternative**: Use smaller model in `.env`:
```bash
MODEL_NAME=gpt2  # Much smaller, faster loading
```

---

## Next Steps After Testing

### If All Tests Pass ✅

1. **Mark todo complete**:
   - [x] Test all services start successfully with Docker Compose

2. **Proceed to Week 1 Day 5**:
   - Implement GitHub webhook handler
   - Connect ingestion service to agent orchestrator
   - Test end-to-end flow

### If Tests Fail ❌

1. **Review logs**: `docker compose logs [service-name]`
2. **Check troubleshooting guide**: See `docs/TESTING.md` Section 4
3. **Fix issues** and retest
4. **Document failures** for future reference

---

## Test Execution Command Summary

### Quick Commands

```bash
# Option 1: Full automated test (Bash)
cd /c/develop/workflow-ai && ./test-services.sh

# Option 2: Quick test (PowerShell)
cd C:\develop\workflow-ai
docker compose up -d agent-orchestrator indexing model-service
.\test-services-quick.ps1

# Option 3: One-line health check
curl http://localhost:8002/health && \
curl http://localhost:8003/health && \
curl http://localhost:8004/health
```

---

## Summary

**Status**: ✅ **Testing Infrastructure Complete - Ready for User Execution**

**Created**:
- 5 comprehensive test documents
- 2 automated test scripts (Bash + PowerShell)
- Complete troubleshooting guide
- Expected results documentation

**Services**:
- 3 Python microservices fully built and configured
- All using uv for package management (as required)
- Docker Compose integration complete
- Health checks and readiness probes implemented

**Limitation**:
- Current environment (Git Bash) does not have Docker access
- Test execution requires Docker-enabled shell (WSL2 or PowerShell)

**Recommended Action**:
1. Open WSL2 or PowerShell with Docker Desktop
2. Navigate to project directory
3. Run `./test-services.sh` (Bash) or `.\test-services-quick.ps1` (PowerShell)
4. Verify all services are healthy
5. Mark Day 4 complete and proceed to Day 5

**Time Estimate**: 5-10 minutes for full test execution

---

**Documentation Created By**: Sisyphus  
**Date**: 2026-02-27  
**Status**: Ready for user testing
