---
stepsCompleted: ['step-01-init', 'step-02-context', 'step-03-starter', 'step-04-decisions', 'step-05-patterns', 'step-06-structure', 'step-07-validation', 'step-08-complete']
inputDocuments:
  - docs/bmad/planning-artifacts/prd.md
  - docs/index.md
  - docs/architecture.md
  - docs/project-overview.md
  - docs/api-contracts.md
  - docs/data-models.md
  - docs/source-tree-analysis.md
  - docs/development-guide.md
  - docs/deployment-guide.md
  - docs/1-4-python-worker-generation-pipeline.md
  - .claude/commands/project-context.md
  - CLAUDE.md
workflowType: 'architecture'
project_name: 'wearon-worker'
user_name: 'ABaid'
date: '2026-02-15'
status: 'complete'
---

# Architecture Decision Document — wearon-worker

**Author:** ABaid
**Date:** 2026-02-15
**Status:** Complete
**Version:** 1.0

---

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
The PRD defines 7 FR groups (38 requirements) covering the existing generation pipeline, credit management, error handling, size recommendation, health monitoring, B2B/B2C routing, and the planned production infrastructure. All MVP-phase FRs are implemented. Growth-phase FRs (FR-7) require new infrastructure components: Nginx, Prometheus, Grafana, Loki, Alloy, and docker-compose orchestration.

**Non-Functional Requirements:**
5 NFR groups (17 requirements) drive architectural decisions:
- **Performance:** P95 generation < 45s, size rec < 3s, 300 req/min rate limit
- **Reliability:** 99.5% uptime, < 30s crash recovery, 100% credit consistency
- **Security:** SSRF protection, ports 80/443 only, SSL/TLS, Grafana auth
- **Observability:** Structured JSON logs, correlation IDs, Prometheus metrics, Loki log aggregation, 7-day retention, < 5 min alert latency
- **Scalability:** Configurable concurrency, acks_late for crash recovery

**Scale & Complexity:**
- Primary domain: Backend API / worker service
- Complexity level: Medium (AI integration, dual channels, credit management)
- Architectural components: 10 (worker, Redis, Nginx, Prometheus, Grafana, Loki, Alloy, celery-exporter, whatsapp-webhook, certbot)

### Technical Constraints & Dependencies

| Constraint | Impact |
|-----------|--------|
| Single VPS deployment | All services must co-exist on one machine |
| OpenAI rate limit (300/min) | Celery rate limiting enforced at task level |
| Celery sync model | Async operations wrapped in `asyncio.new_event_loop()` |
| MediaPipe system deps | Requires `libgl1`, `libglib2.0-0` in Docker image |
| 6-hour image expiry | Ephemeral storage, no long-term persistence |
| Cross-language queue contract | Python Pydantic model must match TypeScript type |

### Cross-Cutting Concerns Identified

1. **Correlation tracking** — `request_id` must flow through all components (consumer → Celery → services → logs)
2. **Credit integrity** — Deduction, refund, and retry-before-refund must be atomic across B2B/B2C channels
3. **Health monitoring** — All 3 services (consumer, Celery, FastAPI) must be independently monitored
4. **Secret management** — Environment variables must never leak into images, logs, or version control
5. **Container orchestration** — All services must start in correct order with health check dependencies

---

## Technology Stack (Brownfield — Existing)

This is a brownfield project. The core technology stack is already implemented and deployed. No starter template evaluation is needed.

### Current Stack

