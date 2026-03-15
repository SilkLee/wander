# Week 10: Performance Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Optimize all services for production-grade performance: connection pooling, caching, multi-worker Python, Docker image optimization, frontend code splitting.

**Architecture:** Performance optimization across 4 layers — Go Gateway (connection reuse, caching), Python services (multi-worker, response caching), Frontend (code splitting, nginx), Docker (multi-stage builds, resource limits).

**Tech Stack:** Go (net/http Transport pooling, Redis cache), Python (gunicorn + uvicorn workers), React (React.lazy, Suspense), Vite (manualChunks), nginx, Docker multi-stage.

---

## Task 1: Go Gateway — Connection Pooling + HTTP Client Reuse

**Problem:** `proxy.go` creates a new `http.Client{}` per request (line 48). No connection reuse, no keepalive pooling, no timeouts.

**Fix:** Create a shared `http.Client` with configured Transport (connection pooling) and timeouts.

**Files:**
- Modify: `services/api-gateway/utils/proxy.go`
- Modify: `services/api-gateway/internal/interfaces/http/router.go` (server timeouts)

## Task 2: Go Gateway — Response Caching Middleware

**Problem:** No caching for read-heavy endpoints (health, metrics, model info). Every GET re-fetches from downstream.

**Fix:** Add Redis-backed response cache middleware for GET endpoints with configurable TTL.

**Files:**
- Create: `services/api-gateway/internal/interfaces/http/middleware/cache.go`
- Modify: `services/api-gateway/internal/interfaces/http/router.go`

## Task 3: Python Services — Multi-Worker + Gunicorn

**Problem:** All Python services run single-worker uvicorn. Can't use multiple CPU cores.

**Fix:** Add gunicorn with uvicorn workers for production. Keep single-worker for dev.

**Files:**
- Modify: `services/agent-orchestrator/Dockerfile`
- Modify: `services/metrics/Dockerfile`
- Modify: `services/indexing/Dockerfile`
- Modify: `services/model-service/Dockerfile`
- Modify: `services/metrics/pyproject.toml` (add gunicorn dep)
- Modify: `services/agent-orchestrator/pyproject.toml` (add gunicorn dep)

## Task 4: Metrics Dockerfile — Multi-Stage Build

**Problem:** Metrics Dockerfile is single-stage, includes build-essential in final image.

**Fix:** Multi-stage build matching agent-orchestrator pattern.

**Files:**
- Modify: `services/metrics/Dockerfile`

## Task 5: Frontend — React.lazy Code Splitting + Vite Chunks

**Problem:** All pages loaded eagerly. No code splitting. No memoization.

**Fix:** React.lazy + Suspense for route-level code splitting. Vite manualChunks for vendor splitting.

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/vite.config.ts`

## Task 6: Frontend Dockerfile — Nginx

**Problem:** Uses `serve` npm package for static files. Nginx is faster and more configurable.

**Fix:** Replace serve with nginx:alpine for static file serving with caching headers.

**Files:**
- Modify: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`

## Task 7: Metrics Service — In-Memory TTL Cache

**Problem:** DORA metrics recalculated on every request. Expensive aggregation queries.

**Fix:** Add TTL-based in-memory cache for DORA calculations (30s default).

**Files:**
- Create: `services/metrics/app/infrastructure/cache.py`
- Modify: `services/metrics/app/api/dora.py`

## Task 8: Docker Compose — Resource Limits + Health Check Tuning

**Problem:** No memory/CPU limits. Health checks not optimized.

**Fix:** Add deploy.resources.limits. Tune health check intervals.

**Files:**
- Modify: `docker-compose.yml`

## Task 9: Verify All Tests Pass

Run full test suite across all services to confirm no regressions.

## Task 10: Commit + Push + Update README
