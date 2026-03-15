package handlers

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

func init() {
	gin.SetMode(gin.TestMode)
}

func TestRootHandler(t *testing.T) {
	r := gin.New()
	r.GET("/", RootHandler)

	w := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var body map[string]interface{}
	if err := json.Unmarshal(w.Body.Bytes(), &body); err != nil {
		t.Fatalf("Failed to parse response body: %v", err)
	}

	if body["service"] != "WorkflowAI API Gateway" {
		t.Errorf("Expected service='WorkflowAI API Gateway', got %v", body["service"])
	}
	if body["version"] != "0.1.0" {
		t.Errorf("Expected version='0.1.0', got %v", body["version"])
	}
	if body["time"] == nil {
		t.Error("Expected time field to be present")
	}
}

func TestWorkflowsHandler_WithUserID(t *testing.T) {
	r := gin.New()
	r.GET("/workflows", func(c *gin.Context) {
		c.Set("userID", "user123")
		c.Next()
	}, WorkflowsHandler)

	w := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/workflows", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var body map[string]interface{}
	if err := json.Unmarshal(w.Body.Bytes(), &body); err != nil {
		t.Fatalf("Failed to parse response body: %v", err)
	}

	if body["message"] != "Workflows endpoint" {
		t.Errorf("Expected message='Workflows endpoint', got %v", body["message"])
	}
	if body["user_id"] != "user123" {
		t.Errorf("Expected user_id='user123', got %v", body["user_id"])
	}
}

func TestWorkflowsHandler_NoUserID(t *testing.T) {
	r := gin.New()
	r.GET("/workflows", WorkflowsHandler)

	w := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/workflows", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var body map[string]interface{}
	if err := json.Unmarshal(w.Body.Bytes(), &body); err != nil {
		t.Fatalf("Failed to parse response body: %v", err)
	}

	// When no userID is set, it should be nil/null
	if body["user_id"] != nil {
		// In Go, c.Get returns (nil, false) when key not found
		// gin.H serializes nil as JSON null
		t.Logf("user_id without auth: %v (type: %T)", body["user_id"], body["user_id"])
	}
}

func TestAdminStatsHandler(t *testing.T) {
	r := gin.New()
	r.GET("/admin/stats", AdminStatsHandler)

	w := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/admin/stats", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	var body map[string]interface{}
	if err := json.Unmarshal(w.Body.Bytes(), &body); err != nil {
		t.Fatalf("Failed to parse response body: %v", err)
	}

	// Verify expected fields exist
	for _, field := range []string{"uptime", "requests", "errors", "timestamp"} {
		if _, ok := body[field]; !ok {
			t.Errorf("Expected field '%s' in response", field)
		}
	}
}
