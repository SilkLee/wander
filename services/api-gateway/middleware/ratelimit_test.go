package middleware

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
	"workflow-ai/gateway/utils"

	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
)

// Mock Redis client for testing
type mockRedisClient struct {
	redis.UniversalClient
	data map[string][]redis.Z
}

func newMockRedisClient() *mockRedisClient {
	return &mockRedisClient{
		data: make(map[string][]redis.Z),
	}
}

func (m *mockRedisClient) ZRemRangeByScore(ctx context.Context, key string, min, max string) *redis.IntCmd {
	// Simple mock: just return success
	cmd := redis.NewIntCmd(ctx)
	cmd.SetVal(0)
	return cmd
}

func (m *mockRedisClient) ZCard(ctx context.Context, key string) *redis.IntCmd {
	cmd := redis.NewIntCmd(ctx)
	if entries, exists := m.data[key]; exists {
		cmd.SetVal(int64(len(entries)))
	} else {
		cmd.SetVal(0)
	}
	return cmd
}

func (m *mockRedisClient) ZAdd(ctx context.Context, key string, members ...redis.Z) *redis.IntCmd {
	if _, exists := m.data[key]; !exists {
		m.data[key] = []redis.Z{}
	}
	m.data[key] = append(m.data[key], members...)
	
	cmd := redis.NewIntCmd(ctx)
	cmd.SetVal(int64(len(members)))
	return cmd
}

func (m *mockRedisClient) Expire(ctx context.Context, key string, expiration time.Duration) *redis.BoolCmd {
	cmd := redis.NewBoolCmd(ctx)
	cmd.SetVal(true)
	return cmd
}

func TestRateLimit_FirstRequest(t *testing.T) {
	gin.SetMode(gin.TestMode)

	// Initialize mock Redis
	mockRedis := newMockRedisClient()
	
	// Temporarily replace Redis client
	// Note: This requires modifying utils package to allow injection
	// For now, we'll test the basic flow

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/test", nil)
	c.Set("userID", "user123")

	// Test would need actual Redis or more sophisticated mocking
	// This is a basic structure test
	handler := RateLimit(100)
	
	// Can't run without real Redis, but code compiles
	_ = handler
	_ = mockRedis
	
	// For actual testing, would need:
	// 1. Real Redis instance (via testcontainers)
	// 2. Or dependency injection in middleware
	t.Skip("Requires Redis instance - integration test")
}

func TestRateLimit_NoAuth_UsesIP(t *testing.T) {
	gin.SetMode(gin.TestMode)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/test", nil)
	// No userID set - should use IP

	handler := RateLimit(100)
	_ = handler
	
	t.Skip("Requires Redis instance - integration test")
}

func TestRateLimit_ExceedsLimit(t *testing.T) {
	gin.SetMode(gin.TestMode)

	// This test would require:
	// 1. Real Redis connection
	// 2. Making multiple requests rapidly
	// 3. Verifying 429 status on limit exceeded
	
	t.Skip("Requires Redis instance - integration test")
}

func TestRateLimit_Headers(t *testing.T) {
	gin.SetMode(gin.TestMode)

	// This test would verify:
	// - X-RateLimit-Limit header is set
	// - X-RateLimit-Remaining decreases
	// - X-RateLimit-Reset is reasonable
	
	t.Skip("Requires Redis instance - integration test")
}

func TestRateLimit_SlidingWindow(t *testing.T) {
	gin.SetMode(gin.TestMode)

	// This test would verify sliding window behavior:
	// 1. Make requests at t=0, t=0.5, t=1.0
	// 2. Verify old requests (t=0) are removed after window
	// 3. Verify new requests are allowed after old ones expire
	
	t.Skip("Requires Redis instance - integration test")
}

// Integration test helper (requires real Redis)
func setupTestRedis(t *testing.T) {
	// This would initialize Redis for integration tests
	// using testcontainers or similar
	err := utils.InitRedis("redis://localhost:6379/15") // Use test DB
	if err != nil {
		t.Skip("Redis not available for integration tests")
	}
}

func teardownTestRedis(t *testing.T) {
	ctx := context.Background()
	rdb := utils.GetRedisClient()
	if rdb != nil {
		// Clean up test data
		rdb.FlushDB(ctx)
		utils.CloseRedis()
	}
}

func TestRateLimit_Integration(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test")
	}

	setupTestRedis(t)
	defer teardownTestRedis(t)

	gin.SetMode(gin.TestMode)

	// Test with real Redis
	requestsPerSecond := 5

	// Make 5 requests (should all succeed)
	for i := 0; i < requestsPerSecond; i++ {
		w := httptest.NewRecorder()
		c, _ := gin.CreateTestContext(w)
		c.Request = httptest.NewRequest("GET", "/test", nil)
		c.Set("userID", "user123")

		nextCalled := false
		c.Next = func() {
			nextCalled = true
		}

		handler := RateLimit(requestsPerSecond)
		handler(c)

		if !nextCalled {
			t.Errorf("Request %d should have succeeded (rate limit not exceeded)", i+1)
		}

		// Check headers
		limit := w.Header().Get("X-RateLimit-Limit")
		if limit != "5" {
			t.Errorf("Expected X-RateLimit-Limit=5, got %s", limit)
		}
	}

	// 6th request should be rate limited
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/test", nil)
	c.Set("userID", "user123")

	handler := RateLimit(requestsPerSecond)
	handler(c)

	if w.Code != http.StatusTooManyRequests {
		t.Errorf("Expected status 429 for rate limited request, got %d", w.Code)
	}

	remaining := w.Header().Get("X-RateLimit-Remaining")
	if remaining != "0" {
		t.Errorf("Expected X-RateLimit-Remaining=0, got %s", remaining)
	}
}
