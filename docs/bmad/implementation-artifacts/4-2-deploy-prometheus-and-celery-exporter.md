# Story 4.2: Deploy Prometheus and Celery Exporter

Status: review

## Story

As a **platform operator**,
I want **Prometheus collecting metrics from the worker and celery-exporter**,
So that **I can visualize task throughput, error rates, and API latency**.

## Existing Infrastructure (Already Implemented)

- `docker-compose.prod.yml` — Production compose with `wearon-net` network
- Worker `/metrics` endpoint from Story 4.1 (prometheus-fastapi-instrumentator)
- `worker/celery_app.py` — Celery uses Redis as broker

## Acceptance Criteria

1. **Given** the Prometheus configuration `monitoring/prometheus/prometheus.yml`,
   **When** Prometheus starts,
   **Then** it scrapes the worker's `/metrics` endpoint and celery-exporter on port 9808.

2. **Given** the celery-exporter container,
   **When** it connects to Redis,
   **Then** it exports Celery task metrics (task success/failure counts, queue depths, latencies).

3. **Given** Prometheus and celery-exporter in docker-compose.prod.yml,
   **When** the stack starts,
   **Then** both containers are healthy and scraping metrics.

## Tasks / Subtasks

- [x] Task 1: Create Prometheus configuration
  - [x] 1.1 Create `monitoring/prometheus/prometheus.yml` with global scrape interval (15s)
  - [x] 1.2 Add scrape target: `worker:8000/metrics` (FastAPI metrics)
  - [x] 1.3 Add scrape target: `celery-exporter:9808/metrics` (Celery metrics)

- [x] Task 2: Add Prometheus service to docker-compose.prod.yml
  - [x] 2.1 Add `prometheus` service (image: prom/prometheus:latest)
  - [x] 2.2 Mount `monitoring/prometheus/prometheus.yml` as config (read-only)
  - [x] 2.3 Add `prometheus-data` volume for persistence
  - [x] 2.4 Internal port 9090 only (NOT host-mapped)
  - [x] 2.5 Add health check (wget /-/healthy), restart: unless-stopped, resource limits (0.5 CPU, 512MB)
  - [x] 2.6 Add to `wearon-net` network

- [x] Task 3: Add celery-exporter service to docker-compose.prod.yml
  - [x] 3.1 Add `celery-exporter` service (image: danihodovic/celery-exporter:latest)
  - [x] 3.2 Configure CE_BROKER_URL with Redis password
  - [x] 3.3 Internal port 9808 only (NOT host-mapped)
  - [x] 3.4 Add `depends_on: redis: condition: service_healthy`
  - [x] 3.5 Add restart: unless-stopped, resource limits (0.25 CPU, 256MB)
  - [x] 3.6 Add to `wearon-net` network

- [x] Task 4: Validation
  - [x] 4.1 Prometheus scrape config targets worker:8000 and celery-exporter:9808 (runtime test requires VPS)
  - [x] 4.2 Both scrape targets defined in prometheus.yml
  - [x] 4.3 `docker compose -f docker-compose.prod.yml config` validates successfully

## Dev Notes

### Prometheus Scrape Config Example

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'worker'
    static_configs:
      - targets: ['worker:8000']

  - job_name: 'celery'
    static_configs:
      - targets: ['celery-exporter:9808']
```

### celery-exporter Environment

The celery-exporter needs the Redis broker URL. Pass via environment variable:
```yaml
environment:
  - CE_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
```

### Architecture References

- ADR-4: Grafana + Prometheus + Loki Monitoring Stack
- NFR-4.3: Metrics collection — Prometheus scraping Celery + FastAPI
- Pattern 6: Docker Compose Service Dependencies

## Dev Agent Record

### Implementation Notes

- Created `monitoring/prometheus/prometheus.yml` with 15s scrape interval and two targets.
- Added Prometheus service with persistent volume, health check, and internal-only port 9090.
- Added celery-exporter service with Redis broker URL via CE_BROKER_URL env var, depends_on Redis healthy.
- Neither Prometheus nor celery-exporter expose ports to the host — internal Docker network only.
- All 15 existing tests pass with no regressions.

### Debug Log

No issues encountered.

## File List

- `monitoring/prometheus/prometheus.yml` — **New** — Prometheus scrape configuration
- `docker-compose.prod.yml` — **Modified** — Added prometheus and celery-exporter services

## Change Log

- 2026-02-15: Deployed Prometheus and celery-exporter services with scrape targets for worker and Celery metrics.
