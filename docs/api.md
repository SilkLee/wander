# API Documentation

> Complete endpoint reference for WorkflowAI's API Gateway (port 8000)

All requests go through the Go API Gateway, which reverse-proxies to downstream Python services.

---

## Base URL

| Environment | URL |
|------------|-----|
| Local | `http://localhost:8000` |
| Production (EKS) | `http://k8s-workflow-workflow-40cd3e1fe4-525208112.ap-southeast-1.elb.amazonaws.com` |

---

## Authentication

Protected routes require a JWT Bearer token in the `Authorization` header:

```
Authorization: Bearer <jwt-token>
```

**Public routes** (no auth required): Health check, workflow endpoints, metrics endpoints, and the root endpoint.

---

## Public Endpoints

### Health Check

```
GET /health
```

**Response** `200 OK`:
```json
{
  "status": "healthy",
  "service": "api-gateway",
  "timestamp": "2026-03-15T10:30:00Z"
}
```

### Root

```
GET /
```

Returns API information and version.

---

## Workflow Endpoints (Public, Rate-Limited)

These endpoints power the React frontend. No JWT required.

### Analyze Build Log

```
POST /api/v1/workflows/analyze-log
Content-Type: application/json
```

**Request Body**:
```json
{
  "log_content": "ERROR: ModuleNotFoundError: No module named 'torch'\n...",
  "workflow_type": "build_failure_triage"
}
```

**Response** `200 OK`:
```json
{
  "workflow_id": "wf-abc123",
  "status": "completed",
  "result": {
    "root_cause": "Missing PyTorch dependency in Docker image",
    "severity": "high",
    "fix_steps": [
      "Add torch>=2.1.0 to pyproject.toml dependencies",
      "Rebuild Docker image with updated requirements"
    ],
    "references": [
      "https://pytorch.org/get-started/locally/"
    ],
    "confidence": 0.92
  }
}
```

### Analyze Build Log (Streaming)

```
POST /api/v1/workflows/analyze-log/stream
Content-Type: application/json
```

Returns Server-Sent Events (SSE) stream with incremental results.

### Execute Workflow

```
POST /api/v1/workflows/execute
Content-Type: application/json
```

**Request Body**:
```json
{
  "workflow_type": "pr_risk_assessment",
  "input": {
    "pr_diff": "diff --git a/main.py ...",
    "pr_metadata": {
      "files_changed": 15,
      "additions": 400,
      "deletions": 120
    }
  }
}
```

**Response** `200 OK`:
```json
{
  "workflow_id": "wf-def456",
  "status": "completed",
  "result": {
    "risk_score": 0.72,
    "risk_level": "high",
    "recommendations": [
      "Large diff — consider splitting into smaller PRs",
      "Changes touch authentication module — requires security review"
    ]
  }
}
```

### List Workflow Types

```
GET /api/v1/workflows/types
```

**Response** `200 OK`:
```json
{
  "workflow_types": [
    "build_failure_triage",
    "pr_risk_assessment",
    "code_review",
    "incident_response"
  ]
}
```

---

## Metrics Endpoints (Public, Rate-Limited)

### Get DORA Metrics

```
GET /api/metrics/dora
```

**Response** `200 OK` (cached 30s):
```json
{
  "deployment_frequency": {
    "value": 3.5,
    "unit": "deploys/week",
    "rating": "high"
  },
  "lead_time": {
    "value": 2.4,
    "unit": "hours",
    "rating": "elite"
  },
  "change_failure_rate": {
    "value": 0.08,
    "unit": "ratio",
    "rating": "elite"
  },
  "mttr": {
    "value": 0.5,
    "unit": "hours",
    "rating": "elite"
  }
}
```

### Record Deployment Event

```
POST /api/metrics/events/deployment
Content-Type: application/json
```

**Request Body**:
```json
{
  "service": "api-gateway",
  "version": "sha-d8fc155",
  "environment": "production",
  "status": "success",
  "timestamp": "2026-03-15T10:00:00Z"
}
```

### Record Change Event

```
POST /api/metrics/events/change
Content-Type: application/json
```

**Request Body**:
```json
{
  "commit_sha": "d8fc155",
  "author": "silk",
  "repository": "SilkLee/workflow-ai",
  "timestamp": "2026-03-15T09:00:00Z"
}
```

### Record Incident Event

```
POST /api/metrics/events/incident
Content-Type: application/json
```

**Request Body**:
```json
{
  "title": "API Gateway 5xx spike",
  "severity": "high",
  "started_at": "2026-03-15T08:00:00Z",
  "resolved_at": "2026-03-15T08:30:00Z"
}
```

### List Events

```
GET /api/metrics/events
```

Returns all recorded metric events.

---

## Protected Endpoints (JWT Required)

All `/api/v1/*` endpoints below require a valid JWT Bearer token.

### Ingestion

```
POST /api/v1/ingest           # Ingest CI/CD event (webhook payload)
GET  /api/v1/ingest/health    # Ingestion service health
```

### Indexing & Search

```
POST /api/v1/index            # Index a single document
POST /api/v1/index/batch      # Batch index documents
POST /api/v1/search           # Hybrid search (BM25 + dense vector)
GET  /api/v1/stats            # Index statistics
```

### Agent Orchestrator

```
POST /api/v1/execute          # Execute agent workflow
GET  /api/v1/execute/:id      # Get workflow execution status/result
```

### Model Service

```
POST /api/v1/generate         # LLM text generation
GET  /api/v1/model/info       # Model info (cached 30s)
```

### Metrics (Protected Path)

```
ANY /api/v1/metrics/*path     # Proxied to metrics service (cached 30s)
```

---

## Admin Endpoints (JWT + Admin Role)

```
GET /admin/stats              # System-wide statistics
```

Requires JWT with admin role claim.

---

## Rate Limiting

All API routes are rate-limited via Redis token bucket. Default: configurable RPS per client IP.

**Response when rate-limited** `429 Too Many Requests`:
```json
{
  "error": "rate limit exceeded",
  "retry_after": 1
}
```

---

## Response Caching

Read endpoints are cached via Redis with TTL:

| Endpoint | Cache TTL |
|----------|----------|
| `GET /api/v1/model/info` | 30 seconds |
| `ANY /api/v1/metrics/*` | 30 seconds |
| `GET /api/metrics/dora` | 30 seconds |

Cache is bypassed for POST/PUT/DELETE requests.

---

## Error Response Format

All errors follow a consistent JSON format:

```json
{
  "error": "descriptive error message",
  "code": 400
}
```

| Status Code | Meaning |
|------------|---------|
| 400 | Bad Request — invalid input |
| 401 | Unauthorized — missing or invalid JWT |
| 403 | Forbidden — insufficient permissions |
| 404 | Not Found — endpoint or resource doesn't exist |
| 429 | Too Many Requests — rate limit exceeded |
| 500 | Internal Server Error |
| 502 | Bad Gateway — downstream service unavailable |

---

## Service Ports (Internal)

For direct service access during local development:

| Service | Port | Base URL |
|---------|------|----------|
| API Gateway | 8000 | `http://localhost:8000` |
| Ingestion | 8001 | `http://localhost:8001` |
| Agent Orchestrator | 8002 | `http://localhost:8002` |
| Indexing | 8003 | `http://localhost:8003` |
| Model Service | 8004 | `http://localhost:8004` |
| Metrics | 8005 | `http://localhost:8005` |
| Finetune | 8006 | `http://localhost:8006` |
| Frontend | 3000 | `http://localhost:3000` |
