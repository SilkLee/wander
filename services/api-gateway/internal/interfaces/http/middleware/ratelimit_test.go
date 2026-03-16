package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"workflow-ai/gateway/utils"

	"github.com/gin-gonic/gin"
)


func rateLimitEngine(rps int, setUserID bool) *gin.Engine {
	r := gin.New()
	r.GET("/test", func(c *gin.Context) {
		if setUserID {
			c.Set("userID", "user123")
		}
		c.Next()
	}, RateLimit(rps), func(c *gin.Context) {
		c.Status(http.StatusOK)
	})
	return r
}

func TestRateLimit_FirstRequest(t *testing.T) {
	// RateLimit requires a running Redis instance — skip in unit tests.
	t.Skip("Requires Redis instance - integration test")
}

func TestRateLimit_NoAuth_UsesIP(t *testing.T) {
	t.Skip("Requires Redis instance - integration test")
}

func TestRateLimit_ExceedsLimit(t *testing.T) {
	t.Skip("Requires Redis instance - integration test")
}

func TestRateLimit_Headers(t *testing.T) {
	t.Skip("Requires Redis instance - integration test")
}

func TestRateLimit_SlidingWindow(t *testing.T) {
	t.Skip("Requires Redis instance - integration test")
}

// setupTestRedis initializes Redis for integration tests.
func setupTestRedis(t *testing.T) {
	t.Helper()
	err := utils.InitRedis("redis://localhost:6379/15") // Use test DB
	if err != nil {
		t.Skip("Redis not available for integration tests")
	}
}

func teardownTestRedis(t *testing.T) {
	t.Helper()
	_ = utils.CloseRedis()
}

func TestRateLimit_Integration(t *testing.T) {
	if testing.Short() {
		t.Skip("Skipping integration test")
	}

	setupTestRedis(t)
	defer teardownTestRedis(t)

	rps := 5
	r := rateLimitEngine(rps, true)

	// Make 5 requests (should all succeed)
	for i := 0; i < rps; i++ {
		w := httptest.NewRecorder()
		req := httptest.NewRequest("GET", "/test", nil)
		r.ServeHTTP(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("Request %d: expected status 200, got %d", i+1, w.Code)
		}

		limit := w.Header().Get("X-RateLimit-Limit")
		if limit != "5" {
			t.Errorf("Expected X-RateLimit-Limit=5, got %s", limit)
		}
	}

	// 6th request should be rate limited
	w := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/test", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusTooManyRequests {
		t.Errorf("Expected status 429 for rate limited request, got %d", w.Code)
	}

	remaining := w.Header().Get("X-RateLimit-Remaining")
	if remaining != "0" {
		t.Errorf("Expected X-RateLimit-Remaining=0, got %s", remaining)
	}
}
