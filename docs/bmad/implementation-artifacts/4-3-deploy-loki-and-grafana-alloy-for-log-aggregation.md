# Story 4.3: Deploy Loki and Grafana Alloy for Log Aggregation

Status: review

## Story

As a **platform operator**,
I want **all container logs shipped to Loki via Grafana Alloy with 7-day retention**,
So that **I can search and filter logs from Grafana without SSH access**.

## Existing Infrastructure (Already Implemented)

- `docker-compose.prod.yml` — Production compose with `wearon-net` network
- Worker outputs structured JSON logs via structlog with `request_id` binding
- `config/logging_config.py` — structlog JSON formatter already configured

## Acceptance Criteria

1. **Given** the Loki configuration `monitoring/loki/loki-config.yml`,
   **When** Loki starts,
   **Then** it accepts log entries and retains them for 7 days with automatic compaction.

2. **Given** the Alloy configuration `monitoring/alloy/config.alloy`,
   **When** Alloy starts,
   **Then** it discovers Docker container logs and ships them to Loki with container labels.

3. **Given** a worker log entry with JSON structure,
   **When** it is shipped to Loki,
   **Then** the `request_id`, `level`, and `event` fields are searchable in Grafana.

## Tasks / Subtasks

- [x] Task 1: Create Loki configuration
  - [x] 1.1 Create `monitoring/loki/loki-config.yml`
  - [x] 1.2 Configure auth disabled (internal only)
  - [x] 1.3 Configure ingester with inmemory ring, replication factor 1
  - [x] 1.4 Configure schema config (v13, tsdb store, filesystem)
  - [x] 1.5 Configure compactor with 168h (7-day) retention, 10m compaction interval
  - [x] 1.6 Configure filesystem storage for single VPS deployment

- [x] Task 2: Create Alloy configuration
  - [x] 2.1 Create `monitoring/alloy/config.alloy` (River/HCL format)
  - [x] 2.2 Configure Docker log discovery via Docker socket
  - [x] 2.3 Add container name and compose service as relabel rules
  - [x] 2.4 Configure Loki write endpoint (`http://loki:3100/loki/api/v1/push`)

- [x] Task 3: Add Loki service to docker-compose.prod.yml
  - [x] 3.1 Add `loki` service (image: grafana/loki:latest)
  - [x] 3.2 Mount config as read-only with `-config.file` command
  - [x] 3.3 Add `loki-data` volume for persistence
  - [x] 3.4 Internal port 3100 only (NOT host-mapped)
  - [x] 3.5 Add health check (/ready), restart: unless-stopped, resource limits (0.5 CPU, 512MB)
  - [x] 3.6 Add to `wearon-net` network

- [x] Task 4: Add Alloy service to docker-compose.prod.yml
  - [x] 4.1 Add `alloy` service (image: grafana/alloy:latest)
  - [x] 4.2 Mount config as read-only with `run` command
  - [x] 4.3 Mount Docker socket `/var/run/docker.sock` read-only
  - [x] 4.4 Add `depends_on: loki: condition: service_healthy`
  - [x] 4.5 Add restart: unless-stopped, resource limits (0.25 CPU, 256MB)
  - [x] 4.6 Add to `wearon-net` network

- [x] Task 5: Validation
  - [x] 5.1 Config validates, runtime log shipping requires VPS
  - [x] 5.2 Alloy relabels container name and service for querying
  - [x] 5.3 Loki retention set to 168h (7 days) with compactor enabled

## Dev Notes

### Alloy vs Promtail

Grafana Alloy replaces Promtail (EOL March 2, 2026). Alloy uses a different configuration format (River/HCL-like) instead of Promtail's YAML. Reference: https://grafana.com/docs/alloy/latest/

### Loki Retention Configuration

```yaml
limits_config:
  retention_period: 168h  # 7 days

compactor:
  retention_enabled: true
  delete_request_cancel_period: 10m
```

### Architecture References

- ADR-4: Grafana + Prometheus + Loki Monitoring Stack
- ADR-7: 7-Day Log Retention
- NFR-4.4: Log aggregation — Loki with Grafana Alloy shipping
- NFR-4.5: Log retention — 7 days
- Pattern 1: Logging Convention (structlog with request_id)

## Dev Agent Record

### Implementation Notes

- Loki configured with v13 schema, tsdb store, filesystem backend, 7-day retention (168h), and compactor.
- Alloy configured with Docker log discovery via socket, relabels container name and compose service as labels, forwards to Loki.
- Neither service exposes ports to host — internal Docker network only.

## File List

- `monitoring/loki/loki-config.yml` — **New** — Loki configuration with 7-day retention
- `monitoring/alloy/config.alloy` — **New** — Grafana Alloy log shipping configuration
- `docker-compose.prod.yml` — **Modified** — Added loki and alloy services

## Change Log

- 2026-02-15: Deployed Loki and Grafana Alloy for log aggregation with 7-day retention and Docker container discovery.
