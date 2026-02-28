# EC2 Manual Update Instructions for Day 10 Testing

## Problem Diagnosis

The `workflowai-model` container was failing with health check errors due to:

1. **Health check timeout too short**: 120s was insufficient for GPT-2 model download on first run (needs ~300s)
2. **Invalid LOCAL_MODEL_PATH**: Set to `/app/models/qwen` but directory doesn't exist

## Fixes Applied (Commit 9b89f83)

### 1. services/model-service/Dockerfile (Line 43)
```diff
- HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
+ HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=3 \
```

### 2. docker-compose.yml (Line 168)
```diff
-       - LOCAL_MODEL_PATH=/app/models/qwen  # Will be mounted from host
+       - LOCAL_MODEL_PATH=  # Empty - use HuggingFace model_name (gpt2)
```

---

## Step-by-Step Instructions for EC2

### Step 1: Update Files on EC2

**In your EC2 SSM session** (currently at `/home/ec2-user`), run:

```bash
# Method A: Manually edit files (RECOMMENDED - faster)

# 1. Edit Dockerfile
vi services/model-service/Dockerfile
# Press 'i' for insert mode
# Go to line 43, change:
#   --start-period=120s
# to:
#   --start-period=300s
# Press Esc, type :wq to save and exit

# 2. Edit docker-compose.yml
vi docker-compose.yml
# Press 'i' for insert mode
# Go to line 168, change:
#   - LOCAL_MODEL_PATH=/app/models/qwen  # Will be mounted from host
# to:
#   - LOCAL_MODEL_PATH=  # Empty - use HuggingFace model_name (gpt2)
# Press Esc, type :wq to save and exit

# Verify changes
grep "start-period" services/model-service/Dockerfile
# Should show: --start-period=300s

grep "LOCAL_MODEL_PATH" docker-compose.yml
# Should show: - LOCAL_MODEL_PATH=  # Empty - use HuggingFace model_name (gpt2)
```

**Alternative Method B: Download updated tarball from S3** (slower, 166MB download):

```bash
# Only if Method A doesn't work - this downloads ALL code again
cd /home/ec2-user
sudo aws s3 cp s3://workflow-ai-test-e23aba9e/workflow-ai-updated.tar.gz . --region ap-southeast-1
tar xzf workflow-ai-updated.tar.gz --strip-components=1
```

---

### Step 2: Rebuild and Restart Docker Services

```bash
# Stop all services
sudo docker-compose down

# Remove unhealthy model container
sudo docker rm workflowai-model 2>/dev/null || true

# Rebuild model-service image (with new health check settings)
sudo docker-compose build model-service

# Start all services
sudo docker-compose up -d elasticsearch redis indexing agent-orchestrator model-service

# Monitor startup (this will take 2-5 minutes for model download)
watch -n 5 'sudo docker-compose ps'
# Wait until all 5 services show "Up" or "healthy"
# Press Ctrl+C to exit watch when done
```

**Expected output after ~5 minutes:**
```
NAME                       STATUS                    PORTS
workflowai-agent           Up 2 minutes              0.0.0.0:8002->8002/tcp
workflowai-elasticsearch   Up 5 minutes (healthy)    0.0.0.0:9200->9200/tcp
workflowai-indexing        Up 3 minutes              0.0.0.0:8003->8003/tcp
workflowai-model           Up 4 minutes (healthy)    0.0.0.0:8004->8004/tcp
workflowai-redis           Up 5 minutes (healthy)    0.0.0.0:6379->6379/tcp
```

---

### Step 3: Verify Services

```bash
# Check Model Service health
curl http://localhost:8004/health
# Expected: {"status":"healthy","service":"model-service","version":"0.1.0","model_loaded":true,"model_name":"gpt2"}

# Check Agent Orchestrator health
curl http://localhost:8002/health
# Expected: {"status":"healthy",...}

# Check Indexing Service health
curl http://localhost:8003/health
# Expected: {"status":"healthy",...}

# If any service fails, check logs:
sudo docker logs workflowai-model
sudo docker logs workflowai-agent
sudo docker logs workflowai-indexing
```

---

### Step 4: Run Integration Tests

