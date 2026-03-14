# Week 8 DORA Metrics + Frontend Integration Design

## Goal
Deliver Week 8 by adding a DORA metrics API and a frontend dashboard that displays the four core DORA metrics with simple trends.

## Architecture
- **Metrics Service (FastAPI)**: Provide a `/metrics/dora` endpoint that returns aggregate DORA metrics and a time-series trend.
- **Data Source**: Use in-memory/stub data initially (with a clear model) and allow future integration with Git/CI events.
- **Frontend Dashboard (React)**: Display metric cards and a simple trend chart; call the metrics API with time window parameters.

## Data Flow & API Shape
Frontend requests:
```
GET /metrics/dora?from=...&to=...&interval=...
```

Backend response shape:
```
{
  "deployment_frequency": 1.2,
  "lead_time": 18.4,
  "change_failure_rate": 0.12,
  "mttr": 3.6,
  "trend": [
    {"timestamp": "2026-03-01", "deployment_frequency": 1.1, "lead_time": 20.0, "change_failure_rate": 0.1, "mttr": 4.0}
  ]
}
```

## Error Handling
- Validate time window parameters; return 400 for invalid ranges.
- Return empty trend arrays for no data; metrics default to zero.
- Frontend handles API errors with empty-state + non-blocking messaging.

## Testing
- Backend: API and schema tests for `/metrics/dora`.
- Frontend: render tests for dashboard cards and empty-state behavior.
