package handlers

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"workflow-ai/ingestion/parser"
	"workflow-ai/ingestion/streams"
)

// WebhookHandler handles GitHub webhook events
type WebhookHandler struct {
	publisher     *streams.Publisher
	webhookSecret string
}

// NewWebhookHandler creates a new webhook handler
func NewWebhookHandler(publisher *streams.Publisher, webhookSecret string) *WebhookHandler {
	return &WebhookHandler{
		publisher:     publisher,
		webhookSecret: webhookSecret,
	}
}

// GitHubWorkflowEvent represents a GitHub Actions workflow event
type GitHubWorkflowEvent struct {
	Action       string       `json:"action"`
	WorkflowRun  WorkflowRun  `json:"workflow_run"`
	Repository   Repository   `json:"repository"`
	Organization Organization `json:"organization,omitempty"`
}

type WorkflowRun struct {
	ID         int64     `json:"id"`
	Name       string    `json:"name"`
	HeadBranch string    `json:"head_branch"`
	HeadSHA    string    `json:"head_sha"`
	Status     string    `json:"status"`
	Conclusion string    `json:"conclusion"`
	URL        string    `json:"url"`
	LogsURL    string    `json:"logs_url"`
	CreatedAt  time.Time `json:"created_at"`
	UpdatedAt  time.Time `json:"updated_at"`
}

type Repository struct {
	Name     string `json:"name"`
	FullName string `json:"full_name"`
	Private  bool   `json:"private"`
}

type Organization struct {
	Login string `json:"login"`
}

// HandleWebhook handles incoming webhook POST requests
func (h *WebhookHandler) HandleWebhook(c *gin.Context) {
	// Verify webhook signature
	signature := c.GetHeader("X-Hub-Signature-256")
	if signature == "" {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Missing signature"})
		return
	}

	// Read body
	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		log.Printf("Error reading request body: %v", err)
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request body"})
		return
	}

	// Verify signature
	if !h.verifySignature(body, signature) {
		log.Printf("Invalid webhook signature")
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid signature"})
		return
	}

	// Check event type
	eventType := c.GetHeader("X-GitHub-Event")
	if eventType != "workflow_run" {
		// Ignore non-workflow events
		c.JSON(http.StatusOK, gin.H{"message": "Event ignored", "type": eventType})
		return
	}

	// Parse webhook payload
	var event GitHubWorkflowEvent
	if err := json.Unmarshal(body, &event); err != nil {
		log.Printf("Error parsing webhook payload: %v", err)
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
		return
	}

	// Only process completed workflows with failure
	if event.Action != "completed" || event.WorkflowRun.Conclusion == "success" {
		c.JSON(http.StatusOK, gin.H{
			"message": "Workflow not failed, ignoring",
			"action":  event.Action,
			"status":  event.WorkflowRun.Status,
		})
		return
	}

	log.Printf("Processing failed workflow: %s (conclusion: %s)",
		event.WorkflowRun.Name, event.WorkflowRun.Conclusion)

	// Process the failure
	if err := h.processWorkflowFailure(c.Request.Context(), &event); err != nil {
		log.Printf("Error processing workflow failure: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Processing failed"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message":    "Webhook processed successfully",
		"workflow":   event.WorkflowRun.Name,
		"repository": event.Repository.FullName,
		"conclusion": event.WorkflowRun.Conclusion,
	})
}

// HandleManualLog handles manual log submission (for testing)
func (h *WebhookHandler) HandleManualLog(c *gin.Context) {
	var req struct {
		LogContent string `json:"log_content" binding:"required"`
		LogType    string `json:"log_type" binding:"required"`
		Repository string `json:"repository"`
		Branch     string `json:"branch"`
		Commit     string `json:"commit"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Parse log type
	var logType parser.LogType
	switch strings.ToLower(req.LogType) {
	case "build":
		logType = parser.LogTypeBuild
	case "deploy":
		logType = parser.LogTypeDeploy
	case "test":
		logType = parser.LogTypeTest
	default:
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid log_type (must be: build, deploy, test)"})
		return
	}

	// Parse log content
	signal := parser.ParseLog(req.LogContent, logType)

	// Create log event
	event := &streams.LogEvent{
		EventID:       uuid.New().String(),
		Timestamp:     time.Now(),
		Source:        "manual",
		Repository:    req.Repository,
		Branch:        req.Branch,
		Commit:        req.Commit,
		LogType:       string(logType),
		LogContent:    req.LogContent,
		FailureSignal: signal,
	}

	// Publish to stream
	ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
	defer cancel()

	if err := h.publisher.Publish(ctx, event); err != nil {
		log.Printf("Error publishing event: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to publish event"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message":        "Log submitted successfully",
		"event_id":       event.EventID,
		"failure_signal": signal,
	})
}

// processWorkflowFailure processes a failed workflow
func (h *WebhookHandler) processWorkflowFailure(ctx context.Context, event *GitHubWorkflowEvent) error {
	// In a real implementation, we would fetch logs from event.WorkflowRun.LogsURL
	// For now, we'll create a placeholder log content
	logContent := fmt.Sprintf(`Workflow failed: %s
Repository: %s
Branch: %s
Commit: %s
Conclusion: %s
Logs URL: %s

ERROR: Workflow execution failed
Exit code: 1`,
		event.WorkflowRun.Name,
		event.Repository.FullName,
		event.WorkflowRun.HeadBranch,
		event.WorkflowRun.HeadSHA,
		event.WorkflowRun.Conclusion,
		event.WorkflowRun.LogsURL,
	)

	// Parse log content
	signal := parser.ParseLog(logContent, parser.LogTypeBuild)

	// Create log event
	logEvent := &streams.LogEvent{
		EventID:       uuid.New().String(),
		Timestamp:     time.Now(),
		Source:        "github",
		Repository:    event.Repository.FullName,
		Branch:        event.WorkflowRun.HeadBranch,
		Commit:        event.WorkflowRun.HeadSHA,
		LogType:       string(parser.LogTypeBuild),
		LogContent:    logContent,
		FailureSignal: signal,
	}

	// Publish to stream
	return h.publisher.Publish(ctx, logEvent)
}

// verifySignature verifies GitHub webhook signature
func (h *WebhookHandler) verifySignature(body []byte, signature string) bool {
	if h.webhookSecret == "" || h.webhookSecret == "changeme-in-production" {
		// Skip verification in development mode
		log.Println("Warning: Webhook signature verification disabled (development mode)")
		return true
	}

	// GitHub sends signature as "sha256=<hash>"
	if !strings.HasPrefix(signature, "sha256=") {
		return false
	}

	expectedMAC := signature[7:] // Remove "sha256=" prefix

	// Compute HMAC
	mac := hmac.New(sha256.New, []byte(h.webhookSecret))
	mac.Write(body)
	actualMAC := hex.EncodeToString(mac.Sum(nil))

	return hmac.Equal([]byte(actualMAC), []byte(expectedMAC))
}
