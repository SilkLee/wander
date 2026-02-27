package main

import (
	"fmt"
	"os"
	"time"
	"workflow-ai/gateway/models"

	"github.com/golang-jwt/jwt/v5"
)

func main() {
	secret := os.Getenv("JWT_SECRET")
	if secret == "" {
		secret = "changeme-in-production"
	}

	fmt.Println("=== JWT Token Generator ===")
	fmt.Printf("Using secret: %s\n\n", secret)

	// Regular user token (valid for 24 hours)
	userClaims := &models.JWTClaims{
		UserID:   "user123",
		Username: "testuser",
		Roles:    []string{"user"},
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(24 * time.Hour)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			Subject:   "user123",
		},
	}
	userToken := jwt.NewWithClaims(jwt.SigningMethodHS256, userClaims)
	userTokenString, err := userToken.SignedString([]byte(secret))
	if err != nil {
		fmt.Printf("Error generating user token: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("1. REGULAR USER TOKEN (valid 24h):")
	fmt.Println("   User ID: user123")
	fmt.Println("   Username: testuser")
	fmt.Println("   Roles: [user]")
	fmt.Println("   Token:")
	fmt.Println(userTokenString)
	fmt.Println()

	// Admin token (valid for 24 hours)
	adminClaims := &models.JWTClaims{
		UserID:   "admin456",
		Username: "admin",
		Roles:    []string{"user", "admin"},
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(24 * time.Hour)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			Subject:   "admin456",
		},
	}
	adminToken := jwt.NewWithClaims(jwt.SigningMethodHS256, adminClaims)
	adminTokenString, err := adminToken.SignedString([]byte(secret))
	if err != nil {
		fmt.Printf("Error generating admin token: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("2. ADMIN TOKEN (valid 24h):")
	fmt.Println("   User ID: admin456")
	fmt.Println("   Username: admin")
	fmt.Println("   Roles: [user, admin]")
	fmt.Println("   Token:")
	fmt.Println(adminTokenString)
	fmt.Println()

	// Expired token
	expiredClaims := &models.JWTClaims{
		UserID:   "user789",
		Username: "expireduser",
		Roles:    []string{"user"},
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(-1 * time.Hour)),
			IssuedAt:  jwt.NewNumericDate(time.Now().Add(-2 * time.Hour)),
			Subject:   "user789",
		},
	}
	expiredToken := jwt.NewWithClaims(jwt.SigningMethodHS256, expiredClaims)
	expiredTokenString, err := expiredToken.SignedString([]byte(secret))
	if err != nil {
		fmt.Printf("Error generating expired token: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("3. EXPIRED TOKEN (expired 1h ago):")
	fmt.Println("   User ID: user789")
	fmt.Println("   Username: expireduser")
	fmt.Println("   Roles: [user]")
	fmt.Println("   Token:")
	fmt.Println(expiredTokenString)
	fmt.Println()

	// Short-lived token (5 minutes)
	shortClaims := &models.JWTClaims{
		UserID:   "user999",
		Username: "shortuser",
		Roles:    []string{"user"},
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(5 * time.Minute)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			Subject:   "user999",
		},
	}
	shortToken := jwt.NewWithClaims(jwt.SigningMethodHS256, shortClaims)
	shortTokenString, err := shortToken.SignedString([]byte(secret))
	if err != nil {
		fmt.Printf("Error generating short-lived token: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("4. SHORT-LIVED TOKEN (valid 5min):")
	fmt.Println("   User ID: user999")
	fmt.Println("   Username: shortuser")
	fmt.Println("   Roles: [user]")
	fmt.Println("   Token:")
	fmt.Println(shortTokenString)
	fmt.Println()

	fmt.Println("=== Usage Examples ===")
	fmt.Println()
	fmt.Println("Test protected endpoint with regular user:")
	fmt.Printf("curl -H \"Authorization: Bearer %s\" http://localhost:8000/api/v1/test\n\n", userTokenString)

	fmt.Println("Test admin endpoint with admin user:")
	fmt.Printf("curl -H \"Authorization: Bearer %s\" http://localhost:8000/admin/test\n\n", adminTokenString)

	fmt.Println("Test expired token (should return 401):")
	fmt.Printf("curl -H \"Authorization: Bearer %s\" http://localhost:8000/api/v1/test\n\n", expiredTokenString)

	fmt.Println("Test admin endpoint with regular user (should return 403):")
	fmt.Printf("curl -H \"Authorization: Bearer %s\" http://localhost:8000/admin/test\n\n", userTokenString)
}
