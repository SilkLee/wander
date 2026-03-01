package main

import (
	"log"
	"os"
	"os/signal"
	"syscall"
	"workflow-ai/gateway/config"
	"workflow-ai/gateway/internal/interfaces/http"
	"workflow-ai/gateway/utils"
)

func main() {
	// 1. Load configuration
	cfg := config.Load()

	// 2. Initialize infrastructure
	if err := utils.InitRedis(cfg.RedisURL); err != nil {
		log.Fatalf("Failed to connect to Redis: %v", err)
	}
	defer utils.CloseRedis()

	// 3. Initialize HTTP router with all dependencies
	router := http.NewRouter(cfg)

	// 4. Start server in background
	go func() {
		if err := router.Run(cfg.Port); err != nil {
			log.Fatalf("Server failed: %v", err)
		}
	}()

	// 5. Wait for interrupt signal for graceful shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("Server shutting down...")
}
