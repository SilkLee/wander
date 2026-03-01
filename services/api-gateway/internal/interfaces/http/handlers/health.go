package handlers

import (
	"context"
	"net/http"
	"time"
	"workflow-ai/gateway/utils"

	"github.com/gin-gonic/gin"
)

// HealthHandler handles health check requests
type HealthHandler struct{}

// NewHealthHandler creates a new HealthHandler
func NewHealthHandler() *HealthHandler {
	return &HealthHandler{}
}

// Check performs health check including Redis connection
func (h *HealthHandler) Check(c *gin.Context) {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	// Check Redis connection
	rdb := utils.GetRedisClient()
	_, err := rdb.Ping(ctx).Result()

	if err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"status": "unhealthy",
			"redis":  "disconnected",
			"error":  err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status": "healthy",
		"redis":  "connected",
		"time":   time.Now().UTC(),
	})
}
