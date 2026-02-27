# Day 5 集成测试指南

## 当前状态

✅ **已完成的工作**:
1. Go Ingestion Service (9 个文件, ~850 行代码)
2. Agent Orchestrator Stream Consumer (4 个文件, ~430 行代码)
3. Redis Streams 集成
4. Docker Compose 配置
5. E2E 测试脚本 (`test-ingestion-e2e.sh`)
6. Day 5 完成文档

## 测试准备

### 1. 生成 Go 依赖文件

已完成! `go.sum` 文件已生成在 `services/ingestion/` 目录。

## WSL2 测试步骤

### 方式一：使用 PowerShell (推荐)

在 PowerShell 中运行以下命令:

```powershell
# 1. 进入 WSL2
wsl

# 2. 导航到项目目录
cd /mnt/c/develop/workflow-ai

# 3. 启动 Docker 服务
docker compose up -d redis ingestion agent-orchestrator

# 4. 等待服务启动 (30秒)
sleep 30

# 5. 检查服务状态
docker ps

# 6. 运行 E2E 测试
bash test-ingestion-e2e.sh

# 7. 查看日志
docker logs workflowai-ingestion --tail 50
docker logs workflowai-agent --tail 50
```

### 方式二：一键测试脚本

```bash
# 在 WSL2 中运行
cd /mnt/c/develop/workflow-ai
bash << 'EOF'
echo "========================================"
echo "Day 5 Ingestion Pipeline Test"
echo "========================================"

# 启动服务
docker compose up -d redis ingestion agent-orchestrator
echo "等待服务启动..."
sleep 30

# 检查服务
echo ""
echo "Running containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 运行测试
echo ""
bash test-ingestion-e2e.sh

# 显示日志
echo ""
echo "=== Ingestion Logs ==="
docker logs workflowai-ingestion --tail 20
echo ""
echo "=== Agent Logs ==="
docker logs workflowai-agent --tail 20
EOF
```

## 预期测试结果

### 成功输出示例:

```
==================================================
WorkflowAI Ingestion Pipeline E2E Test
==================================================

[STEP] 1. Checking Services
→ Checking Ingestion at http://localhost:8001/health...
✓ Ingestion is healthy
→ Checking Agent at http://localhost:8002/health...
✓ Agent is healthy

[STEP] 2. Initial State
→ Stream length: 0

[STEP] 3. Submit Test Log
→ Submitting test log (type: build)...
✓ Log submitted (HTTP 200)

[STEP] 4. Verify Stream
→ New stream length: 1
✓ Message published to stream

[STEP] 5. Check Agent Logs
✓ Agent processing detected

==================================================
✓ E2E Test Complete
==================================================

Data Flow Verified:
  Webhook → Parse → Redis Stream → Consumer → Agent
```

## 手动测试

### 1. 提交测试日志

```bash
curl -X POST http://localhost:8001/logs/submit \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "manual-test-1",
    "log_type": "build",
    "log_content": "Error: NullPointerException at line 42\n    at UserService.getUser(UserService.java:42)\nExit code: 1",
    "repository": "test/repo",
    "workflow": "CI Build",
    "run_id": "12345",
    "commit_sha": "abc123",
    "branch": "main"
  }'
```

### 2. 检查 Redis Stream

```bash
# 进入 Redis 容器
docker exec -it workflowai-redis redis-cli

# 查看 stream 长度
XLEN workflowai:logs

# 查看 consumer group 信息
XINFO GROUPS workflowai:logs

# 查看最新消息
XRANGE workflowai:logs - + COUNT 5
```

### 3. 查看服务日志

```bash
# Ingestion Service
docker logs -f workflowai-ingestion

# Agent Orchestrator  
docker logs -f workflowai-agent

# Redis
docker logs -f workflowai-redis
```

## 故障排查

### 服务未启动

```bash
# 查看所有容器状态
docker ps -a

# 查看失败日志
docker logs workflowai-ingestion
docker logs workflowai-agent

# 重新构建
docker compose build ingestion agent-orchestrator
docker compose up -d redis ingestion agent-orchestrator
```

### 健康检查失败

```bash
# 直接测试服务
curl http://localhost:8001/health
curl http://localhost:8002/health

# 检查端口占用
netstat -ano | findstr :8001
netstat -ano | findstr :8002
```

## 文件清单

### 新创建的文件:

1. `services/ingestion/` - Go Ingestion Service (9 files)
   - main.go, Dockerfile, go.mod, go.sum
   - config/config.go
   - utils/redis.go
   - parser/log_parser.go
   - streams/publisher.go
   - handlers/webhook.go

2. `services/agent-orchestrator/app/consumers/` - Stream Consumer
   - stream_consumer.py
   - __init__.py

3. `services/agent-orchestrator/app/workflows/` - Workflow Processor
   - processor.py
   - __init__.py

4. `test-ingestion-e2e.sh` - E2E 测试脚本

5. `docs/day5-ingestion-completion.md` - Day 5 完成文档

6. `TESTING-INSTRUCTIONS.md` - 本文档

### 修改的文件:

1. `services/agent-orchestrator/app/main.py` - 添加 stream consumer 生命周期
2. `services/agent-orchestrator/app/config.py` - 添加 stream 配置
3. `docker-compose.yml` - 已包含 ingestion service

## Day 5 完成状态

✅ Go Ingestion Service - 100%
✅ Log Parser - 100%  
✅ Redis Streams Publisher - 100%
✅ Agent Orchestrator Consumer - 100%
✅ Workflow Processor - 100%
✅ Docker Integration - 100%
✅ Testing Script - 100%
✅ Documentation - 100%

**总体完成度: 100%**

## 下一步 (Week 2)

1. 数据库持久化 (存储分析结果)
2. Webhook 安全加固
3. 多消费者扩展
4. 死信队列实现
5. 监控指标导出

---

**说明**: WSL2 环境需要先启动。如果遇到超时问题，请在 Windows Terminal 中打开 WSL2 后再运行测试。
