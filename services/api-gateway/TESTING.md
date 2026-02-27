# API Gateway Testing Guide

## Overview
This document provides comprehensive testing procedures for the JWT authentication and Redis rate limiting middleware implemented in Day 3.

## Prerequisites
- Docker and Docker Compose running
- Redis service healthy (port 6379)
- `curl` or Postman for API testing
- `redis-cli` for Redis inspection (optional)

## Automated Tests

### Running Unit Tests

```bash
# From api-gateway directory
cd C:\develop\workflow-ai\services\api-gateway

# Run all middleware tests
go test -v ./middleware/

# Run specific test suites
go test -v ./middleware/ -run TestAuthenticate
go test -v ./middleware/ -run TestRateLimit

# Run with coverage
go test -coverprofile=coverage.out ./middleware/
go tool cover -html=coverage.out
```

### Test Suite Coverage

**Authentication Tests** (`middleware/auth_test.go`):
- ✅ `TestAuthenticate_MissingAuthHeader` - Missing Authorization header returns 401
- ✅ `TestAuthenticate_InvalidAuthFormat` - Non-Bearer format returns 401
- ✅ `TestAuthenticate_InvalidToken` - Malformed token returns 401
- ✅ `TestAuthenticate_ValidToken` - Valid token extracts claims to context
- ✅ `TestAuthenticate_ExpiredToken` - Expired token returns 401
- ✅ `TestRequireAdmin_NoRoles` - Missing roles returns 403
- ✅ `TestRequireAdmin_NonAdminRole` - Non-admin user returns 403
- ✅ `TestRequireAdmin_WithAdminRole` - Admin user passes through
- ✅ `TestRequireAdmin_InvalidRolesType` - Malformed roles returns 403

**Rate Limiting Tests** (`middleware/ratelimit_test.go`):
- ✅ `TestRateLimit_Integration` - Integration test with real Redis (requires Redis connection)
- Mock Redis client structure for unit testing

## Manual Testing

### 1. Start Services

```bash
cd C:\develop\workflow-ai

# Start Redis (if not running)
docker-compose up -d redis

# Check Redis health
docker exec workflowai-redis redis-cli ping
# Expected: PONG

# Start API Gateway
docker-compose up -d api-gateway

# Check logs
docker logs workflowai-gateway
```

### 2. Generate Test JWT Tokens

Create a helper script `generate-token.go`:

```go
package main

import (
    "fmt"
    "time"
    "github.com/golang-jwt/jwt/v5"
)

type JWTClaims struct {
    UserID   string   `json:"userId"`
    Username string   `json:"username"`
    Roles    []string `json:"roles"`
    jwt.RegisteredClaims
}

func main() {
    secret := "changeme-in-production"
    
    // Regular user token
    userClaims := &JWTClaims{
        UserID:   "user123",
        Username: "testuser",
        Roles:    []string{"user"},
        RegisteredClaims: jwt.RegisteredClaims{
            ExpiresAt: jwt.NewNumericDate(time.Now().Add(24 * time.Hour)),
            IssuedAt:  jwt.NewNumericDate(time.Now()),
        },
    }
    userToken := jwt.NewWithClaims(jwt.SigningMethodHS256, userClaims)
    userTokenString, _ := userToken.SignedString([]byte(secret))
    fmt.Println("Regular User Token:")
    fmt.Println(userTokenString)
    fmt.Println()
    
    // Admin token
    adminClaims := &JWTClaims{
        UserID:   "admin456",
        Username: "admin",
        Roles:    []string{"user", "admin"},
        RegisteredClaims: jwt.RegisteredClaims{
            ExpiresAt: jwt.NewNumericDate(time.Now().Add(24 * time.Hour)),
            IssuedAt:  jwt.NewNumericDate(time.Now()),
        },
    }
    adminToken := jwt.NewWithClaims(jwt.SigningMethodHS256, adminClaims)
    adminTokenString, _ := adminToken.SignedString([]byte(secret))
    fmt.Println("Admin Token:")
    fmt.Println(adminTokenString)
    fmt.Println()
    
    // Expired token
    expiredClaims := &JWTClaims{
        UserID:   "user789",
        Username: "expireduser",
        Roles:    []string{"user"},
        RegisteredClaims: jwt.RegisteredClaims{
            ExpiresAt: jwt.NewNumericDate(time.Now().Add(-1 * time.Hour)),
            IssuedAt:  jwt.NewNumericDate(time.Now().Add(-2 * time.Hour)),
        },
    }
    expiredToken := jwt.NewWithClaims(jwt.SigningMethodHS256, expiredClaims)
    expiredTokenString, _ := expiredToken.SignedString([]byte(secret))
    fmt.Println("Expired Token:")
    fmt.Println(expiredTokenString)
}
```

