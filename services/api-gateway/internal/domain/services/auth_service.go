package services

import (
	"fmt"

	"workflow-ai/gateway/internal/domain/entities"
)

// AuthService is a domain service that handles authentication-related business logic.
// It operates at the domain level, not the application or infrastructure level.
// Domain services are used when business logic spans multiple entities or requires
// complex orchestration of domain rules.
type AuthService struct {
	// Placeholder for future dependencies (e.g., token verifier, identity provider)
	// Currently kept empty to maintain pure domain logic separation
}

// NewAuthService creates a new instance of AuthService.
// It initializes an empty service for domain-level authorization operations.
func NewAuthService() *AuthService {
	return &AuthService{}
}

// VerifyToken verifies an authentication token and returns the associated User.
// This is a placeholder for the actual token verification logic, which would
// typically involve parsing JWT tokens or verifying against an identity provider.
// This method is kept simple to demonstrate domain service patterns.
//
// Parameters:
//   - token: the authentication token to verify
//
// Returns:
//   - A pointer to the verified User entity, or nil if verification fails
//   - An error if verification is not implemented or token is invalid
//
// Note: Actual implementation would parse JWT tokens, verify signatures, and check expiration.
func (as *AuthService) VerifyToken(token string) (*entities.User, error) {
	if token == "" {
		return nil, fmt.Errorf("token cannot be empty")
	}

	// TODO: Implement actual token verification logic
	// This placeholder demonstrates the separation of concerns:
	// - Domain layer defines WHAT should happen (verify token -> get user)
	// - Infrastructure layer implements HOW it happens (JWT parsing, crypto verification)
	// - This allows domain logic to remain independent of authentication mechanism changes

	return nil, fmt.Errorf("VerifyToken not implemented yet")
}

// AuthorizeAccess checks if a user can access a specific resource.
// This method implements a domain-level authorization rule using the User entity's
// CanAccessResource method. It delegates the actual business logic to the entity.
//
// Parameters:
//   - user: the user attempting to access the resource (must not be nil)
//   - resourceID: the ID of the resource being accessed (typically the owner's ID)
//
// Returns:
//   - An error if access is denied or if user is nil
//   - nil if access is granted
//
// Business Rules:
//   - Admins can access any resource
//   - Regular users can only access resources they own (resourceID == user.ID)
func (as *AuthService) AuthorizeAccess(user *entities.User, resourceID string) error {
	if user == nil {
		return fmt.Errorf("user cannot be nil for authorization")
	}

	// Validate the user entity state before authorization
	if err := user.Validate(); err != nil {
		return fmt.Errorf("invalid user entity: %w", err)
	}

	// Delegate authorization decision to the User entity's business rule
	if !user.CanAccessResource(resourceID) {
		return fmt.Errorf("access denied: user %s cannot access resource %s", user.ID, resourceID)
	}

	return nil
}
