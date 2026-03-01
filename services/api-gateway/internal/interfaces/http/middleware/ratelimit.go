package middleware

import (
	"context"
	"fmt"
	"net/http"
	"time"
	"workflow-ai/gateway/utils"

	"github.com/gin-gonic/gin"
)

// RateLimit implements sliding window rate limiting using Redis
func RateLimit(requestsPerSecond int) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Get user ID from context (set by auth middleware)
		userID, exists := c.Get("userID")
		if !exists {
			// If no auth, use IP address
			userID = c.ClientIP()
		}

		key := fmt.Sprintf("rate_limit:%v", userID)
		ctx := context.Background()

		// Use Redis sorted set for sliding window
		now := time.Now().Unix()
		windowStart := now - 1 // 1 second window

		rdb := utils.GetRedisClient()

		// Remove old entries outside the window
		rdb.ZRemRangeByScore(ctx, key, "0", fmt.Sprintf("%d", windowStart))

		// Count requests in current window
		count, err := rdb.ZCard(ctx, key).Result()
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Rate limit check failed"})
			c.Abort()
			return
		}

		// Check if rate limit exceeded
		if count >= int64(requestsPerSecond) {
			c.Header("X-RateLimit-Limit", fmt.Sprintf("%d", requestsPerSecond))
			c.Header("X-RateLimit-Remaining", "0")
			c.Header("X-RateLimit-Reset", fmt.Sprintf("%d", now+1))
			c.JSON(http.StatusTooManyRequests, gin.H{
				"error":       "Rate limit exceeded",
				"retry_after": 1,
			})
			c.Abort()
			return
		}

		// Add current request to window
		rdb.ZAdd(ctx, key, utils.Z{Score: float64(now), Member: fmt.Sprintf("%d", time.Now().UnixNano())})
		rdb.Expire(ctx, key, 2*time.Second) // TTL slightly longer than window

		// Set rate limit headers
		remaining := requestsPerSecond - int(count) - 1
		c.Header("X-RateLimit-Limit", fmt.Sprintf("%d", requestsPerSecond))
		c.Header("X-RateLimit-Remaining", fmt.Sprintf("%d", remaining))
		c.Header("X-RateLimit-Reset", fmt.Sprintf("%d", now+1))

		c.Next()
	}
}
