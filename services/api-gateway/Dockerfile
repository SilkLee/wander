# Build stage
FROM golang:1.22-alpine AS builder

WORKDIR /build

# Install dependencies
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY . .

# Build binary (CGO_ENABLED=0 for static binary)
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -ldflags="-w -s" -o gateway .

# Runtime stage
FROM scratch

# Copy SSL certificates (needed for HTTPS requests)
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

# Copy binary
COPY --from=builder /build/gateway /gateway

# Expose port
EXPOSE 8000

# Run
ENTRYPOINT ["/gateway"]

# Final image size: ~25MB (vs Python's 180MB)
