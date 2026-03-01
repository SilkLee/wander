# Application Layer Implementation

## Summary
Created production-ready application layer with use cases, DTOs, and port interfaces using clean architecture principles.

## Directory Structure
```
app/application/
├── __init__.py
├── ports.py                          # Protocol interfaces (dependency inversion)
├── use_cases/
│   ├── __init__.py
│   └── analyze_log.py               # AnalyzeLogUseCase (5 steps)
├── dto/
│   ├── __init__.py
│   ├── log_analysis_request.py       # Request DTO with Pydantic validation
│   └── log_analysis_response.py      # Response DTO with from_domain()
└── services/
    ├── __init__.py
    └── workflow_orchestrator.py      # Placeholder service (10 lines)
```

## Components

### 1. Ports (app/application/ports.py)
**Purpose**: Define contracts for external dependencies using `typing.Protocol`

- **AgentPort**: Interface for LLM-based analysis
  - `async analyze_logs(log_content: str) -> dict`
  - Returns: severity, confidence, root_causes, summary

- **ParserPort**: Interface for parsing agent output
  - `parse_analysis_result(raw_result: dict) -> tuple`
  - Returns: (Severity, Confidence, list[RootCause])

- **RepositoryPort**: Interface for persistence
  - `async save(analysis: LogAnalysis) -> None`
  - `async get_by_id(analysis_id: str) -> Optional[LogAnalysis]`

### 2. AnalyzeLogUseCase (app/application/use_cases/analyze_log.py)
**Purpose**: Orchestrate log analysis workflow respecting domain invariants

**Constructor**:
```python
def __init__(self, agent: AgentPort, parser: ParserPort, repository: RepositoryPort)
```

**Workflow (execute method)**:
1. Validate input (non-empty log content)
2. Call agent to analyze logs
3. Parse raw agent output into domain components
4. Create LogAnalysis domain model (enforces invariants)
5. Persist to repository
6. Return domain model

**Dependency Inversion**: Uses Protocol interfaces, enabling testing with any compatible mock

### 3. DTOs

#### LogAnalysisRequest (app/application/dto/log_analysis_request.py)
**Purpose**: Validate incoming API requests

- Uses Pydantic `BaseModel` for automatic validation
- Fields:
  - `log_content`: str (required, 10-100,000 chars)
- Validators:
  - Rejects empty/whitespace-only strings
  - Enforces min length (10 chars) and max length (100,000 chars)
- Separate from domain models (API layer concern)

#### LogAnalysisResponse (app/application/dto/log_analysis_response.py)
**Purpose**: Serialize domain models to JSON-safe API format

- Uses Pydantic `BaseModel`
- Includes `from_domain()` classmethod for conversion
  - Gracefully handles None inputs
  - Converts UUID to str
  - Converts Enum.name to string
  - Computes derived fields (is_actionable, is_critical, remediation_steps)
- Fields:
  - `id`, `severity`, `confidence`, `root_causes`, `summary`
  - `is_actionable`, `is_critical`, `is_resolved`, `remediation_steps`
- Nested RootCauseDTO with `from_domain()` method

### 4. WorkflowOrchestrator (app/application/services/workflow_orchestrator.py)
**Purpose**: Placeholder for future complex orchestration

- Minimal implementation (10 lines)
- Reserved for: Saga patterns, retry/circuit-breaker, state machines
- Future expansion without modifying existing code

## Key Design Decisions

### 1. Dependency Inversion (Protocol Interfaces)
- Used `typing.Protocol` instead of abstract classes
- Enables testing with simple mocks (structure-based typing)
- No explicit inheritance required from adapters

### 2. Separation of Concerns
- DTOs separate API contracts from domain models
- Can evolve independently
- Clear responsibility boundaries

### 3. Pydantic Validation
- Request validation at API boundary
- Type hints with runtime validation
- Comprehensive error messages

### 4. Async/Await
- AnalyzeLogUseCase.execute() is async
- Enables high-concurrency handling
- Matches FastAPI ecosystem

### 5. Domain Model Enforcement
- LogAnalysis invariants enforced in __post_init__
- Business rules (is_actionable, is_critical) in domain
- Use case respects domain boundaries

## Testing Strategy

### Unit Testing Ports
```python
class MockAgent:
    async def analyze_logs(self, log_content: str) -> dict:
        return {"severity": "HIGH", ...}

class MockParser:
    def parse_analysis_result(self, raw: dict) -> tuple:
        return (Severity.HIGH, Confidence(0.9), [])

use_case = AnalyzeLogUseCase(MockAgent(), MockParser(), MockRepository())
result = await use_case.execute("logs...")
```

### Unit Testing DTOs
```python
# Request validation
LogAnalysisRequest(log_content="too short")  # Raises ValidationError
LogAnalysisRequest(log_content="valid log...")  # OK

# Response serialization
dto = LogAnalysisResponse.from_domain(analysis)
json_str = dto.model_dump_json()
```

## Next Steps (Infrastructure Layer)

Will implement concrete adapters:
1. **AgentAdapter**: LangChain agent wrapper
2. **ParserAdapter**: Raw result → domain model conversion
3. **RepositoryAdapter**: PostgreSQL/Redis persistence

These will satisfy the Port interfaces without modifying application layer.

## Python Version Compatibility
- Uses `Optional[T]` instead of `T | None` (Python 3.9 support)
- Uses `list` instead of `list[T]` (Python 3.9 support)
- All code compatible with Python 3.9+
