package config

import (
	"log"
	"os"
	"strconv"

	"github.com/joho/godotenv"
)

type Config struct {
	// Server
	Port  string
	Debug bool

	// JWT
	JWTSecret string

	// Redis
	RedisURL string

	// Rate Limiting
	RateLimitRPS int

	// CORS
	AllowedOrigins []string

	// Downstream services
	AgentServiceURL     string
	IngestionServiceURL string
	IndexingServiceURL  string
	ModelServiceURL     string
	MetricsServiceURL   string
}

func Load() *Config {
	// Load .env file (ignore error in production)
	_ = godotenv.Load()

	cfg := &Config{
		Port:               getEnv("PORT", "8000"),
		Debug:              getEnvBool("DEBUG", true),
		JWTSecret:          getEnv("JWT_SECRET", "changeme-in-production"),
		RedisURL:           getEnv("REDIS_URL", "redis://localhost:6379/0"),
		RateLimitRPS:       getEnvInt("RATE_LIMIT_RPS", 100),
		AllowedOrigins:     []string{getEnv("CORS_ORIGIN", "http://localhost:3000")},
		AgentServiceURL:     getEnv("AGENT_SERVICE_URL", "http://localhost:8002"),
		IngestionServiceURL: getEnv("INGESTION_SERVICE_URL", "http://localhost:8001"),
		IndexingServiceURL:  getEnv("INDEXING_SERVICE_URL", "http://localhost:8003"),
		ModelServiceURL:     getEnv("MODEL_SERVICE_URL", "http://localhost:8004"),
		MetricsServiceURL:   getEnv("METRICS_SERVICE_URL", "http://localhost:8005"),
	}

	// Validate required fields
	if cfg.JWTSecret == "changeme-in-production" {
		log.Println("WARNING: Using default JWT secret. Set JWT_SECRET in production!")
	}

	return cfg
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvBool(key string, defaultValue bool) bool {
	if value := os.Getenv(key); value != "" {
		result, err := strconv.ParseBool(value)
		if err != nil {
			return defaultValue
		}
		return result
	}
	return defaultValue
}

func getEnvInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		result, err := strconv.Atoi(value)
		if err != nil {
			return defaultValue
		}
		return result
	}
	return defaultValue
}