```bash
cd /home/ec2-user
bash test-day10-internal.sh
```

**Expected output:**
```
=== Day 10 RAG Integration Tests ===

[1/8] Elasticsearch health... ✅ PASS
[2/8] Indexing Service health... ✅ PASS
[3/8] Agent Orchestrator health... ✅ PASS
[4/8] Knowledge Base population... ✅ PASS (20 documents indexed)
[5/8] Semantic search... ✅ PASS (3 results)
[6/8] Hybrid search... ✅ PASS (3 results)
[7/8] RAG-enhanced log analysis... ✅ PASS (context retrieval working)
[8/8] OutOfMemoryError RAG analysis... ✅ PASS (similar cases retrieved)

=== Test Summary ===
Total: 8 tests
Passed: 8 ✅
Failed: 0 ❌
Duration: 45 seconds

✅ Day 10 RAG integration fully verified!
```

---

### Step 5: Save Test Results

```bash
# Save test output for documentation
bash test-day10-internal.sh | tee ~/day10-test-results.txt

# Display results
cat ~/day10-test-results.txt
```

---

### Step 6: Exit and Clean Up

```bash
# Exit SSM session
exit
```

**Then on your local machine** (xde-22 WSL), press **Ctrl+C** in the terminal where `aws-ec2-test-ssm.sh` is running. This will:
- Terminate EC2 instance `i-0b00972987f6bfb9c`
- Delete S3 bucket `workflow-ai-test-e23aba9e`
- Preserve IAM roles (as requested)

---

## Troubleshooting

### If model-service still unhealthy after 5 minutes:

```bash
# Check detailed logs
sudo docker logs workflowai-model --tail 100

# Common issues:
# 1. Network timeout downloading GPT-2 model
#    → Wait longer (up to 10 minutes on slow network)
#    → Check: curl https://huggingface.co

# 2. Out of memory
#    → Check: free -h
#    → Should have at least 2GB free RAM

# 3. Port already in use
#    → Check: sudo netstat -tlnp | grep 8004
```

### If tests fail:

```bash
# 1. Check all services are up
sudo docker-compose ps

# 2. Check logs for each service
sudo docker logs workflowai-elasticsearch
sudo docker logs workflowai-redis
sudo docker logs workflowai-indexing
sudo docker logs workflowai-model
sudo docker logs workflowai-agent

# 3. Manual health checks
curl http://localhost:9200/_cluster/health  # Elasticsearch
curl http://localhost:8003/health           # Indexing
curl http://localhost:8004/health           # Model
curl http://localhost:8002/health           # Agent

# 4. Re-run specific test sections
# Edit test-day10-internal.sh to comment out passing tests
```

---

## What Changed and Why

### Before (Failing):
```yaml
# docker-compose.yml
LOCAL_MODEL_PATH=/app/models/qwen  # ❌ Directory doesn't exist, causes inference.py to fail

# Dockerfile
HEALTHCHECK --start-period=120s  # ❌ Too short for GPT-2 download (~500MB)
```

### After (Working):
```yaml
# docker-compose.yml
LOCAL_MODEL_PATH=  # ✅ Empty, uses MODEL_NAME=gpt2 from HuggingFace

# Dockerfile
HEALTHCHECK --start-period=300s  # ✅ Allows 5min for model download + loading
```

### Why GPT-2 Needs 5 Minutes:
1. **Download**: GPT-2 model files (~500MB) from HuggingFace
2. **Extract**: Decompress and save to cache (`/app/cache/transformers`)
3. **Load**: Load weights into memory and initialize PyTorch model
4. **Total**: 2-5 minutes on t3.large with EC2 network speeds

---

## Next Steps After Successful Tests

1. ✅ **Update README.md**: Mark Day 10 as complete
2. ✅ **Document results**: Save test output to `DAY10-AWS-TEST-RESULTS.md`
3. 📝 **Begin Day 11**: Multi-agent orchestration with LangGraph
4. 📝 **Week 2 completion**: Day 8-10 done (3/7 days)

---

**Last Updated**: 2026-02-28 19:32
**Commit**: 9b89f83 - fix: model-service health check and LOCAL_MODEL_PATH for EC2 deployment
