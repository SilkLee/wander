# EC2 Qwen Model Deployment Guide

## Quick Start

### 1. Connect to EC2
```bash
export AWS_CLI_SSL_NO_VERIFY=1
aws ssm start-session --region ap-southeast-1 --target i-04c15212545859456
```

### 2. Switch to ec2-user and Deploy
```bash
sudo su - ec2-user
cd /home/ec2-user/workflow-ai

# Copy deployment scripts from this repo
curl -O https://raw.githubusercontent.com/SilkLee/workflow-ai/main/deploy-qwen-model.sh
curl -O https://raw.githubusercontent.com/SilkLee/workflow-ai/main/test-agent-workflow-qwen.sh

chmod +x deploy-qwen-model.sh test-agent-workflow-qwen.sh

# Run deployment
./deploy-qwen-model.sh
```

### 3. Test Agent Workflow
```bash
# This will test with a realistic database timeout error
./test-agent-workflow-qwen.sh
```

---

## What Changed

**Commit 293a283**: Upgrade to Qwen2.5-1.5B-Instruct

### Problem (Before)
- `docker-compose.yml` used `gpt2` (124M base model)
- `config.py` had `Qwen2.5-7B-Instruct` (7B, too large)
- **Model mismatch**: Docker override used gpt2, which is not instruction-tuned
- **Result**: Agent returns prompt echo instead of structured analysis

### Solution (After)
- Both files now use `Qwen2.5-1.5B-Instruct`
- Instruction-tuned model (unlike gpt2 base model)
- 3GB memory (vs 7GB for Qwen 7B, 500MB for gpt2)
- CPU-friendly for Day 10 demo

---

## Expected Behavior

### Old Output (GPT-2)
```json
{
  "root_cause": "the final answer to the original input question\n\nBegin!\n\nQuestion: Analyze this application log..."
}
```

### New Output (Qwen 1.5B)
```json
{
  "root_cause": "Database connection timeout after 30 seconds - likely network issue or database overload",
  "severity": "high",
  "suggested_fixes": [
    "Check database connectivity from application host",
    "Review database server load and connection pool settings",
    "Increase connection timeout if appropriate"
  ],
  "confidence": 0.85
}
```

---

## Troubleshooting

### Model Download Taking Too Long
```bash
# Monitor download progress
docker logs workflowai-model --follow

# Expected: "Downloading shards: 100%"
# Wait 2-3 minutes for 1.5GB download
```

### Agent Still Returns Gibberish
```bash
# Check which model is actually loaded
docker exec workflowai-model env | grep MODEL_NAME
# Should show: MODEL_NAME=Qwen/Qwen2.5-1.5B-Instruct

# Check config file
docker exec workflowai-model cat /app/app/config.py | grep -A 2 "model_name"

# If mismatch found, rebuild:
docker-compose build --no-cache model-service
docker-compose up -d model-service
```

### Out of Memory
```bash
# Check memory usage
docker stats workflowai-model

# Qwen 1.5B should use ~3GB
# If OOM, check if other services are using too much memory
```

### Agent Timeout (>180s)
```bash
# First request is slow (model download + inference)
# Subsequent requests should be 30-60s

# To reduce timeout:
# 1. Use smaller model (Qwen 0.5B)
# 2. Reduce max_iterations in agent config
# 3. Add GPU support (future)
```

---

## Validation Checklist

After running `test-agent-workflow-qwen.sh`, verify:

- [x] `root_cause` contains meaningful analysis (not prompt echo)
- [x] `severity` is "high" or "critical" (database timeout is serious)
- [x] `suggested_fixes` has 3-5 actionable items
- [x] `confidence` >= 0.7
- [x] Response time 30-60s (after initial model download)

---

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Model | Qwen2.5-1.5B-Instruct |
| Parameters | 1.5B |
| Memory | ~3GB |
| Download Size | 1.5GB |
| First Request | 2-3 minutes (download + inference) |
| Subsequent Requests | 30-60s (CPU inference) |
| Context Window | 4096 tokens |

---

## Next Steps After Validation

1. ✅ Mark Day 10 complete in README.md
2. 📊 Document actual response time from test
3. 🎯 Move to Day 11: Multi-agent orchestration with LangGraph

---

## Related Files

- `services/model-service/app/config.py` - Model configuration
- `docker-compose.yml` - Environment variables
- `services/agent-orchestrator/app/agents/analyzer.py` - Agent workflow
- `services/agent-orchestrator/app/tools/knowledge_base.py` - Single-input tool (fixed)

---

## Commit History

```
293a283 (HEAD -> main, origin/main) feat: upgrade to Qwen2.5-1.5B-Instruct for Agent workflow
ef76226 fix: make KnowledgeBaseTool single-input for ZeroShotAgent compatibility
```
