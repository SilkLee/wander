package middleware

import (
	"bytes"
	"context"
	"fmt"
	"net/http"
	"time"
	"workflow-ai/gateway/utils"

	"github.com/gin-gonic/gin"
)

// cachedResponseWriter captures the response body for caching.
type cachedResponseWriter struct {
	gin.ResponseWriter
	body *bytes.Buffer
}

func (w *cachedResponseWriter) Write(b []byte) (int, error) {
	w.body.Write(b)
	return w.ResponseWriter.Write(b)
}

// CacheResponse returns middleware that caches GET responses in Redis.
// Only successful (2xx) JSON responses are cached. Non-GET methods bypass cache.
func CacheResponse(ttl time.Duration) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Only cache GET requests
		if c.Request.Method != http.MethodGet {
			c.Next()
			return
		}

		rdb := utils.GetRedisClient()
		if rdb == nil {
			// No Redis — skip caching, serve normally
			c.Next()
			return
		}

		key := fmt.Sprintf("cache:%s", c.Request.URL.RequestURI())
		ctx := context.Background()

		// Try cache hit
		cached, err := rdb.Get(ctx, key).Bytes()
		if err == nil && len(cached) > 0 {
			c.Header("X-Cache", "HIT")
			c.Header("Content-Type", "application/json")
			c.Writer.WriteHeader(http.StatusOK)
			c.Writer.Write(cached)
			c.Abort()
			return
		}

		// Cache miss — capture response
		c.Header("X-Cache", "MISS")
		writer := &cachedResponseWriter{
			ResponseWriter: c.Writer,
			body:           bytes.NewBuffer(nil),
		}
		c.Writer = writer

		c.Next()

		// Only cache successful JSON responses
		status := c.Writer.Status()
		if status >= 200 && status < 300 && writer.body.Len() > 0 {
			rdb.Set(ctx, key, writer.body.Bytes(), ttl)
		}
	}
}
