# Story 3.1: Create Nginx Reverse Proxy Configuration

Status: done

## Story

As a **platform operator**,
I want **Nginx to reverse-proxy all HTTP traffic to the worker and Grafana**,
So that **only ports 80 and 443 are exposed to the internet and internal services are protected**.

## Existing Infrastructure (Already Implemented)

- `docker-compose.prod.yml` — Production compose with `wearon-net` bridge network (from Story 2.1)
- Worker serves `/health` and `/estimate-body` on port 8000 (internal)
- Grafana will serve on port 3000 (added in Story 4.4)

## Acceptance Criteria

1. **Given** a request to `/health` or `/estimate-body` on ports 80/443,
   **When** Nginx receives the request,
   **Then** it proxies to the worker container on port 8000 over the internal Docker network.

2. **Given** a request to `/grafana/*` on ports 80/443,
   **When** Nginx receives the request,
   **Then** it proxies to the Grafana container on port 3000 over the internal Docker network.

3. **Given** any direct access attempt to ports 8000, 3000, 9090, 6379, or 3100 from the internet,
   **When** the connection is attempted,
   **Then** it is refused because only ports 80/443 are mapped to the host.

4. **Given** the Nginx service in docker-compose.prod.yml,
   **When** all upstream services are healthy,
   **Then** Nginx starts and serves traffic on ports 80 and 443.

## Tasks / Subtasks

- [x] Task 1: Create Nginx configuration files
  - [x] 1.1 Create `nginx/nginx.conf` with worker process, event, and http block settings
  - [x] 1.2 Create `nginx/conf.d/default.conf` with upstream definitions and server block
  - [x] 1.3 Configure `proxy_pass` for `/health` and `/estimate-body` → worker:8000
  - [x] 1.4 Configure `proxy_pass` for `/grafana/` → grafana:3000
  - [x] 1.5 Add standard proxy headers (X-Real-IP, X-Forwarded-For, X-Forwarded-Proto)

- [x] Task 2: Add Nginx service to docker-compose.prod.yml
  - [x] 2.1 Add `nginx` service (image: nginx:stable-alpine)
  - [x] 2.2 Map ports 80:80 and 443:443 to host
  - [x] 2.3 Mount `nginx/nginx.conf` and `nginx/conf.d/` as read-only volumes
  - [x] 2.4 Add `depends_on: worker: condition: service_healthy`
  - [x] 2.5 Add to `wearon-net` network
  - [x] 2.6 Add health check (wget — Alpine has wget, not curl)
  - [x] 2.7 Add `restart: unless-stopped` and resource limits (0.5 CPU, 256M)

- [x] Task 3: Prepare for SSL (Story 3.2)
  - [x] 3.1 Add volume mounts for certbot webroot (`.well-known/acme-challenge/`)
  - [x] 3.2 Add volume mounts for SSL certificates (certbot-certs, certbot-webroot)
  - [x] 3.3 Start with HTTP-only config, SSL added in Story 3.2

- [x] Task 4: Validation
  - [x] 4.1 Nginx proxies `/health` to worker:8000 (config validated, runtime test requires VPS)
  - [x] 4.2 Port 8000 not mapped to host — only ports 80/443 exposed via Nginx
  - [x] 4.3 `docker compose -f docker-compose.prod.yml config` validates successfully

### Review Follow-ups (AI)

- [x] [AI-Review][HIGH] Task 1.2 claims `nginx/conf.d/default.conf` — **Resolved: False positive.** Commit `3476106` created `nginx/conf.d/default.conf`. Story 3.2 (`5ed4a6d`) later moved it to `nginx/templates/default.conf.template`. Story 3.1 was correct at the time.
- [x] [AI-Review][HIGH] Task 3.3 claims HTTP-only but HTTPS present — **Resolved: False positive.** Story 3.1 started HTTP-only as planned. HTTPS was added by Story 3.2. Reviewer compared current state, not commit state.
- [x] [AI-Review][HIGH] Compose validation not reproducible — **Resolved.** `docker compose -f docker-compose.prod.yml config` validates with `.env` file. Env vars are expected runtime requirement.
- [x] [AI-Review][MEDIUM] Task 2.3 mount mismatch (conf.d vs templates) — **Resolved: False positive.** Story 3.1 originally mounted `nginx/conf.d/`. Story 3.2 changed to `nginx/templates/` for envsubst.
- [x] [AI-Review][MEDIUM] File List path outdated — **Resolved.** Updated File List to note supersession by Story 3.2.
- [x] [AI-Review][LOW] "HTTP-only" notes stale — **Resolved.** Notes describe Story 3.1's HTTP-only approach; HTTPS was added by Story 3.2 as planned.

## Dev Notes

### Nginx Routing Table

| Path | Upstream | Auth |
|------|----------|------|
| `/health` | worker:8000 | None |
| `/estimate-body` | worker:8000 | None (rate limited) |
| `/grafana/*` | grafana:3000 | Grafana built-in auth |
| `/.well-known/acme-challenge/` | Local filesystem | None (certbot) |

### Important Notes

- Start with HTTP-only configuration. SSL is added in Story 3.2.
- Grafana upstream may not be available until Story 4.4. Use a fallback 502 or skip the block initially and add it with Grafana.
- Port 8000 is intentionally NOT mapped to host in docker-compose.prod.yml — only Nginx ports 80/443 are host-mapped.

### Architecture References

- ADR-3: Nginx as Security Boundary
- NFR-3.5: Network exposure — only ports 80/443 internet-facing
- Pattern 6: Docker Compose Service Dependencies

## Dev Agent Record

### Implementation Notes

- Created `nginx/nginx.conf` with auto worker processes, standard logging, and include for conf.d.
- Created `nginx/conf.d/default.conf` with upstream blocks for worker (port 8000) and Grafana (port 3000), proxy_pass routes for `/health`, `/estimate-body`, `/grafana/`, and certbot ACME challenge location.
- All proxy locations include standard headers: X-Real-IP, X-Forwarded-For, X-Forwarded-Proto.
- Nginx health check uses `wget` instead of `curl` because `nginx:stable-alpine` includes wget but not curl.
- Grafana upstream is configured but will return 502 until Grafana is deployed in Story 4.4 — this is expected behavior.
- SSL volume mounts (certbot-webroot, certbot-certs) are mounted read-only, ready for Story 3.2.
- Resource limits: 0.5 CPU, 256MB RAM (Nginx is lightweight).
- All 15 existing tests pass with no regressions.

### Debug Log

No issues encountered during implementation.

### Senior Developer Review (AI)

- 2026-02-15: Adversarial review completed. Added 6 follow-up action items (3 HIGH, 2 MEDIUM, 1 LOW).

## File List

- `nginx/nginx.conf` — **New** — Nginx main configuration
- `nginx/conf.d/default.conf` — **New** — Server block with upstream definitions and proxy routes *(superseded by Story 3.2 → `nginx/templates/default.conf.template`)*
- `docker-compose.prod.yml` — **Modified** — Added nginx service with ports, volumes, health check, resource limits

## Change Log

- 2026-02-15: Created Nginx reverse proxy configuration with worker and Grafana upstreams, SSL preparation volumes, and added nginx service to docker-compose.prod.yml.
- 2026-02-15: Senior Developer Review (AI) performed; status moved to in-progress and review follow-ups added.
- 2026-02-15: All 6 review follow-ups resolved (5 false positives from comparing current state vs commit state, 1 compose validation confirmed). Status moved to done.
