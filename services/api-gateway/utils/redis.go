package utils

import (
	"context"
	"time"

	"github.com/redis/go-redis/v9"
)

var rdb *redis.Client

// Z is an alias for redis.Z
type Z = redis.Z

func InitRedis(redisURL string) error {
	opt, err := redis.ParseURL(redisURL)
	if err != nil {
		return err
	}

	rdb = redis.NewClient(opt)

	// Test connection
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	_, err = rdb.Ping(ctx).Result()
	return err
}

func GetRedisClient() *redis.Client {
	return rdb
}

func CloseRedis() error {
	if rdb != nil {
		return rdb.Close()
	}
	return nil
}