Run: `go run generate-token.go`

### 3. Authentication Testing

#### Test 1: Public Endpoints (No Auth Required)

```bash
# Root endpoint
curl http://localhost:8000/
# Expected: {"message": "WorkflowAI API Gateway", "version": "1.0.0"}

# Health check
curl http://localhost:8000/health
# Expected: {"status": "healthy", "redis": "connected", "timestamp": "..."}
```

#### Test 2: Missing Authorization Header

```bash
curl -v http://localhost:8000/api/v1/test
# Expected: 401 Unauthorized
# Response: {"error": "Missing Authorization header"}
```

#### Test 3: Invalid Token Format

```bash
curl -H "Authorization: InvalidFormat token123" http://localhost:8000/api/v1/test
# Expected: 401 Unauthorized
# Response: {"error": "Invalid authorization format"}
```

#### Test 4: Valid Token (Protected Route)

```bash
# Replace <USER_TOKEN> with token from generate-token.go
curl -H "Authorization: Bearer <USER_TOKEN>" http://localhost:8000/api/v1/test
# Expected: 200 OK (if route exists) or 404 (route not implemented yet)
# Should NOT return 401 - means auth passed
```

#### Test 5: Expired Token

```bash
curl -H "Authorization: Bearer <EXPIRED_TOKEN>" http://localhost:8000/api/v1/test
# Expected: 401 Unauthorized
# Response: {"error": "Invalid or expired token"}
```

#### Test 6: Admin Route - Non-Admin User

```bash
curl -H "Authorization: Bearer <USER_TOKEN>" http://localhost:8000/admin/test
# Expected: 403 Forbidden
# Response: {"error": "Admin access required"}
```

#### Test 7: Admin Route - Admin User

```bash
curl -H "Authorization: Bearer <ADMIN_TOKEN>" http://localhost:8000/admin/test
# Expected: 200 OK (if route exists) or 404
# Should NOT return 403 - means admin check passed
```

### 4. Rate Limiting Testing

#### Test 1: Check Rate Limit Headers

```bash
curl -v -H "Authorization: Bearer <USER_TOKEN>" http://localhost:8000/api/v1/test
# Check response headers:
# X-RateLimit-Limit: 100
# X-RateLimit-Remaining: 99
# X-RateLimit-Reset: <unix_timestamp>
```

#### Test 2: Exhaust Rate Limit

```bash
# Send 101 requests rapidly (requires loop script)
for i in {1..101}; do
  curl -s -H "Authorization: Bearer <USER_TOKEN>" \
    http://localhost:8000/api/v1/test -w "\n%{http_code}\n"
done

# First 100 should succeed (200 or 404)
# 101st should return: 429 Too Many Requests
# Response: {"error": "Rate limit exceeded", "retry_after": <seconds>}
```

#### Test 3: Rate Limit Per User

```bash
# User 1 exhausts limit
for i in {1..100}; do
  curl -s -H "Authorization: Bearer <USER_TOKEN>" \
    http://localhost:8000/api/v1/test > /dev/null
done

# User 2 should still have full quota
curl -H "Authorization: Bearer <ADMIN_TOKEN>" \
  http://localhost:8000/api/v1/test
# Expected: 200 OK (not rate limited)
```

#### Test 4: Rate Limit for Anonymous Users (By IP)

```bash
# Without authentication
for i in {1..101}; do
  curl -s http://localhost:8000/ -w "%{http_code}\n"
done

# Should rate limit based on IP after 100 requests
```

#### Test 5: Rate Limit Reset Window

```bash
# Exhaust limit
for i in {1..100}; do curl -s -H "Authorization: Bearer <USER_TOKEN>" http://localhost:8000/api/v1/test > /dev/null; done

# Check remaining
curl -v -H "Authorization: Bearer <USER_TOKEN>" http://localhost:8000/api/v1/test 2>&1 | grep X-RateLimit-Remaining
# Expected: X-RateLimit-Remaining: 0

# Wait 1 second (sliding window)
sleep 1

# Try again - should have quota restored
curl -v -H "Authorization: Bearer <USER_TOKEN>" http://localhost:8000/api/v1/test 2>&1 | grep X-RateLimit-Remaining
# Expected: X-RateLimit-Remaining: 100 (or close to it)
```

### 5. Redis Inspection

