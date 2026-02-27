package streams

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/redis/go-redis/v9"
	"workflow-ai/ingestion/parser"
)

// Publisher publishes messages to Redis Streams
type Publisher struct {
	client          *redis.Client
	streamName      string
	maxStreamLength int64
}

// NewPublisher creates a new stream publisher
func NewPublisher(client *redis.Client, streamName string, maxLength int64) *Publisher {
	return &Publisher{
		client:          client,
		streamName:      streamName,
		maxStreamLength: maxLength,
	}
}

// LogEvent represents a log event to be published
type LogEvent struct {
	EventID       string                `json:"event_id"`
	Timestamp     time.Time             `json:"timestamp"`
	Source        string                `json:"source"`
	Repository    string                `json:"repository"`
	Branch        string                `json:"branch"`
	Commit        string                `json:"commit"`
	LogType       string                `json:"log_type"`
	LogContent    string                `json:"log_content"`
	FailureSignal *parser.FailureSignal `json:"failure_signal,omitempty"`
}

// Publish publishes a log event to Redis Streams
func (p *Publisher) Publish(ctx context.Context, event *LogEvent) error {
	// Convert event to JSON
	eventJSON, err := json.Marshal(event)
	if err != nil {
		return fmt.Errorf("failed to marshal event: %w", err)
	}

	// Prepare stream data
	values := map[string]interface{}{
		"event_id":   event.EventID,
		"timestamp":  event.Timestamp.Unix(),
		"source":     event.Source,
		"repository": event.Repository,
		"branch":     event.Branch,
		"commit":     event.Commit,
		"log_type":   event.LogType,
		"data":       string(eventJSON),
	}

	// Add to stream with MAXLEN to prevent unbounded growth
	args := &redis.XAddArgs{
		Stream: p.streamName,
		MaxLen: p.maxStreamLength,
		Approx: true, // Use approximate trimming for better performance
		Values: values,
	}

	messageID, err := p.client.XAdd(ctx, args).Result()
	if err != nil {
		return fmt.Errorf("failed to publish to stream: %w", err)
	}

	log.Printf("Published event %s to stream %s (message ID: %s)",
		event.EventID, p.streamName, messageID)

	return nil
}

// CreateConsumerGroup creates a consumer group for the stream
func (p *Publisher) CreateConsumerGroup(ctx context.Context, groupName string) error {
	// Try to create consumer group (ignore error if already exists)
	err := p.client.XGroupCreateMkStream(ctx, p.streamName, groupName, "0").Err()
	if err != nil && err.Error() != "BUSYGROUP Consumer Group name already exists" {
		return fmt.Errorf("failed to create consumer group: %w", err)
	}

	log.Printf("Consumer group '%s' ready for stream '%s'", groupName, p.streamName)
	return nil
}

// GetStreamInfo gets stream information
func (p *Publisher) GetStreamInfo(ctx context.Context) (int64, error) {
	info, err := p.client.XInfoStream(ctx, p.streamName).Result()
	if err != nil {
		if err == redis.Nil {
			return 0, nil
		}
		return 0, fmt.Errorf("failed to get stream info: %w", err)
	}

	return info.Length, nil
}
