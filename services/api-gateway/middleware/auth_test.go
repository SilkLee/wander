package middleware

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
	"workflow-ai/gateway/models"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
)

func TestAuthenticate_MissingAuthHeader(t *testing.T) {
	gin.SetMode(gin.TestMode)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/test", nil)

	handler := Authenticate("test-secret")
	handler(c)

	if w.Code != http.StatusUnauthorized {
		t.Errorf("Expected status 401, got %d", w.Code)
	}
}

func TestAuthenticate_InvalidAuthFormat(t *testing.T) {
	gin.SetMode(gin.TestMode)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/test", nil)
	c.Request.Header.Set("Authorization", "InvalidFormat token123")

	handler := Authenticate("test-secret")
	handler(c)

	if w.Code != http.StatusUnauthorized {
		t.Errorf("Expected status 401, got %d", w.Code)
	}
}

func TestAuthenticate_InvalidToken(t *testing.T) {
	gin.SetMode(gin.TestMode)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/test", nil)
	c.Request.Header.Set("Authorization", "Bearer invalid.token.here")

	handler := Authenticate("test-secret")
	handler(c)

	if w.Code != http.StatusUnauthorized {
		t.Errorf("Expected status 401, got %d", w.Code)
	}
}

func TestAuthenticate_ValidToken(t *testing.T) {
	gin.SetMode(gin.TestMode)

	secret := "test-secret"
	
	// Create valid JWT token
	claims := &models.JWTClaims{
		UserID:   "user123",
		Username: "testuser",
		Roles:    []string{"user"},
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(time.Hour)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
		},
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenString, err := token.SignedString([]byte(secret))
	if err != nil {
		t.Fatalf("Failed to create test token: %v", err)
	}

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/test", nil)
	c.Request.Header.Set("Authorization", "Bearer "+tokenString)

	// Track if Next() was called
	nextCalled := false
	c.Next = func() {
		nextCalled = true
	}

	handler := Authenticate(secret)
	handler(c)

	if !nextCalled {
		t.Error("Expected Next() to be called with valid token")
	}

	// Verify claims were stored in context
	userID, exists := c.Get("userID")
	if !exists || userID != "user123" {
		t.Errorf("Expected userID=user123 in context, got %v", userID)
	}

	username, exists := c.Get("username")
	if !exists || username != "testuser" {
		t.Errorf("Expected username=testuser in context, got %v", username)
	}

	roles, exists := c.Get("roles")
	if !exists {
		t.Error("Expected roles in context")
	}
	roleList, ok := roles.([]string)
	if !ok || len(roleList) != 1 || roleList[0] != "user" {
		t.Errorf("Expected roles=[user] in context, got %v", roles)
	}
}

func TestAuthenticate_ExpiredToken(t *testing.T) {
	gin.SetMode(gin.TestMode)

	secret := "test-secret"
	
	// Create expired JWT token
	claims := &models.JWTClaims{
		UserID:   "user123",
		Username: "testuser",
		Roles:    []string{"user"},
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(-time.Hour)), // Expired 1 hour ago
			IssuedAt:  jwt.NewNumericDate(time.Now().Add(-2 * time.Hour)),
		},
	}
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenString, err := token.SignedString([]byte(secret))
	if err != nil {
		t.Fatalf("Failed to create test token: %v", err)
	}

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/test", nil)
	c.Request.Header.Set("Authorization", "Bearer "+tokenString)

	handler := Authenticate(secret)
	handler(c)

	if w.Code != http.StatusUnauthorized {
		t.Errorf("Expected status 401 for expired token, got %d", w.Code)
	}
}

func TestRequireAdmin_NoRoles(t *testing.T) {
	gin.SetMode(gin.TestMode)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/admin", nil)

	handler := RequireAdmin()
	handler(c)

	if w.Code != http.StatusForbidden {
		t.Errorf("Expected status 403, got %d", w.Code)
	}
}

func TestRequireAdmin_NonAdminRole(t *testing.T) {
	gin.SetMode(gin.TestMode)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/admin", nil)
	c.Set("roles", []string{"user", "editor"})

	handler := RequireAdmin()
	handler(c)

	if w.Code != http.StatusForbidden {
		t.Errorf("Expected status 403 for non-admin, got %d", w.Code)
	}
}

func TestRequireAdmin_WithAdminRole(t *testing.T) {
	gin.SetMode(gin.TestMode)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/admin", nil)
	c.Set("roles", []string{"user", "admin"})

	// Track if Next() was called
	nextCalled := false
	c.Next = func() {
		nextCalled = true
	}

	handler := RequireAdmin()
	handler(c)

	if !nextCalled {
		t.Error("Expected Next() to be called for admin user")
	}
}

func TestRequireAdmin_InvalidRolesType(t *testing.T) {
	gin.SetMode(gin.TestMode)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest("GET", "/admin", nil)
	c.Set("roles", "not-a-slice") // Invalid type

	handler := RequireAdmin()
	handler(c)

	if w.Code != http.StatusForbidden {
		t.Errorf("Expected status 403 for invalid roles type, got %d", w.Code)
	}
}
