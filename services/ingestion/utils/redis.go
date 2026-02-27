package utils

import (
	"context"
	"log"

	"github.com/redis/go-redis/v9"
)

var (
	rdb *redis.Client
)

// InitRedis initializes Redis connection
func InitRedis(url string) error {
	opt, err := redis.ParseURL(url)
	if err != nil {
		return err
	}

	rdb = redis.NewClient(opt)

	// Test connection
	ctx := context.Background()
	if err := rdb.Ping(ctx).Err(); err != nil {
		return err
	}

	log.Println("Connected to Redis successfully")
	return nil
}

// GetRedisClient returns the Redis client
func GetRedisClient() *redis.Client {
	return rdb
}

// CloseRedis closes Redis connection
func CloseRedis() error {
	if rdb != nil {
		return rdb.Close()
	}
	return nil
}
