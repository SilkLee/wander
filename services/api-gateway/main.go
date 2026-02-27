package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
	"workflow-ai/gateway/config"
	"workflow-ai/gateway/middleware"
	"workflow-ai/gateway/utils"

	"github.com/gin-gonic/gin"
)

func main() {
	// Load configuration
	cfg := config.Load()

	// Initialize Redis
	if err := utils.InitRedis(cfg.RedisURL); err != nil {
		log.Fatalf("Failed to connect to Redis: %v", err)
	}
	defer utils.CloseRedis()

	// Set Gin mode
	if !cfg.Debug {
		gin.SetMode(gin.ReleaseMode)
	}

	// Create Gin router
	r := gin.Default()

	// CORS middleware
	r.Use(func(c *gin.Context) {
		origin := c.Request.Header.Get("Origin")
		allowed := false
		for _, allowedOrigin := range cfg.AllowedOrigins {
			if allowedOrigin == "*" || allowedOrigin == origin {
				allowed = true
				break
			}
		}

		if allowed {
			c.Writer.Header().Set("Access-Control-Allow-Origin", origin)
		}

		c.Writer.Header().Set("Access-Control-Allow-Credentials", "true")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH, OPTIONS")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
		c.Writer.Header().Set("Access-Control-Max-Age", "86400")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}

		c.Next()
	})

	// Public routes (no auth required)
	r.GET("/", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"service": "WorkflowAI API Gateway",
			"version": "0.1.0",
			"time":    time.Now().UTC(),
		})
	})

	r.GET("/health", func(c *gin.Context) {
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
	})

	// Protected API routes (require JWT)
	api := r.Group("/api/v1")
	api.Use(middleware.RateLimit(cfg.RateLimitRPS))
	api.Use(middleware.Authenticate(cfg.JWTSecret))
	{
		// Ingestion Service - Data ingestion and processing
		api.POST("/ingest", utils.ProxyToService(cfg.IngestionServiceURL))
		api.GET("/ingest/health", utils.ProxyToService(cfg.IngestionServiceURL+"/health"))

		// Indexing Service - Vector embeddings and search
		api.POST("/index", utils.ProxyToService(cfg.IndexingServiceURL))
		api.POST("/index/batch", utils.ProxyToService(cfg.IndexingServiceURL+"/index/batch"))
		api.POST("/search", utils.ProxyToService(cfg.IndexingServiceURL))
		api.GET("/stats", utils.ProxyToService(cfg.IndexingServiceURL))

		// Agent Orchestrator - Workflow coordination
		api.POST("/execute", utils.ProxyToService(cfg.AgentServiceURL))
		api.GET("/execute/:id", utils.ProxyToService(cfg.AgentServiceURL+"/execute"))

		// Placeholder for future routes
		api.GET("/workflows", func(c *gin.Context) {
			userID, _ := c.Get("userID")
			c.JSON(http.StatusOK, gin.H{
				"message": "Workflows endpoint",
				"user_id": userID,
			})
		})
	}

	// Admin routes (require admin role)
	admin := r.Group("/admin")
	admin.Use(middleware.RateLimit(cfg.RateLimitRPS))
	admin.Use(middleware.Authenticate(cfg.JWTSecret))
	admin.Use(middleware.RequireAdmin())
	{
		admin.GET("/stats", func(c *gin.Context) {
			c.JSON(http.StatusOK, gin.H{
				"uptime":    "TODO: track uptime",
				"requests":  "TODO: track total requests",
				"errors":    "TODO: track error count",
				"timestamp": time.Now().UTC(),
			})
		})
	}

	// Create server with graceful shutdown
	srv := &http.Server{
		Addr:    ":" + cfg.Port,
		Handler: r,
	}

	// Start server in goroutine
	go func() {
		log.Printf("Starting API Gateway on port %s", cfg.Port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Failed to start server: %v", err)
		}
	}()

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("Shutting down server...")

	// Graceful shutdown with 5s timeout
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		log.Fatal("Server forced to shutdown:", err)
	}

	log.Println("Server exited")
}