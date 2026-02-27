package config

import (
	"log"
	"os"
	"strconv"

	"github.com/joho/godotenv"
)

// Config holds application configuration
type Config struct {
	Port            string
	Debug           bool
	RedisURL        string
	StreamName      string
	StreamGroup     string
	MaxStreamLength int64
	WebhookSecret   string
}

// Load loads configuration from environment variables
func Load() *Config {
	// Load .env file if exists (ignore error in production)
	_ = godotenv.Load()

	debug := os.Getenv("DEBUG") == "true"

	maxStreamLength, err := strconv.ParseInt(os.Getenv("MAX_STREAM_LENGTH"), 10, 64)
	if err != nil {
		maxStreamLength = 10000 // default
	}

	cfg := &Config{
		Port:            getEnv("PORT", "8001"),
		Debug:           debug,
		RedisURL:        getEnv("REDIS_URL", "redis://localhost:6379/0"),
		StreamName:      getEnv("STREAM_NAME", "workflowai:logs"),
		StreamGroup:     getEnv("STREAM_GROUP", "agent-orchestrator"),
		MaxStreamLength: maxStreamLength,
		WebhookSecret:   getEnv("WEBHOOK_SECRET", "changeme-in-production"),
	}

	log.Printf("Loaded configuration: Port=%s, StreamName=%s", cfg.Port, cfg.StreamName)
	return cfg
}

// getEnv gets environment variable with fallback
func getEnv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}