| Layer | Technology | Version | Decision Rationale |
|-------|-----------|---------|-------------------|
| Language | Python | 3.12 | Team expertise, AI/ML ecosystem, MediaPipe support |
| Task Queue | Celery | 5.4+ | Industry standard, rate limiting, retry logic, acks_late |
| Queue Broker | Redis | 7 Alpine | Shared with Next.js (LPUSH/BRPOP), minimal overhead |
| Web Framework | FastAPI | 0.116+ | Async support, Pydantic integration, auto-docs |
| HTTP Client | httpx | 0.28+ | Async HTTP, timeout control, redirect control (SSRF) |
| AI Generation | OpenAI GPT Image 1.5 | API | Platform requirement — virtual try-on core capability |
| Pose Estimation | MediaPipe | 0.10+ | 33-landmark pose, runs on CPU, no GPU required |
| Image Processing | Pillow | 11+ | Resize, format conversion, lightweight |
| Database/Storage | Supabase | 2.13+ | Platform choice — shared with Next.js frontend |
| Validation | Pydantic | 2.10+ | Type-safe models, settings management |
| Logging | structlog | 24.4+ | JSON structured logging, processor pipeline |
| Server | Uvicorn | 0.34+ | ASGI server for FastAPI |
| Testing | pytest + pytest-asyncio | 8.3+ | Standard Python testing |
| Container | Docker | Multi-stage | Production deployment |

### New Stack (Growth Phase)

| Layer | Technology | Version | Decision Rationale |
|-------|-----------|---------|-------------------|
| Reverse Proxy | Nginx | Latest stable | SSL termination, rate limiting, routing, security boundary |
| SSL | Let's Encrypt (certbot) | Latest | Free, auto-renewing TLS certificates |
| Metrics | Prometheus | Latest | Industry standard time-series metrics |
| Dashboards | Grafana | Latest OSS | Unified visualization, alerting, Loki integration |
| Log Aggregation | Loki | Latest | Designed for Grafana, label-based, cost-efficient |
| Log Shipping | Grafana Alloy | Latest | Replaces deprecated Promtail (EOL March 2, 2026) |
| Celery Metrics | celery-exporter | Latest | Exports Celery task metrics to Prometheus format |
| API Metrics | prometheus-fastapi-instrumentator | Latest | FastAPI middleware exporting HTTP metrics |
| Alerting | grafana-whatsapp-webhook | Latest | Bridges Grafana alerts to WhatsApp Business API |

---

## Core Architectural Decisions

### ADR-1: Multi-Service Single-Process Architecture

**Decision:** Run Redis consumer, Celery worker, and FastAPI in a single Python process orchestrated by `main.py`.

**Context:** The worker needs to consume from Redis, process tasks via Celery, and serve HTTP endpoints. Running these as separate containers would add deployment complexity without benefit at current scale.

**Rationale:**
- Single container simplifies deployment and monitoring
- Services share the same process lifecycle (startup/shutdown)
- Celery runs as a subprocess, consumer as a daemon thread, FastAPI blocks main thread
- Appropriate for current single-VPS deployment model

**Consequences:**
- Cannot scale individual services independently (acceptable at current scale)
- Single point of failure (mitigated by Docker restart policy and startup cleanup)
- All services must fit within one container's resource allocation

### ADR-2: Production Docker Compose Orchestration

**Decision:** Use `docker-compose.prod.yml` to orchestrate all production services as a single deployable unit.

**Context:** Current deployment uses raw `docker run` commands, which doesn't manage Redis or monitoring services. First deploy requires manual setup. No service coordination.

**Rationale:**
- Single command deploys entire stack: worker, Redis, Nginx, monitoring
- Declarative service dependencies with health checks
- Consistent environment between first deploy and updates
- Replaces fragile manual SSH commands in CI/CD

**Consequences:**
- VPS must have Docker Compose installed
- All services share one host (acceptable for single-VPS model)
- CI/CD pipeline simplified to `docker compose pull && docker compose up -d`

### ADR-3: Nginx as Security Boundary

**Decision:** Deploy Nginx as reverse proxy, exposing only ports 80 and 443 to the internet.

**Context:** Without Nginx, the worker's FastAPI port (8000), Grafana (3000), Prometheus (9090), Redis (6379), and Loki (3100) would all need direct firewall rules. Exposing internal services increases attack surface.

**Rationale:**
- Single entry point for all HTTP traffic
- SSL termination with auto-renewing Let's Encrypt certificates
- Rate limiting at the edge (before requests reach the worker)
- Internal services only accessible via Docker network
- Grafana accessible at `/grafana` path (or subdomain) through Nginx

**Consequences:**
- Nginx configuration must be maintained
- Let's Encrypt requires port 80 for ACME challenges
- Slightly increased latency (negligible for this use case)

