# Week 8: DORA Metrics + Frontend Integration — Full Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete Week 8 by building a production-grade DORA metrics service with real calculation logic and PostgreSQL storage, a full React frontend with routing and pages for all 5 workflows (Log Analysis, PR Risk, Code Review, Incident Response, DORA Metrics), API Gateway proxy wiring, and Docker Compose integration.

**Architecture:** 
- Metrics Service: DDD-style FastAPI service with domain models, repository pattern (PostgreSQL), and DORA calculation engine
- Frontend: React + TypeScript + React Router with a sidebar layout, 5 pages, and a shared API client layer
- API Gateway: Add proxy routes for metrics service
- Docker Compose: Enable metrics + frontend services

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, PostgreSQL, React 18, TypeScript, React Router v6, Vite

---

## Task 1: DORA Metrics Service — Domain Models + Calculation Engine

**Files:**
- Create: `services/metrics/app/domain/__init__.py`
- Create: `services/metrics/app/domain/models.py`
- Create: `services/metrics/app/domain/calculator.py`
- Create: `services/metrics/app/domain/enums.py`

### domain/enums.py
```python
from enum import Enum

class DORALevel(str, Enum):
    ELITE = "elite"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class MetricInterval(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
```

### domain/models.py
Domain value objects:
- `DeploymentEvent(id, repo, sha, deployed_at, success)`
- `ChangeEvent(id, repo, sha, first_commit_at, merged_at, deployed_at)`
- `IncidentEvent(id, repo, detected_at, resolved_at, caused_by_sha)`
- `DORASnapshot(deployment_frequency, lead_time_hours, change_failure_rate, mttr_hours, level, period_start, period_end)`

### domain/calculator.py
Pure functions:
- `calc_deployment_frequency(events, start, end) -> float` — deploys per day
- `calc_lead_time(changes, start, end) -> float` — median hours from commit to deploy
- `calc_change_failure_rate(deploys, incidents) -> float` — ratio 0.0-1.0
- `calc_mttr(incidents) -> float` — mean hours to recovery
- `classify_level(df, lt, cfr, mttr) -> DORALevel` — per Google DORA benchmarks
- `calculate_dora(deploys, changes, incidents, start, end) -> DORASnapshot`

---

## Task 2: Metrics Service — Repository + Database Layer

**Files:**
- Create: `services/metrics/app/infrastructure/__init__.py`
- Create: `services/metrics/app/infrastructure/database.py`
- Create: `services/metrics/app/infrastructure/repository.py`
- Modify: `infra/docker/postgres/init.sql` — add DORA event tables

### New DB tables (init.sql additions):
```sql
CREATE TABLE deployment_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository VARCHAR(255) NOT NULL,
    commit_sha VARCHAR(64) NOT NULL,
    deployed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    success BOOLEAN NOT NULL DEFAULT true,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE change_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository VARCHAR(255) NOT NULL,
    commit_sha VARCHAR(64) NOT NULL,
    first_commit_at TIMESTAMP WITH TIME ZONE NOT NULL,
    merged_at TIMESTAMP WITH TIME ZONE,
    deployed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE incident_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository VARCHAR(255) NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE NOT NULL,
    resolved_at TIMESTAMP WITH TIME ZONE,
    caused_by_sha VARCHAR(64),
    severity VARCHAR(20) DEFAULT 'medium',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### infrastructure/database.py
- SQLAlchemy async engine + session factory
- Connection to PostgreSQL via DATABASE_URL env var
- Fallback to in-memory stub when DB unavailable

### infrastructure/repository.py
- `DORARepository` class implementing CRUD for events
- `get_deployments(repo, start, end)`, `get_changes(...)`, `get_incidents(...)`
- `record_deployment(...)`, `record_change(...)`, `record_incident(...)`

---

## Task 3: Metrics Service — Enhanced API Endpoints

**Files:**
- Modify: `services/metrics/app/api/dora.py` — expand to full API
- Create: `services/metrics/app/api/events.py` — event ingestion endpoints
- Modify: `services/metrics/app/main.py` — register new routers
- Create: `services/metrics/app/config.py` — settings

### API Endpoints:
```
GET  /metrics/dora?repo=...&from=...&to=...&interval=day  → DORAResponse with trend
POST /metrics/events/deployment  → Record deployment event
POST /metrics/events/change      → Record change event
POST /metrics/events/incident    → Record incident event
GET  /metrics/events?repo=...&type=...&from=...&to=...    → List events
GET  /health                     → Health check
```

---

## Task 4: Frontend — React Router + Layout + Pages

**Files:**
- Modify: `frontend/package.json` — add react-router-dom
- Create: `frontend/src/layout/AppLayout.tsx` — sidebar + header layout
- Create: `frontend/src/pages/DashboardPage.tsx` — overview/home
- Create: `frontend/src/pages/LogAnalysisPage.tsx`
- Create: `frontend/src/pages/PrRiskPage.tsx`
- Create: `frontend/src/pages/CodeReviewPage.tsx`
- Create: `frontend/src/pages/IncidentResponsePage.tsx`
- Create: `frontend/src/pages/DoraMetricsPage.tsx` — move existing dashboard here
- Modify: `frontend/src/App.tsx` — add Router

---

## Task 5: Frontend — API Client Layer

**Files:**
- Modify: `frontend/src/api/metrics.ts` — enhance
- Create: `frontend/src/api/workflows.ts` — workflow API client
- Create: `frontend/src/api/client.ts` — base fetch wrapper

---

## Task 6: API Gateway — Metrics Proxy Routes

**Files:**
- Modify: `services/api-gateway/internal/interfaces/http/router.go`
- Modify: `services/api-gateway/internal/interfaces/http/handlers/proxy.go`

Add:
```
/api/v1/metrics/*  → proxy to metrics service (port 8005)
```

---

## Task 7: Docker Compose — Enable Metrics + Frontend

**Files:**
- Modify: `docker-compose.yml` — uncomment + configure metrics and frontend services
- Create: `services/metrics/Dockerfile`
- Create: `services/metrics/pyproject.toml` — dependencies
- Modify: `frontend/Dockerfile` (or create if missing)

---

## Task 8: Vite Proxy Update + Frontend Dev Config

**Files:**
- Modify: `frontend/vite.config.ts` — proxy both `/api/metrics` → metrics:8005 and `/api` → agent:8002

---
