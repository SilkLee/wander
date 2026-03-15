# Week 8 Vite Preview Design

## Goal
Run the DORA dashboard locally with a Vite dev server so the UI can be viewed in a browser.

## Architecture
- Add Vite to the existing frontend package for fast local development.
- Provide `index.html` and `src/main.tsx` to mount `App`.
- Add a Vite proxy for `/api` to the metrics service.
- Run metrics API locally via FastAPI on a known port.

## Data Flow
Browser → Vite dev server → `/api/metrics/dora` proxy → Metrics service.

## Error Handling
- If metrics service is down, the UI renders the existing empty state.
- Vite console surfaces startup errors.

## Testing
- Frontend tests: `npm test -- DoraDashboard.test.tsx`.
- Metrics API tests: `pytest services/metrics/tests/test_dora_endpoint.py -v`.
