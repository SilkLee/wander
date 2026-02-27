package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"workflow-ai/ingestion/config"
	"workflow-ai/ingestion/handlers"
	"workflow-ai/ingestion/streams"
	"workflow-ai/ingestion/utils"
)

func main() {
	// Load configuration
	cfg := config.Load()

	// Initialize Redis
	if err := utils.InitRedis(cfg.RedisURL); err != nil {
		log.Fatalf("Failed to connect to Redis: %v", err)
	}
	defer utils.CloseRedis()

	// Create stream publisher
	publisher := streams.NewPublisher(
		utils.GetRedisClient(),
		cfg.StreamName,
		cfg.MaxStreamLength,
	)

	// Create consumer group for agent orchestrator
	ctx := context.Background()
	if err := publisher.CreateConsumerGroup(ctx, cfg.StreamGroup); err != nil {
		log.Printf("Warning: Failed to create consumer group: %v", err)
	}

	// Set Gin mode
	if !cfg.Debug {
		gin.SetMode(gin.ReleaseMode)
	}

	// Create Gin router
	r := gin.Default()

	// Create webhook handler
	webhookHandler := handlers.NewWebhookHandler(publisher, cfg.WebhookSecret)

	// Health check endpoint
	r.GET("/health", func(c *gin.Context) {
		rdb := utils.GetRedisClient()
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()

		// Check Redis connection
		_, err := rdb.Ping(ctx).Result()
		if err != nil {
			c.JSON(http.StatusServiceUnavailable, gin.H{
				"status": "unhealthy",
				"redis":  "disconnected",
				"error":  err.Error(),
			})
			return
		}

		// Get stream info
		streamLength, err := publisher.GetStreamInfo(ctx)
		if err != nil {
			log.Printf("Warning: Failed to get stream info: %v", err)
		}

		c.JSON(http.StatusOK, gin.H{
			"status":        "healthy",
			"service":       "ingestion",
			"version":       "0.1.0",
			"redis":         "connected",
			"stream":        cfg.StreamName,
			"stream_length": streamLength,
			"time":          time.Now().UTC(),
		})
	})

	// Readiness probe
	r.GET("/ready", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"ready":   true,
			"service": "ingestion",
		})
	})

	// Liveness probe
	r.GET("/live", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"alive":   true,
			"service": "ingestion",
		})
	})

	// Root endpoint
	r.GET("/", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"service": "WorkflowAI Ingestion Service",
			"version": "0.1.0",
			"stream":  cfg.StreamName,
			"time":    time.Now().UTC(),
		})
	})

	// Webhook endpoints
	r.POST("/webhook/github", webhookHandler.HandleWebhook)
	r.POST("/logs/submit", webhookHandler.HandleManualLog)

	// Stream stats endpoint
	r.GET("/stream/stats", func(c *gin.Context) {
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()

		streamLength, err := publisher.GetStreamInfo(ctx)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to get stream info",
			})
			return
		}

		c.JSON(http.StatusOK, gin.H{
			"stream":         cfg.StreamName,
			"length":         streamLength,
			"max_length":     cfg.MaxStreamLength,
			"consumer_group": cfg.StreamGroup,
		})
	})

	// Create HTTP server
	srv := &http.Server{
		Addr:    ":" + cfg.Port,
		Handler: r,
	}

	// Start server in a goroutine
	go func() {
		log.Printf("Starting ingestion service on port %s", cfg.Port)
		log.Printf("Stream: %s, Consumer Group: %s", cfg.StreamName, cfg.StreamGroup)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Failed to start server: %v", err)
		}
	}()

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("Shutting down server...")

	// Graceful shutdown
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		log.Fatal("Server forced to shutdown:", err)
	}

	log.Println("Server exited")
}
