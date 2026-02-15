# Story 2.1: Create Production Docker Compose Configuration

Status: review

## Story

As a **platform operator**,
I want **a docker-compose.prod.yml that orchestrates the worker and Redis with health checks**,
So that **production deployment is a single command and services start in the correct order**.

## Existing Infrastructure (Already Implemented)

The following is already in place and should be leveraged:

- `docker-compose.yml` — Dev compose with Redis 7-alpine + worker, health checks, `depends_on: service_healthy`
- `Dockerfile` — Multi-stage production build (builder + runtime), already production-ready
- `.env.example` — All required env vars documented
- `Makefile` — Docker commands (dev, up, down, logs, test, build)
- CI/CD (`.github/workflows/ci-cd.yml`) — Builds image, pushes to GHCR, deploys via SSH with raw `docker run`
- Health check endpoint (`GET /health`) — Returns MediaPipe + Redis status

## Acceptance Criteria

1. **Given** the production Docker Compose file `docker-compose.prod.yml`,
   **When** `docker compose -f docker-compose.prod.yml up -d` is run on a VPS with Docker Compose installed,
   **Then** the worker and Redis containers start with the worker depending on Redis being healthy.

2. **Given** the Redis service in docker-compose.prod.yml,
   **When** the container starts,
   **Then** Redis runs with password authentication from `.env` and a health check (`redis-cli ping`).

3. **Given** the worker service in docker-compose.prod.yml,
   **When** Redis is healthy,
   **Then** the worker starts with `restart: unless-stopped`, loads env vars from `.env` file, and does NOT expose port 8000 to the host (internal Docker network only, Nginx will handle external access in Story 3.1).

4. **Given** the Docker network configuration,
   **When** services are running,
   **Then** all services communicate over a dedicated Docker bridge network (`wearon-net`).

5. **Given** the worker container,
   **When** it is running under load,
   **Then** it is limited by configured CPU and memory resource limits.

## Tasks / Subtasks

- [x] Task 1: Create `docker-compose.prod.yml`
  - [x] 1.1 Define `wearon-net` bridge network
  - [x] 1.2 Add Redis service (image: redis:7-alpine, password from .env, health check, restart policy, resource limits)
  - [x] 1.3 Add worker service (image: ghcr.io/lancer-code/wearon-worker:latest, depends_on Redis healthy, env_file, restart policy, resource limits, NO host port mapping)
  - [x] 1.4 Add worker health check (python urllib — curl not available in slim image)
  - [x] 1.5 Add redis-data volume for persistence

- [x] Task 2: Update `.env.example` with production variables
  - [x] 2.1 Add `REDIS_PASSWORD` variable (already existed)
  - [x] 2.2 Add `DOMAIN` variable (for future Nginx/SSL use)

- [x] Task 3: Update `Makefile` with production commands
  - [x] 3.1 Add `prod-up` target: `docker compose -f docker-compose.prod.yml up -d`
  - [x] 3.2 Add `prod-down` target: `docker compose -f docker-compose.prod.yml down`
  - [x] 3.3 Add `prod-logs` target: `docker compose -f docker-compose.prod.yml logs -f`
  - [x] 3.4 Add `prod-pull` target: `docker compose -f docker-compose.prod.yml pull`

- [x] Task 4: Validation
  - [x] 4.1 Verify `docker compose -f docker-compose.prod.yml config` validates successfully
  - [x] 4.2 Verify worker health check configured (python urllib on localhost:8000/health)
  - [x] 4.3 Verify port 8000 is NOT accessible from host (no ports mapping in worker service)

## Dev Notes

### Key Differences from docker-compose.yml (dev)

| Aspect | Dev (`docker-compose.yml`) | Prod (`docker-compose.prod.yml`) |
|--------|---------------------------|----------------------------------|
| Worker image | `build: .` (local build) | `ghcr.io/lancer-code/wearon-worker:latest` |
| Worker port | `8000:8000` (host mapped) | Not mapped (Nginx in Story 3.1) |
| Network | Default | Explicit `wearon-net` bridge |
| Restart | None | `unless-stopped` |
| Resources | None | CPU/memory limits |
| Health check | None on worker | curl health endpoint |

### Architecture References

- ADR-2: Production Docker Compose Orchestration
- ADR-3: Nginx as Security Boundary (port 8000 not exposed — Nginx handles in Story 3.1)
- Pattern 6: Docker Compose Service Dependencies
- Pattern 7: Environment Variable Management

### Important Notes

- Worker port 8000 is intentionally NOT mapped to host. Nginx (Story 3.1) will proxy to it via Docker network.
- The `wearon-net` network will be shared with Nginx, monitoring containers added in later stories.
- Redis password MUST come from `.env` file, never hardcoded.
- Resource limits should be conservative initially (e.g., worker: 2 CPU, 2GB RAM; Redis: 0.5 CPU, 512MB RAM) and adjusted based on monitoring data (Epic 3).

## Dev Agent Record

### Implementation Notes

- Created `docker-compose.prod.yml` with all required services, networking, health checks, restart policies, and resource limits.
- Worker health check uses `python urllib.request.urlopen()` instead of `curl` because the production image (`python:3.12-slim`) does not include `curl`. This avoids adding unnecessary dependencies to the Dockerfile.
- `REDIS_PASSWORD` was already present in `.env.example`; only `DOMAIN` needed to be added.
- Resource limits set to conservative values per Dev Notes: worker (2 CPU, 2GB RAM), Redis (0.5 CPU, 512MB RAM).
- Worker port 8000 is intentionally NOT mapped to the host — accessible only within `wearon-net` Docker network for Nginx proxy (Story 3.1).
- All 15 existing tests pass with no regressions.

### Debug Log

No issues encountered during implementation.

## File List

- `docker-compose.prod.yml` — **New** — Production Docker Compose configuration
- `.env.example` — **Modified** — Added `DOMAIN` variable
- `Makefile` — **Modified** — Added `prod-up`, `prod-down`, `prod-logs`, `prod-pull` targets

## Change Log

- 2026-02-15: Created production Docker Compose configuration with Redis + worker services, health checks, restart policies, resource limits, `wearon-net` bridge network, and production Makefile targets.