**Nginx Routing:**

| Path/Domain | Target | Auth |
|------------|--------|------|
| `/health` | Worker :8000 | None |
| `/estimate-body` | Worker :8000 | None (rate limited) |
| `/grafana/*` | Grafana :3000 | Grafana built-in auth |

### ADR-4: Grafana + Prometheus + Loki Monitoring Stack

**Decision:** Deploy Prometheus for metrics, Loki for logs, and Grafana as the unified dashboard, with Grafana Alloy for log shipping.

**Context:** Currently, the only visibility into the worker is SSH + `docker logs`. No metrics, no alerting, no centralized log search. Errors may go unnoticed for hours.

**Rationale:**
- **Prometheus:** Industry standard for metrics; scrapes celery-exporter and FastAPI instrumentator
- **Grafana:** Unified dashboard for metrics AND logs; built-in alerting
- **Loki:** Label-based log aggregation designed for Grafana; much lighter than ELK
- **Alloy:** Replaces Promtail (EOL March 2, 2026); Grafana's official log/metric collector
- **celery-exporter:** Exports Celery task metrics (success/failure rates, latencies, queue depths)
- **prometheus-fastapi-instrumentator:** Exports HTTP request metrics from FastAPI

**Consequences:**
- Additional ~1.5 GB RAM for monitoring stack
- 7-day log retention requires ~2-5 GB disk (at current volume)
- Monitoring containers add to Docker Compose complexity
- Grafana requires initial dashboard provisioning

### ADR-5: WhatsApp Alerting via Webhook Bridge

**Decision:** Use `grafana-whatsapp-webhook` as a bridge between Grafana alerting and WhatsApp Business API.

**Context:** Native Grafana does not support WhatsApp as an alert channel. Team needs mobile-first alert notifications.

**Rationale:**
- Lightweight webhook container that translates Grafana alert JSON to WhatsApp messages
- Uses WhatsApp Business API (free tier available)
- Alternative approaches (Telegram, Slack) were considered but WhatsApp preferred for the team
- Runs as a small sidecar container in docker-compose

**Consequences:**
- Requires WhatsApp Business API account setup
- grafana-whatsapp-webhook is a third-party container (evaluate trust)
- Fallback: Grafana email alerts if WhatsApp bridge fails

### ADR-6: Zero-Downtime Deployment Strategy

**Decision:** Use Docker Compose rolling updates with health check validation for zero-downtime deploys.

**Context:** Current deployment stops the container, pulls new image, starts new container. This creates a gap where no worker is processing tasks.

**Rationale:**
- Docker Compose `--wait` flag ensures new container is healthy before old is stopped
- Health check endpoint (`/health`) validates both MediaPipe model and Redis connection
- Redis queue acts as buffer — tasks queued during deploy are processed when new container is ready
- Startup cleanup handles any edge cases from the transition

**Consequences:**
- Brief period where two containers may run simultaneously (acceptable on single VPS)
- Health check must be reliable and fast (< 200ms requirement)
- CI/CD pipeline uses `docker compose up -d --wait` instead of manual stop/start

### ADR-7: 7-Day Log Retention

**Decision:** Configure Loki with 7-day log retention and automatic compaction.

**Context:** Need enough history for debugging production issues without consuming excessive disk on a single VPS.

**Rationale:**
- 7 days covers a full business week for incident investigation
- Keeps disk usage bounded (~2-5 GB at current log volume)
- Loki compaction automatically cleans expired data
- Prometheus metrics retain longer trends; logs are for detailed debugging

**Consequences:**
- Cannot search logs older than 7 days
- Must extract and archive critical error details if longer retention needed
- Disk usage is predictable and bounded

---

## Implementation Patterns & Consistency Rules

These patterns ensure AI agents implement consistently across the codebase.

### Pattern 1: Logging Convention

**Rule:** ALL log calls MUST use structlog with `request_id` binding.

