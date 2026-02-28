# WorkflowAI Day 10 Testing - Quick Start

## 🚀 One-Command Setup

```powershell
# Step 1: Configure AWS credentials (one-time setup)
wsl -d xde-22 -e bash /mnt/c/develop/workflow-ai/aws-setup.sh

# Step 2: Run automated tests
wsl -d xde-22 -e bash /mnt/c/develop/workflow-ai/aws-ec2-test.sh
```

That's it! The automation handles everything else.

---

## 📋 What You Need

**AWS Credentials** (from AWS Console):
1. Go to: https://ap-southeast-1.console.aws.amazon.com/iam/
2. Click **Users** → Your username → **Security credentials**
3. Click **Create access key** → Choose "CLI" → Copy both keys

**Cost**: Less than $0.01 (1 cent) for ~10 minutes of testing

---

## ⏱️ Timeline

```
[1/8] Create SSH key pair          5s
[2/8] Create security group         5s
[3/8] Launch EC2 instance          10s
[4/8] Wait for instance start      60s
[5/8] Wait for Docker install     180s
[6/8] Upload code to EC2           30s
[7/8] Run Day 10 tests            180s
[8/8] Cleanup resources            30s
────────────────────────────────────────
Total: 6-10 minutes
```

---

## ✅ What Gets Tested

- Elasticsearch cluster health
- Indexing Service + embedding model
- Agent Orchestrator integration
- Knowledge Base population (20 docs)
- Semantic + Keyword + Hybrid search
- RAG-enhanced log analysis
- Context-aware failure diagnosis

---

## 🧹 Auto-Cleanup

The script **automatically terminates** the EC2 instance and deletes all resources when done. No manual cleanup needed!

---

## 📖 Full Documentation

See [AWS-EC2-TESTING.md](./AWS-EC2-TESTING.md) for detailed instructions and troubleshooting.

---

**Ready?** Run the commands above! 🎯
