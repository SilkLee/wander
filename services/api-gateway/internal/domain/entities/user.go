package entities

import (
	"fmt"
	"regexp"
	"strings"
	"time"

	"github.com/google/uuid"
)

// User represents a user entity in the domain model.
// It encapsulates user data and implements business rules for user-related operations.
// User entities are immutable after creation (no setters).
type User struct {
	// ID is a unique identifier (UUID) for the user.
	ID string

	// Email is the user's email address. Must be unique and in valid format.
	Email string

	// Username is the user's login name. Must be alphanumeric with underscores, 3-32 chars.
	Username string

	// Role is the user's role: either "admin" or "user".
	Role string

	// CreatedAt is the timestamp when the user was created.
	CreatedAt time.Time
}

// NewUser creates a new User entity with validation.
// It generates a UUID and timestamp automatically.
// Returns an error if any validation rule is violated.
//
// Validation rules:
// - Email: required, must match valid email format
// - Username: required, 3-32 characters, alphanumeric and underscore only
// - Role: required, must be "admin" or "user"
func NewUser(email, username, role string) (*User, error) {
	// Trim whitespace
	email = strings.TrimSpace(email)
	username = strings.TrimSpace(username)
	role = strings.TrimSpace(role)

	// Validate email
	if email == "" {
		return nil, fmt.Errorf("email is required")
	}
	if !isValidEmail(email) {
		return nil, fmt.Errorf("email format is invalid: %s", email)
	}

	// Validate username
	if username == "" {
		return nil, fmt.Errorf("username is required")
	}
	if len(username) < 3 || len(username) > 32 {
		return nil, fmt.Errorf("username must be between 3 and 32 characters, got %d", len(username))
	}
	if !isValidUsername(username) {
		return nil, fmt.Errorf("username must contain only alphanumeric characters and underscores: %s", username)
	}

	// Validate role
	if role == "" {
		return nil, fmt.Errorf("role is required")
	}
	if role != "admin" && role != "user" {
		return nil, fmt.Errorf("role must be 'admin' or 'user', got %q", role)
	}

	user := &User{
		ID:        uuid.New().String(),
		Email:     email,
		Username:  username,
		Role:      role,
		CreatedAt: time.Now().UTC(),
	}

	return user, nil
}

// IsAdmin is a business rule that checks if the user has admin role.
// Returns true if the user is an admin, false otherwise.
func (u *User) IsAdmin() bool {
	return u.Role == "admin"
}

// CanAccessResource is a business rule that determines if the user can access a specific resource.
// Admins can access all resources. Regular users can only access their own resources (resourceOwnerID).
// Returns true if access is granted, false otherwise.
func (u *User) CanAccessResource(resourceOwnerID string) bool {
	// Admin can access any resource
	if u.IsAdmin() {
		return true
	}
	// Regular user can only access resources they own (matching their ID)
	return u.ID == resourceOwnerID
}

// Validate validates the current state of the User entity.
// It ensures all invariants are maintained.
// Returns an error if any validation rule is violated.
func (u *User) Validate() error {
	if u == nil {
		return fmt.Errorf("user entity is nil")
	}

	if u.ID == "" {
		return fmt.Errorf("user ID cannot be empty")
	}

	if u.Email == "" {
		return fmt.Errorf("user email cannot be empty")
	}
	if !isValidEmail(u.Email) {
		return fmt.Errorf("user email format is invalid: %s", u.Email)
	}

	if u.Username == "" {
		return fmt.Errorf("user username cannot be empty")
	}
	if len(u.Username) < 3 || len(u.Username) > 32 {
		return fmt.Errorf("user username must be between 3 and 32 characters, got %d", len(u.Username))
	}
	if !isValidUsername(u.Username) {
		return fmt.Errorf("user username must contain only alphanumeric characters and underscores: %s", u.Username)
	}

	if u.Role != "admin" && u.Role != "user" {
		return fmt.Errorf("user role must be 'admin' or 'user', got %q", u.Role)
	}

	if u.CreatedAt.IsZero() {
		return fmt.Errorf("user CreatedAt timestamp cannot be zero")
	}

	return nil
}

// isValidEmail checks if an email string matches a basic valid email format.
// It uses a simple regex pattern for validation.
// This is a basic check; production systems should use more robust validation or RFC 5322.
func isValidEmail(email string) bool {
	// Basic email regex: simple pattern for common email formats
	// Pattern: word.chars@word.chars.word
	pattern := `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`
	matched, err := regexp.MatchString(pattern, email)
	return err == nil && matched
}

// isValidUsername checks if a username contains only alphanumeric characters and underscores.
func isValidUsername(username string) bool {
	// Regex: only alphanumeric (a-z, A-Z, 0-9) and underscore (_)
	pattern := `^[a-zA-Z0-9_]+$`
	matched, err := regexp.MatchString(pattern, username)
	return err == nil && matched
}