```python
import structlog
logger = structlog.get_logger()

# Bind request_id at task entry
log = logger.bind(request_id=task.request_id)
log.info("processing_started", session_id=task.session_id)

# NEVER use print() or standard logging
# NEVER log without request_id binding in task context
```

**Why:** Without this rule, agents might use `print()` or `logging.info()`, breaking structured log aggregation in Loki.

### Pattern 2: Error Handling — Retry vs Fail

**Rule:** Only 429 rate limit errors trigger Celery retry. ALL other errors fail immediately with credit refund.

```python
# 429 → Retry (max 1), do NOT refund yet
if status_code == 429:
    self.retry(countdown=10, max_retries=1)

# 400 moderation → Fail with user message, refund
# 5xx → Exponential backoff INSIDE openai_client (not Celery retry), refund on final failure
# Everything else → Fail immediately, refund
```

**Why:** Without this rule, agents might add retry logic for non-429 errors, causing delayed failures or credit double-spend.

### Pattern 3: B2B/B2C Channel Routing

**Rule:** Channel routing MUST use the helper functions in `worker/tasks.py`. Never hardcode table names or paths.

```python
# Determine table and path from channel
table = "store_generation_sessions" if channel == "b2b" else "generation_sessions"
id_field = "store_id" if channel == "b2b" else "user_id"
storage_path = f"stores/{id}/generated/" if channel == "b2b" else f"generated/{id}/"
```

**Why:** Without this rule, agents might route B2B data to B2C tables or vice versa, causing data leakage between channels.

### Pattern 4: Async in Celery

**Rule:** Async functions called from Celery tasks MUST use a fresh event loop with `try/finally` cleanup.

```python
loop = asyncio.new_event_loop()
try:
    result = loop.run_until_complete(async_function())
finally:
    loop.close()
```

**Why:** Celery tasks are synchronous. Without explicit loop management, event loops leak and cause "loop is already running" errors.

### Pattern 5: Image Download Security

**Rule:** ALL image downloads MUST use httpx with: no redirects, content-type validation (`image/*`), and 10MB size limit.

```python
async with httpx.AsyncClient(follow_redirects=False) as client:
    response = await client.get(url, timeout=30)
    content_type = response.headers.get("content-type", "")
    if not content_type.startswith("image/"):
        raise ValueError("Invalid content type")
    if len(response.content) > 10 * 1024 * 1024:
        raise ValueError("Image too large")
```

**Why:** Without this rule, agents might enable redirects (SSRF vulnerability) or skip content-type validation (arbitrary file download).

### Pattern 6: Docker Compose Service Dependencies

**Rule:** Production services MUST declare health check dependencies in docker-compose.prod.yml.

```yaml
services:
  worker:
    depends_on:
      redis:
        condition: service_healthy
  nginx:
    depends_on:
      worker:
        condition: service_healthy
      grafana:
        condition: service_healthy
  grafana:
    depends_on:
      prometheus:
        condition: service_healthy
      loki:
        condition: service_healthy
```

**Why:** Without explicit dependencies, services may start before their dependencies are ready, causing startup failures.

### Pattern 7: Environment Variable Management

**Rule:** ALL secrets MUST be in `.env` file on VPS. NEVER hardcode secrets or commit them. Docker Compose references `env_file: .env`.

**Why:** Without this rule, agents might hardcode API keys in docker-compose.yml or Dockerfiles.

---

## Project Structure & Boundaries

### Current Structure (MVP — Implemented)

