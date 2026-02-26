# API Gateway

Go-based API Gateway using Gin framework for WorkflowAI platform.

## Features

- ✅ RESTful API routing
- ✅ CORS middleware
- ✅ Health check endpoint
- ⏳ JWT authentication (Day 3)
- ⏳ Rate limiting with Redis (Day 3)
- ⏳ Request proxy to downstream services (Day 4)

## Quick Start

### Prerequisites

- Go 1.22+
- Redis (optional for development)

### Installation

```bash
# Install dependencies
go mod download

# Copy environment configuration
cp .env.example .env

# Run the server
go run main.go
```

### Testing

```bash
# Health check
curl http://localhost:8000/health

# Root endpoint
curl http://localhost:8000/
```

### Build

```bash
# Build binary
go build -o gateway

# Run binary
./gateway
```

## Project Structure

```
api-gateway/
├── main.go              # Entry point with Gin setup
├── go.mod               # Go module dependencies
├── .env.example         # Environment configuration template
├── config/              # Configuration management (Day 2)
├── middleware/          # JWT auth, rate limiting, CORS (Day 3)
├── handlers/            # HTTP request handlers (Day 4)
├── models/              # Data models (Day 3)
└── utils/               # Helper functions (Day 3)
```

## Environment Variables

See `.env.example` for all available configuration options.

## API Endpoints

### Public Routes

- `GET /` - API information
- `GET /health` - Health check

### Protected Routes (Day 3+)

- `POST /auth/login` - User authentication
- `POST /auth/refresh` - Refresh JWT token

### Proxy Routes (Day 4+)

- `/api/agents/*` - Agent orchestration service
- `/api/index/*` - Indexing service
- `/api/models/*` - Model service
- `/api/metrics/*` - Metrics service

## Development Timeline

- **Day 1**: ✅ Basic Gin setup with health check
- **Day 2**: Docker integration, PostgreSQL connection
- **Day 3**: JWT authentication + rate limiting
- **Day 4**: Service discovery and request proxying
- **Day 5**: Integration testing

## Performance

Target: 40,000 RPS @ P95 < 15ms

See `docs/tech-stack.md` for performance benchmarks and rationale.
