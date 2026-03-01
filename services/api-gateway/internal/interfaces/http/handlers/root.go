package handlers

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
)

// RootHandler handles the root endpoint
func RootHandler(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"service": "WorkflowAI API Gateway",
		"version": "0.1.0",
		"time":    time.Now().UTC(),
	})
}

// WorkflowsHandler handles the workflows endpoint
func WorkflowsHandler(c *gin.Context) {
	userID, _ := c.Get("userID")
	c.JSON(http.StatusOK, gin.H{
		"message": "Workflows endpoint",
		"user_id": userID,
	})
}

// AdminStatsHandler handles the admin stats endpoint
func AdminStatsHandler(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"uptime":    "TODO: track uptime",
		"requests":  "TODO: track total requests",
		"errors":    "TODO: track error count",
		"timestamp": time.Now().UTC(),
	})
}
