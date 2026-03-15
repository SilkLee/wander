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

func init() {
	gin.SetMode(gin.TestMode)
}

// helper: create a test Gin engine with the Authenticate middleware and a
// downstream handler that records whether it was reached.
func authEngine(secret string, downstream func(c *gin.Context)) *gin.Engine {
	r := gin.New()
	r.GET("/test", Authenticate(secret), downstream)
	return r
}

func makeToken(secret string, claims *models.JWTClaims) string {
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	s, _ := token.SignedString([]byte(secret))
	return s
}

func TestAuthenticate_MissingAuthHeader(t *testing.T) {
	reached := false
	r := authEngine("test-secret", func(c *gin.Context) { reached = true })

	w := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/test", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Errorf("Expected status 401, got %d", w.Code)
	}
	if reached {
		t.Error("Handler should not be reached without auth header")
	}
}

func TestAuthenticate_InvalidAuthFormat(t *testing.T) {
	reached := false
	r := authEngine("test-secret", func(c *gin.Context) { reached = true })

	w := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/test", nil)
	req.Header.Set("Authorization", "InvalidFormat token123")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Errorf("Expected status 401, got %d", w.Code)
	}
	if reached {
		t.Error("Handler should not be reached with invalid auth format")
	}
}

func TestAuthenticate_InvalidToken(t *testing.T) {
	reached := false
	r := authEngine("test-secret", func(c *gin.Context) { reached = true })

	w := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/test", nil)
	req.Header.Set("Authorization", "Bearer invalid.token.here")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Errorf("Expected status 401, got %d", w.Code)
	}
	if reached {
		t.Error("Handler should not be reached with invalid token")
	}
}

func TestAuthenticate_ValidToken(t *testing.T) {
	secret := "test-secret"
	var capturedUserID, capturedUsername interface{}
	var capturedRoles interface{}

	r := authEngine(secret, func(c *gin.Context) {
		capturedUserID, _ = c.Get("userID")
		capturedUsername, _ = c.Get("username")
		capturedRoles, _ = c.Get("roles")
		c.Status(http.StatusOK)
	})

	tokenStr := makeToken(secret, &models.JWTClaims{
		UserID:   "user123",
		Username: "testuser",
		Roles:    []string{"user"},
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(time.Hour)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
		},
	})

	w := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/test", nil)
	req.Header.Set("Authorization", "Bearer "+tokenStr)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}
	if capturedUserID != "user123" {
		t.Errorf("Expected userID=user123, got %v", capturedUserID)
	}
	if capturedUsername != "testuser" {
		t.Errorf("Expected username=testuser, got %v", capturedUsername)
	}
	roleList, ok := capturedRoles.([]string)
	if !ok || len(roleList) != 1 || roleList[0] != "user" {
		t.Errorf("Expected roles=[user], got %v", capturedRoles)
	}
}

func TestAuthenticate_ExpiredToken(t *testing.T) {
	secret := "test-secret"
	reached := false
	r := authEngine(secret, func(c *gin.Context) { reached = true })

	tokenStr := makeToken(secret, &models.JWTClaims{
		UserID:   "user123",
		Username: "testuser",
		Roles:    []string{"user"},
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(-time.Hour)),
			IssuedAt:  jwt.NewNumericDate(time.Now().Add(-2 * time.Hour)),
		},
	})

	w := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/test", nil)
	req.Header.Set("Authorization", "Bearer "+tokenStr)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Errorf("Expected status 401 for expired token, got %d", w.Code)
	}
	if reached {
		t.Error("Handler should not be reached with expired token")
	}
}

// --- RequireAdmin tests ---

func adminEngine(downstream func(c *gin.Context)) *gin.Engine {
	r := gin.New()
	// RequireAdmin expects roles to be set in context, so we add a
	// pre-middleware that optionally sets roles from a custom header.
	r.GET("/admin", func(c *gin.Context) {
		// If X-Test-Roles header is set, store it in context.
		// Use a special sentinel: "none" means don't set roles at all.
		if h := c.GetHeader("X-Test-Roles"); h != "" {
			if h == "__invalid_type__" {
				c.Set("roles", "not-a-slice")
			} else {
				var roles []string
				for _, r := range splitRoles(h) {
					if r != "" {
						roles = append(roles, r)
					}
				}
				c.Set("roles", roles)
			}
		}
		c.Next()
	}, RequireAdmin(), downstream)
	return r
}

// splitRoles splits comma-separated roles.
func splitRoles(s string) []string {
	var result []string
	current := ""
	for _, ch := range s {
		if ch == ',' {
			result = append(result, current)
			current = ""
		} else {
			current += string(ch)
		}
	}
	result = append(result, current)
	return result
}

func TestRequireAdmin_NoRoles(t *testing.T) {
	reached := false
	r := adminEngine(func(c *gin.Context) { reached = true; c.Status(http.StatusOK) })

	w := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/admin", nil)
	// No X-Test-Roles header → roles not set
	r.ServeHTTP(w, req)

	if w.Code != http.StatusForbidden {
		t.Errorf("Expected status 403, got %d", w.Code)
	}
	if reached {
		t.Error("Handler should not be reached without roles")
	}
}

func TestRequireAdmin_NonAdminRole(t *testing.T) {
	reached := false
	r := adminEngine(func(c *gin.Context) { reached = true; c.Status(http.StatusOK) })

	w := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/admin", nil)
	req.Header.Set("X-Test-Roles", "user,editor")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusForbidden {
		t.Errorf("Expected status 403 for non-admin, got %d", w.Code)
	}
	if reached {
		t.Error("Handler should not be reached without admin role")
	}
}

func TestRequireAdmin_WithAdminRole(t *testing.T) {
	reached := false
	r := adminEngine(func(c *gin.Context) { reached = true; c.Status(http.StatusOK) })

	w := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/admin", nil)
	req.Header.Set("X-Test-Roles", "user,admin")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}
	if !reached {
		t.Error("Expected handler to be reached for admin user")
	}
}

func TestRequireAdmin_InvalidRolesType(t *testing.T) {
	reached := false
	r := adminEngine(func(c *gin.Context) { reached = true; c.Status(http.StatusOK) })

	w := httptest.NewRecorder()
	req := httptest.NewRequest("GET", "/admin", nil)
	req.Header.Set("X-Test-Roles", "__invalid_type__")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusForbidden {
		t.Errorf("Expected status 403 for invalid roles type, got %d", w.Code)
	}
	if reached {
		t.Error("Handler should not be reached with invalid roles type")
	}
}
