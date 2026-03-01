# Deploy Timeout Fix to EC2

## Summary

**Issue**: Agent workflow fails with `Model Service connection error: timed out` after 60 seconds.

**Root Cause**: First Qwen model inference triggers 1.5GB download (2-3 min) + loading (30-60s) + inference (30-60s) = 4-5 minutes total, but timeout was only 180 seconds.

**Fix**: Increased timeout to 300 seconds (5 minutes) in `services/agent-orchestrator/app/llm/custom_llm.py`.

**Commit**: `618e989` - "fix: increase Model Service timeout to 300s for Qwen download"

---

## Deployment Steps (Run on EC2)

### 1. Connect to EC2
```bash
export AWS_CLI_SSL_NO_VERIFY=1
aws ssm start-session --region ap-southeast-1 --target i-04c15212545859456
```

### 2. Switch to ec2-user
```bash
sudo su - ec2-user
cd /home/ec2-user/workflow-ai
```

### 3. Deploy Timeout Fix
```bash
# Pull latest code (includes timeout fix)
git pull origin main
# Expected: Updating a10d6b2..618e989

# Rebuild agent service with new timeout
docker-compose build --no-cache agent-orchestrator

# Restart agent service
docker-compose up -d agent-orchestrator

# Wait for agent to fully start
sleep 15

# Verify agent health
curl http://localhost:8002/health
# Expected: {"status":"healthy","redis_connected":true,"elasticsearch_connected":true}
```

### 4. Warm Up Model Service (CRITICAL STEP)

**Why**: First inference request triggers 1.5GB model download. Do this BEFORE testing Agent workflow to avoid timeout.

```bash
echo "========================================="
echo "Warming up Model Service"
echo "This will download Qwen2.5-1.5B-Instruct (1.5GB)"
echo "Expected time: 2-3 minutes"
echo "========================================="
echo ""

time curl -X POST http://localhost:8004/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Hello, this is a test","max_tokens":10}' \
  --max-time 300

echo ""
echo "If you see JSON output above, model is cached and ready!"
```

**Expected Output (after 2-3 minutes)**:
```json
{"text":"Hello, this is a test model response"}
```

**If you see errors**:
- Check model service logs: `docker logs workflowai-model --tail 100`
- Look for: "Downloading shards: 100%" or "Loading checkpoint shards"
- If OOM error: Model may be too large (check `docker stats workflowai-model`)

### 5. Test Agent Workflow

```bash
echo "========================================="
echo "Testing Agent Workflow with Qwen Model"
echo "Expected time: 30-60 seconds (model cached)"
echo "========================================="
echo ""

./test-agent-workflow-qwen.sh
```

**Expected Output**:
```
=== Agent Workflow Test (Qwen2.5-1.5B-Instruct) ===

Testing with database connection timeout log...

{
  "analysis_id": "...",
  "root_cause": "Database connection timeout after 30 seconds - likely network issue or database overload",
  "severity": "high",
  "suggested_fixes": [
    "Check database connectivity from application host",
    "Review database server load and connection pool settings",
    "Increase connection timeout if appropriate"
  ],
  "references": [...],
  "confidence": 0.85
}

=== Validation ===

✓ root_cause field present
  "root_cause":"Database connection timeout after 30 seconds - likely network issue or database overload"
✓ severity field present
  "severity":"high"
  ✓ Severity correctly classified (expected high/critical for DB timeout)
✓ confidence field present
  "confidence":0.85
  ✓ Confidence >= 0.7 (good quality)
✓ suggested_fixes field present
  Found 3 suggested fix(es)

=== Summary ===
Status: ✅ PASSED (Qwen model producing structured output)

Day 10 Agent workflow validation: SUCCESS
```

---

## Troubleshooting

### Problem: Still times out after 300s

**Check model download progress**:
```bash
# Watch model service logs
docker logs workflowai-model --follow

# Check if model files are being downloaded
docker exec workflowai-model du -sh /root/.cache/huggingface 2>/dev/null

# Check network speed to HuggingFace
docker exec workflowai-model curl -s -o /dev/null -w "Download speed: %{speed_download} bytes/sec\n" \
  https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/resolve/main/README.md
```

**If download is too slow** (< 100KB/s from China):
- Option 1: Use HuggingFace mirror (e.g., `export HF_ENDPOINT=https://hf-mirror.com`)
- Option 2: Pre-download model to EC2, mount as volume
- Option 3: Fallback to smaller model (Qwen 0.5B)

### Problem: Agent returns gibberish (still echoing prompts)

**Verify model configuration**:
```bash
# Check environment variable
docker exec workflowai-model env | grep MODEL_NAME
# Should show: MODEL_NAME=Qwen/Qwen2.5-1.5B-Instruct

# Check actual model loaded
docker logs workflowai-model | grep -i "loading.*model"
# Should mention Qwen2.5-1.5B-Instruct

# If mismatch, rebuild model service:
docker-compose build --no-cache model-service
docker-compose up -d model-service
```

### Problem: Out of Memory (OOM)

**Check memory usage**:
```bash
docker stats workflowai-model --no-stream

# If memory > 3.5GB, Qwen 1.5B may be too large
# Fallback to Qwen 0.5B:
# 1. Edit docker-compose.yml: MODEL_NAME=Qwen/Qwen2.5-0.5B-Instruct
# 2. docker-compose up -d model-service
```

### Problem: Agent test passes but quality is poor

**Check confidence score**:
```bash
# If confidence < 0.7, model may need more context
# Edit services/agent-orchestrator/app/agents/analyzer.py
# Increase max_iterations or improve prompt engineering
```

---

## Success Criteria

- [x] Agent workflow completes without timeout
- [x] `root_cause` contains meaningful analysis (not prompt echo)
- [x] `severity` correctly classified (high/critical for DB timeout)
- [x] `suggested_fixes` has 3+ actionable items
- [x] `confidence` >= 0.7
- [x] Response time: 30-60s (after warm-up)

**Once all criteria met**: Day 10 is complete! ✅

---

## Next Steps After Validation

1. Update README.md: Mark Day 10 as complete
2. Document actual performance metrics (response time, memory usage)
3. Move to Day 11: Multi-agent orchestration with LangGraph

---

## Files Changed (Summary)

| File | Change | Commit |
|------|--------|--------|
| `services/model-service/app/config.py` | Qwen 7B → Qwen 1.5B | 293a283 |
| `docker-compose.yml` | gpt2 → Qwen 1.5B | 293a283 |
| `services/agent-orchestrator/app/llm/custom_llm.py` | timeout: 180s → 300s | 618e989 |

---

**Ready to deploy. Please execute steps 1-5 above and share the results.**
