package http

import (
	"context"
	"log"
	"net/http"
	"time"
	"workflow-ai/gateway/config"
	"workflow-ai/gateway/internal/interfaces/http/handlers"
	"workflow-ai/gateway/internal/interfaces/http/middleware"

	"github.com/gin-gonic/gin"
)

// Router encapsulates HTTP routing and server lifecycle
type Router struct {
	engine *gin.Engine
	server *http.Server
	config *config.Config
}

// NewRouter creates a new HTTP router with all dependencies injected
func NewRouter(cfg *config.Config) *Router {
	// Set Gin mode
	if !cfg.Debug {
		gin.SetMode(gin.ReleaseMode)
	}

	engine := gin.Default()

	// Apply global middleware
	engine.Use(corsMiddleware(cfg))

	router := &Router{
		engine: engine,
		config: cfg,
	}

	// Setup routes
	router.setupRoutes()

	return router
}

// setupRoutes configures all HTTP routes
func (r *Router) setupRoutes() {
	cfg := r.config

	// Initialize handlers
	healthHandler := handlers.NewHealthHandler()
	proxyHandler := handlers.NewProxyHandler(cfg)

	// Public routes (no auth required)
	r.engine.GET("/", handlers.RootHandler)
	r.engine.GET("/health", healthHandler.Check)

	// Protected API routes (require JWT)
	api := r.engine.Group("/api/v1")
	api.Use(middleware.RateLimit(cfg.RateLimitRPS))
	api.Use(middleware.Authenticate(cfg.JWTSecret))
	{
		// Ingestion Service
		api.POST("/ingest", proxyHandler.ProxyIngestion)
		api.GET("/ingest/health", proxyHandler.ProxyIngestionHealth)

		// Indexing Service
		api.POST("/index", proxyHandler.ProxyIndex)
		api.POST("/index/batch", proxyHandler.ProxyIndexBatch)
		api.POST("/search", proxyHandler.ProxySearch)
		api.GET("/stats", proxyHandler.ProxyStats)

		// Agent Orchestrator
		api.POST("/execute", proxyHandler.ProxyExecute)
		api.GET("/execute/:id", proxyHandler.ProxyExecuteGet)

		// Model Service
		api.POST("/generate", proxyHandler.ProxyGenerate)
		api.GET("/model/info", proxyHandler.ProxyModelInfo)

		// Placeholder workflows endpoint
		api.GET("/workflows", handlers.WorkflowsHandler)
	}

	// Admin routes (require admin role)
	admin := r.engine.Group("/admin")
	admin.Use(middleware.RateLimit(cfg.RateLimitRPS))
	admin.Use(middleware.Authenticate(cfg.JWTSecret))
	admin.Use(middleware.RequireAdmin())
	{
		admin.GET("/stats", handlers.AdminStatsHandler)
	}
}

// Run starts the HTTP server with graceful shutdown
func (r *Router) Run(port string) error {
	r.server = &http.Server{
		Addr:    ":" + port,
		Handler: r.engine,
	}

	// Start server in goroutine
	go func() {
		log.Printf("Starting API Gateway on port %s", port)
		if err := r.server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Failed to start server: %v", err)
		}
	}()

	// Wait for interrupt signal for graceful shutdown
	return r.waitForShutdown()
}

// waitForShutdown handles graceful shutdown
func (r *Router) waitForShutdown() error {
	quit := make(chan struct{})
	// In production, wire up OS signals here
	<-quit

	log.Println("Shutting down server...")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := r.server.Shutdown(ctx); err != nil {
		return err
	}

	log.Println("Server exited")
	return nil
}

// corsMiddleware creates CORS middleware with configured origins
func corsMiddleware(cfg *config.Config) gin.HandlerFunc {
	return func(c *gin.Context) {
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
	}
}