```
wearon-worker/
├── main.py                      # Unified entrypoint (orchestrates all 3 services)
├── config/
│   ├── __init__.py
│   ├── settings.py              # Pydantic Settings (env vars)
│   └── logging_config.py        # structlog JSON formatter
├── models/
│   ├── __init__.py
│   ├── task_payload.py          # GenerationTask (cross-language contract)
│   ├── generation.py            # SessionStatus, SessionUpdate
│   └── size_rec.py              # EstimateBody request/response
├── services/
│   ├── __init__.py
│   ├── openai_client.py         # GPT Image 1.5 (httpx, retries, moderation)
│   ├── supabase_client.py       # Lazy singleton (service role key)
│   ├── image_processor.py       # Download (SSRF safe) + resize to 1024px
│   └── redis_client.py          # Async Redis health check
├── worker/
│   ├── __init__.py
│   ├── celery_app.py            # Celery config (rate limit, acks_late)
│   ├── consumer.py              # BRPOP loop → Pydantic → Celery dispatch
│   ├── tasks.py                 # process_generation (pipeline orchestration)
│   └── startup.py               # Cleanup stuck sessions on restart
├── size_rec/
│   ├── __init__.py
│   ├── app.py                   # FastAPI (/estimate-body, /health)
│   ├── mediapipe_service.py     # MediaPipe Pose singleton
│   ├── size_calculator.py       # Landmarks → measurements → size
│   └── image_processing.py      # Image download for pose estimation
├── tests/
│   ├── conftest.py              # sys.path setup
│   ├── test_consumer.py
│   ├── test_task_payload.py
│   ├── test_tasks.py
│   ├── test_size_rec_app.py
│   ├── test_mediapipe_service.py
│   └── test_size_calculator.py
├── Dockerfile                   # Multi-stage production build
├── docker-compose.yml           # Local dev (Redis + worker)
├── Makefile                     # dev, up, down, logs, test, build
├── requirements.txt
├── pyproject.toml
├── .env.example
├── .dockerignore
├── .github/workflows/ci-cd.yml
└── README.md
```

### Growth Phase — New Files

```
wearon-worker/
├── docker-compose.prod.yml      # Production orchestration (all services)
├── nginx/
│   ├── nginx.conf               # Reverse proxy config
│   └── conf.d/
│       └── default.conf         # Server block (SSL, routing)
├── monitoring/
│   ├── prometheus/
│   │   └── prometheus.yml       # Scrape config (worker, celery-exporter)
│   ├── grafana/
│   │   ├── provisioning/
│   │   │   ├── datasources/
│   │   │   │   └── datasources.yml    # Prometheus + Loki datasources
│   │   │   └── dashboards/
│   │   │       ├── dashboards.yml     # Dashboard auto-provisioning config
│   │   │       ├── celery.json        # Celery task dashboard
│   │   │       ├── fastapi.json       # FastAPI metrics dashboard
│   │   │       └── overview.json      # System overview dashboard
│   │   └── grafana.ini          # Grafana server config (root_url, auth)
│   ├── alloy/
│   │   └── config.alloy         # Alloy config (Docker log discovery → Loki)
│   └── loki/
│       └── loki-config.yml      # Loki config (7-day retention, storage)
├── scripts/
│   ├── first-deploy.sh          # Initial VPS setup script
│   └── renew-certs.sh           # Let's Encrypt renewal script
└── .github/workflows/
    └── ci-cd.yml                # Updated: docker compose deploy
```

### Component Boundaries

| Component | Responsibility | Boundary |
|-----------|---------------|----------|
| `main.py` | Process orchestration | Starts/stops all services, handles signals |
| `worker/` | Task processing | Consumes queue, processes tasks, manages credits |
| `services/` | External integrations | OpenAI, Supabase, image download — no business logic |
| `models/` | Data validation | Pure Pydantic models — no side effects |
| `size_rec/` | Size recommendation | Independent FastAPI app — no dependency on worker/ |
| `config/` | Configuration | Settings + logging — no business logic |
| `nginx/` | Network boundary | SSL, routing, rate limiting — no application logic |
| `monitoring/` | Observability | Metrics, logs, dashboards — read-only access to worker data |

### Data Flow Boundaries

```
Internet → Nginx → Worker FastAPI (/health, /estimate-body)
                 → Grafana (/grafana/*)

Redis (internal) → Worker Consumer → Celery → OpenAI (external)
                                            → Supabase (external)

Worker logs → Alloy → Loki → Grafana
Worker metrics → Prometheus → Grafana
Celery metrics → celery-exporter → Prometheus → Grafana
Grafana alerts → whatsapp-webhook → WhatsApp API (external)
```

---

## Architecture Validation

### Requirements Coverage Matrix

