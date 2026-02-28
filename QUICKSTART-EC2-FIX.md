# Quick Start: EC2 Fix and Test

## TL;DR - Copy-Paste This Into Your EC2 Session

You're currently logged into EC2 via SSM at `/home/ec2-user`. Run this ONE command:

```bash
# Option 1: Automated (RECOMMENDED)
curl -o ec2-fix-and-test.sh https://raw.githubusercontent.com/SilkLee/wander/main/ec2-fix-and-test.sh && bash ec2-fix-and-test.sh
```

**OR** if you prefer manual control:

```bash
# Option 2: Manual (step-by-step)

# 1. Apply fixes
sed -i 's/--start-period=120s/--start-period=300s/g' services/model-service/Dockerfile
sed -i 's|LOCAL_MODEL_PATH=/app/models/qwen.*|LOCAL_MODEL_PATH=  # Empty|g' docker-compose.yml

# 2. Rebuild and restart
sudo docker-compose down
sudo docker-compose build model-service
sudo docker-compose up -d elasticsearch redis indexing agent-orchestrator model-service

# 3. Wait 2-5 minutes, check status
watch -n 5 'sudo docker-compose ps'
# Press Ctrl+C when all services show "Up" or "healthy"

# 4. Run tests
bash test-day10-internal.sh | tee ~/day10-test-results.txt

# 5. Exit
exit
```

---

## What This Does

### Problems Fixed:
1. ❌ **Health check timeout**: 120s → 300s (allows GPT-2 download time)
2. ❌ **Invalid model path**: `/app/models/qwen` → empty (uses HuggingFace gpt2)

### Actions Taken:
1. ✅ Applies sed fixes to 2 files
2. ✅ Rebuilds model-service Docker image
3. ✅ Starts all 5 services (elasticsearch, redis, indexing, model, agent)
4. ✅ Waits for healthy status (up to 10 minutes)
5. ✅ Runs 8 integration tests
6. ✅ Saves results to `~/day10-test-results.txt`

### Expected Timeline:
- **Fixes**: 5 seconds
- **Rebuild**: 30 seconds
- **Service startup**: 2-5 minutes (model download)
- **Tests**: 45 seconds
- **Total**: ~6 minutes

---

## Expected Output

### During Startup (2-5 minutes):
```
[0s] Running: 2/5, Healthy: 1/3
  Model Service: starting, Agent: created
[30s] Running: 4/5, Healthy: 2/3
  Model Service: starting, Agent: created
[180s] Running: 5/5, Healthy: 3/3
  Model Service: healthy, Agent: running
✓ All services are up and running!
```

### Test Results (45 seconds):
```
=== Day 10 RAG Integration Tests ===

[1/8] Elasticsearch health... ✅ PASS
[2/8] Indexing Service health... ✅ PASS
[3/8] Agent Orchestrator health... ✅ PASS
[4/8] Knowledge Base population... ✅ PASS (20 documents)
[5/8] Semantic search... ✅ PASS (3 results)
[6/8] Hybrid search... ✅ PASS (3 results)
[7/8] RAG-enhanced log analysis... ✅ PASS
[8/8] OutOfMemoryError RAG analysis... ✅ PASS

=== Test Summary ===
Total: 8 | Passed: 8 ✅ | Failed: 0 ❌
Duration: 45s

✅ Day 10 RAG integration fully verified!
```

---

## After Tests Complete

### On EC2:
```bash
exit  # Exit SSM session
```

### On Your Local Machine (xde-22):
Press **Ctrl+C** in the terminal where `aws-ec2-test-ssm.sh` is running.

This triggers automatic cleanup:
- ✅ Terminate EC2 instance `i-0b00972987f6bfb9c`
- ✅ Delete S3 bucket `workflow-ai-test-e23aba9e`
- ✅ Preserve IAM roles (WorkflowAI-SSM-FixedRole)

---

## Troubleshooting

### If automated script fails:
```bash
# Check what went wrong
sudo docker-compose ps
sudo docker logs workflowai-model --tail 50

# Common issues:
# 1. Network timeout → Wait longer (up to 10 min)
# 2. Out of memory → Check: free -h (need 2GB+ free)
# 3. Port conflicts → Check: sudo netstat -tlnp | grep 8004
```

### Manual recovery:
See **EC2-UPDATE-INSTRUCTIONS.md** for detailed step-by-step guide with all troubleshooting scenarios.

---

## Files Committed

- **Commit 9b89f83**: Core fixes (Dockerfile + docker-compose.yml)
- **Commit 86484cf**: Automation script + comprehensive docs

All changes are in Git and ready for EC2 execution.

---

**Status**: Ready to execute on EC2  
**Next Action**: Copy-paste the command above into your EC2 SSM session
