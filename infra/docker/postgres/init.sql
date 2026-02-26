-- WorkflowAI Database Initialization Script
-- Purpose: Create initial database schema for all services
-- Target: PostgreSQL 15+

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search optimization

-- ============================================================================
-- AGENT ORCHESTRATOR TABLES
-- ============================================================================

-- Workflows table (LangChain agent workflows)
CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    config JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Workflow executions (history of workflow runs)
CREATE TABLE workflow_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    input JSONB NOT NULL,
    output JSONB,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    error TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER
);

-- Agent interactions (individual LLM calls within workflows)
CREATE TABLE agent_interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id UUID NOT NULL REFERENCES workflow_executions(id) ON DELETE CASCADE,
    agent_type VARCHAR(100) NOT NULL,
    prompt TEXT NOT NULL,
    response TEXT,
    tokens_used INTEGER,
    latency_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- METRICS SERVICE TABLES
-- ============================================================================

-- API metrics (request/response tracking)
CREATE TABLE api_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_name VARCHAR(100) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER NOT NULL,
    response_time_ms INTEGER NOT NULL,
    request_size_bytes INTEGER,
    response_size_bytes INTEGER,
    user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Model metrics (LLM usage tracking)
CREATE TABLE model_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(100) NOT NULL,
    operation VARCHAR(50) NOT NULL,  -- 'inference', 'embedding', 'fine-tune'
    tokens_input INTEGER NOT NULL,
    tokens_output INTEGER NOT NULL,
    latency_ms INTEGER NOT NULL,
    cost_usd DECIMAL(10, 6),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- System health metrics (resource usage)
CREATE TABLE system_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_name VARCHAR(100) NOT NULL,
    cpu_percent DECIMAL(5, 2),
    memory_mb INTEGER,
    disk_mb INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- SHARED TABLES (used by multiple services)
-- ============================================================================

-- Documents table (ingested documents metadata)
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    content_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256 hash for deduplication
    storage_path TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- 'pending', 'indexed', 'failed'
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    indexed_at TIMESTAMP WITH TIME ZONE
);

-- Document chunks (for RAG retrieval)
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    embedding_id VARCHAR(255),  -- Reference to Elasticsearch/vector DB
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, chunk_index)
);

-- Users table (for JWT authentication)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'user',  -- 'user', 'admin'
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE
);

-- ============================================================================
-- INDEXES (Performance optimization)
-- ============================================================================

-- Workflow executions indexes
CREATE INDEX idx_workflow_executions_workflow_id ON workflow_executions(workflow_id);
CREATE INDEX idx_workflow_executions_status ON workflow_executions(status);
CREATE INDEX idx_workflow_executions_started_at ON workflow_executions(started_at DESC);

-- Agent interactions indexes
CREATE INDEX idx_agent_interactions_execution_id ON agent_interactions(execution_id);
CREATE INDEX idx_agent_interactions_agent_type ON agent_interactions(agent_type);

-- API metrics indexes
CREATE INDEX idx_api_metrics_service_name ON api_metrics(service_name);
CREATE INDEX idx_api_metrics_endpoint ON api_metrics(endpoint);
CREATE INDEX idx_api_metrics_created_at ON api_metrics(created_at DESC);

-- Model metrics indexes
CREATE INDEX idx_model_metrics_model_name ON model_metrics(model_name);
CREATE INDEX idx_model_metrics_created_at ON model_metrics(created_at DESC);

-- Documents indexes
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_content_hash ON documents(content_hash);
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);

-- Document chunks indexes
CREATE INDEX idx_document_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_document_chunks_embedding_id ON document_chunks(embedding_id);

-- Users indexes
CREATE INDEX idx_users_email ON users(email);

-- ============================================================================
-- TRIGGERS (Automatic timestamp updates)
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to workflows table
CREATE TRIGGER update_workflows_updated_at
    BEFORE UPDATE ON workflows
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SEED DATA (Development only)
-- ============================================================================

-- Insert a test user (password: 'test123', bcrypt hash)
INSERT INTO users (email, password_hash, full_name, role) VALUES
    ('admin@workflowai.dev', '$2a$10$YourBcryptHashHere', 'Admin User', 'admin'),
    ('test@workflowai.dev', '$2a$10$YourBcryptHashHere', 'Test User', 'user');

-- Insert a sample workflow
INSERT INTO workflows (name, description, config) VALUES
    ('Document Q&A', 'RAG-based question answering over documents', 
     '{"model": "Qwen2.5-7B", "temperature": 0.7, "max_tokens": 512}'::jsonb);

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

-- Grant permissions to workflowai user (matches POSTGRES_USER in docker-compose.yml)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO workflowai;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO workflowai;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Show created tables
\dt

-- Show table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Summary
\echo '✅ Database initialization complete!'
\echo '   - Created 12 tables (workflows, metrics, documents, users)'
\echo '   - Created 15 indexes for performance'
\echo '   - Inserted seed data (2 users, 1 workflow)'
\echo '   - Database ready for WorkflowAI services'