| Requirement Group | PRD Reference | Architecture Coverage |
|------------------|--------------|----------------------|
| FR-1: Generation Pipeline | FR-1.1–1.8 | ADR-1 (multi-service), Pattern 4 (async), Pattern 5 (security) |
| FR-2: Credit Management | FR-2.1–2.4 | Pattern 2 (retry vs fail), ADR-1 |
| FR-3: Error Handling | FR-3.1–3.5 | Pattern 2, ADR-1 |
| FR-4: Size Recommendation | FR-4.1–4.4 | ADR-1 (FastAPI co-located) |
| FR-5: Health Monitoring | FR-5.1–5.3 | ADR-3 (Nginx routing), ADR-6 (health checks) |
| FR-6: B2B/B2C Routing | FR-6.1–6.4 | Pattern 3 (channel routing) |
| FR-7: Production Infra | FR-7.1–7.7 | ADR-2, ADR-3, ADR-4, ADR-5, ADR-6 |
| NFR-1: Performance | NFR-1.1–1.5 | Celery rate limiting, image resize |
| NFR-2: Reliability | NFR-2.1–2.4 | ADR-6 (zero-downtime), Docker restart, startup cleanup |
| NFR-3: Security | NFR-3.1–3.7 | ADR-3 (Nginx), Pattern 5, Pattern 7 |
| NFR-4: Observability | NFR-4.1–4.6 | ADR-4 (monitoring), ADR-7 (retention), Pattern 1 (logging) |
| NFR-5: Scalability | NFR-5.1–5.3 | Celery config, acks_late |

### Validation Checklist

| Check | Status | Notes |
|-------|--------|-------|
| All FRs covered by architecture | PASS | 38/38 FRs mapped to ADRs/patterns |
| All NFRs addressed | PASS | 17/17 NFRs mapped |
| Security boundaries defined | PASS | Nginx + SSRF protection + secret management |
| Cross-cutting concerns resolved | PASS | 5/5 concerns addressed (logging, credits, health, secrets, orchestration) |
| No orphaned components | PASS | All components have clear boundaries and data flows |
| Technology choices justified | PASS | Brownfield stack retained, new stack researched (Alloy over Promtail) |
| Deployment strategy defined | PASS | Docker Compose + zero-downtime + first-deploy script |
| Monitoring covers all services | PASS | Worker, Celery, FastAPI, Redis all monitored |

### Identified Gaps (None Critical)

| Gap | Severity | Mitigation |
|-----|---------|------------|
| No database backup strategy | Low | Supabase handles backups (managed service) |
| No multi-VPS failover | Low | Single VPS accepted per PRD constraints |
| WhatsApp webhook trust | Low | Evaluate container source, pin image version |

---

## Completion & Handoff

### Architecture Summary

This architecture document covers the wearon-worker production deployment evolution:

- **7 ADRs** covering: multi-service process, Docker Compose orchestration, Nginx security boundary, monitoring stack, WhatsApp alerting, zero-downtime deploy, log retention
- **7 implementation patterns** ensuring AI agent consistency: logging, error handling, channel routing, async, image security, service dependencies, secrets
- **Full project structure** with current (MVP) and growth-phase file layouts
- **Complete validation** with 100% FR/NFR coverage

### Next Steps

1. **Create Epics & Stories** (`/bmad:bmm:workflows:create-epics-and-stories`) — Break down Growth-phase requirements into implementable stories
2. **Implementation Readiness** (`/bmad:bmm:workflows:check-implementation-readiness`) — Validate PRD + Architecture + Epics alignment
3. **Sprint Planning** — Begin implementation of the production infrastructure

### Implementation Priority Order

1. `docker-compose.prod.yml` + Redis (foundation for all other services)
2. Nginx + Let's Encrypt (security boundary before exposing monitoring)
3. Prometheus + celery-exporter + prometheus-fastapi-instrumentator (metrics)
4. Loki + Alloy (log aggregation)
5. Grafana + dashboards + provisioning (visualization)
6. WhatsApp webhook + alert rules (alerting)
7. CI/CD pipeline update (automated deployment)
8. `first-deploy.sh` script (one-command initial setup)
