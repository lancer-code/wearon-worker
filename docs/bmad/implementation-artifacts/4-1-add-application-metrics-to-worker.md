# Story 4.1: Add Application Metrics to Worker

Status: review

## Story

As a **platform operator**,
I want **the worker to expose Prometheus metrics for FastAPI requests and Celery tasks**,
So that **Prometheus can scrape and store performance data**.

## Existing Infrastructure (Already Implemented)

- `size_rec/app.py` — FastAPI app with `/health` and `/estimate-body` endpoints
- `requirements.txt` — Current dependencies
- `worker/celery_app.py` — Celery configuration

## Acceptance Criteria

1. **Given** the FastAPI application,
   **When** `prometheus-fastapi-instrumentator` middleware is added,
   **Then** a `/metrics` endpoint is exposed with HTTP request metrics (count, latency, status codes).

2. **Given** the worker's `requirements.txt`,
   **When** `prometheus-fastapi-instrumentator` is added,
   **Then** the dependency is installed and the middleware is initialized in `size_rec/app.py`.

3. **Given** the `/metrics` endpoint,
   **When** Prometheus scrapes it,
   **Then** metrics are returned in Prometheus exposition format.

## Tasks / Subtasks

- [x] Task 1: Add Prometheus instrumentation to FastAPI
  - [x] 1.1 Add `prometheus-fastapi-instrumentator>=7.0.0` to `requirements.txt`
  - [x] 1.2 Add `Instrumentator().instrument(app).expose(app)` to `size_rec/app.py`
  - [x] 1.3 `/metrics` endpoint auto-exposed by instrumentator

- [x] Task 2: Validation
  - [x] 2.1 Instrumentator middleware configured on app (runtime test requires running worker)
  - [x] 2.2 `/metrics` endpoint exposed via `.expose(app)` call
  - [x] 2.3 All 15 existing tests pass with no regressions

## Dev Notes

### Integration Pattern

```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()
Instrumentator().instrument(app).expose(app)
```

### Important Notes

- The `/metrics` endpoint should NOT be exposed through Nginx to the internet. It's only scraped by Prometheus on the internal Docker network.
- No custom Celery metrics in this story — celery-exporter (Story 4.2) handles Celery metrics externally.

### Architecture References

- ADR-4: Grafana + Prometheus + Loki Monitoring Stack
- NFR-4.3: Metrics collection — Prometheus scraping Celery + FastAPI

## Dev Agent Record

### Implementation Notes

- Added `prometheus-fastapi-instrumentator>=7.0.0` to requirements.txt.
- Added two lines to `size_rec/app.py`: import and `Instrumentator().instrument(app).expose(app)` after FastAPI instantiation.
- This auto-exposes a `/metrics` endpoint with HTTP request count, latency histograms, and status code metrics in Prometheus exposition format.
- The `/metrics` endpoint is internal-only (not routed through Nginx) — scraped by Prometheus on Docker network.
- No custom Celery metrics — celery-exporter (Story 4.2) handles those externally.

### Debug Log

No issues encountered.

## File List

- `requirements.txt` — **Modified** — Added `prometheus-fastapi-instrumentator>=7.0.0`
- `size_rec/app.py` — **Modified** — Added Prometheus instrumentator import and initialization

## Change Log

- 2026-02-15: Added Prometheus FastAPI instrumentation exposing `/metrics` endpoint for HTTP request metrics.