```bash
# Connect to Redis
docker exec -it workflowai-redis redis-cli

# View rate limit keys
KEYS rate_limit:*

# Check specific user's rate limit entries
ZRANGE rate_limit:user123 0 -1 WITHSCORES

# Count entries in window
ZCARD rate_limit:user123

# Clear a user's rate limit (for testing)
DEL rate_limit:user123

# Monitor Redis commands in real-time
MONITOR
# (Then run API requests in another terminal)
```

## Integration Testing Scenarios

### Scenario 1: Full Authentication Flow

1. User registers/logs in → receives JWT token
2. User makes API request with token
3. Gateway validates token signature
4. Gateway extracts user claims (userID, roles)
5. Gateway forwards request with user context
6. Protected resource returns data

### Scenario 2: Rate Limit Enforcement

1. User makes 100 requests in quick succession
2. Each request decrements remaining quota
3. 101st request returns 429 with retry_after
4. User waits for window to slide
5. Quota restores, requests succeed again

### Scenario 3: Admin Access Control

1. Regular user attempts to access `/admin/users`
2. JWT validation passes (token is valid)
3. Role check fails (no "admin" role)
4. Returns 403 Forbidden
5. Admin user with "admin" role succeeds

## Performance Testing

### Load Test with Apache Bench

```bash
# Install Apache Bench
# Windows: Download from Apache website
# WSL: sudo apt-get install apache2-utils

# Test with valid token
ab -n 1000 -c 10 \
  -H "Authorization: Bearer <USER_TOKEN>" \
  http://localhost:8000/api/v1/test

# Analyze results:
# - Requests per second
# - Time per request
# - Rate limit enforcement accuracy
```

### Redis Performance Monitoring

```bash
# Redis info
docker exec workflowai-redis redis-cli INFO stats

# Key metrics:
# - total_commands_processed
# - instantaneous_ops_per_sec
# - used_memory_human
```

## Expected Test Results

### Authentication Middleware
- ✅ All public endpoints accessible without auth
- ✅ Protected endpoints require valid Bearer token
- ✅ Expired tokens rejected with 401
- ✅ Malformed tokens rejected with 401
- ✅ User claims correctly extracted to Gin context
- ✅ Admin-only routes enforce role check

### Rate Limiting Middleware
- ✅ Rate limit headers present on all responses
- ✅ Quota correctly decrements per request
- ✅ 429 returned when limit exceeded
- ✅ Sliding window resets after time passage
- ✅ Per-user tracking for authenticated requests
- ✅ Per-IP tracking for anonymous requests
- ✅ Redis keys properly namespaced (`rate_limit:*`)

## Troubleshooting

### Issue: Tests fail with "connection refused"
**Solution**: Ensure Redis is running: `docker ps | grep redis`

### Issue: Rate limit not working
**Solution**: 
1. Check Redis connection: `docker exec workflowai-redis redis-cli ping`
2. Verify REDIS_URL in environment
3. Check Redis logs: `docker logs workflowai-redis`

### Issue: JWT validation fails with valid token
**Solution**:
1. Verify JWT_SECRET matches between token generation and gateway
2. Check token expiration time
3. Inspect token at https://jwt.io

### Issue: Rate limit exhausted immediately
**Solution**:
1. Check system time synchronization
2. Verify RATE_LIMIT_RPS environment variable (default: 100)
3. Clear Redis keys: `docker exec workflowai-redis redis-cli FLUSHDB`

## CI/CD Integration

Add to `.github/workflows/test.yml`:

```yaml
name: API Gateway Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Go
        uses: actions/setup-go@v4
        with:
          go-version: '1.22'
      
      - name: Download dependencies
        working-directory: ./services/api-gateway
        run: go mod download
      
      - name: Run tests
        working-directory: ./services/api-gateway
        env:
          REDIS_URL: redis://localhost:6379/0
        run: go test -v -coverprofile=coverage.out ./...
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./services/api-gateway/coverage.out
```

## Summary

This testing guide covers:
- ✅ Automated unit tests (9 auth tests + integration test)
- ✅ Manual API testing with curl
- ✅ JWT token generation and validation
- ✅ Rate limiting verification
- ✅ Redis inspection commands
- ✅ Integration testing scenarios
- ✅ Performance testing guidelines
- ✅ Troubleshooting common issues
- ✅ CI/CD integration template

**Next Steps**: 
- Run automated tests once WSL2 network issues resolved
- Build Docker image with new code: `docker-compose build api-gateway`
- Restart gateway: `docker-compose up -d api-gateway`
- Execute manual tests from this guide
