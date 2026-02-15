---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-03-success', 'step-04-journeys', 'step-05-frs', 'step-06-nfrs', 'step-07-technical', 'step-08-constraints', 'step-09-risks', 'step-10-review', 'step-11-complete']
inputDocuments:
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
documentCounts:
  briefs: 0
  research: 0
  brainstorming: 0
  projectDocs: 9
  projectContext: 1
classification:
  projectType: api_backend
  domain: e-commerce/fashion-tech
  complexity: medium
  projectContext: brownfield
workflowType: 'prd'
---

# Product Requirements Document - wearon-worker

**Author:** ABaid
**Date:** 2026-02-15
**Status:** Complete
**Version:** 1.0

## Executive Summary

wearon-worker is the Python backend worker for the WearOn virtual try-on platform. It processes AI image generation tasks and provides body size recommendations. The Next.js frontend pushes generation jobs to a Redis queue; this worker consumes and processes them through OpenAI GPT Image 1.5, stores results in Supabase, and serves size recommendation via a FastAPI HTTP endpoint.

The system currently runs as a single Docker container deployed via GitHub Actions to a VPS. This PRD documents the existing system requirements and defines the next phase: production-grade deployment infrastructure with monitoring, observability, and automated operations.

### Product Context

- **Type:** Backend worker service (no UI)
- **Consumers:** Next.js frontend (via Redis queue), B2B merchants (via Shopify integration), mobile app (via REST API)
- **Channels:** B2C (direct users) and B2B (Shopify stores)
- **Current State:** Core generation pipeline and size recommendation fully implemented and deployed

## Success Criteria

### User Success

- Generation tasks complete within 60 seconds of being queued
- Users receive real-time status updates via Supabase Realtime (no polling delay > 2s)
- Failed generations refund credits immediately (< 1s after failure detection)
- Size recommendations return accurate results (confidence > 0.7) within 5 seconds
- B2B and B2C channels process identically with correct data isolation

### Business Success

- 99.5% uptime for the worker service (measured monthly)
- Zero credit leakage (every failed generation refunds exactly 1 credit)
- Support 300 generation requests per minute (current OpenAI rate limit)
- Operational visibility: all errors surfaced within 5 minutes via alerts
- Zero-downtime deployments for code updates

### Technical Success

- All services (Redis consumer, Celery worker, FastAPI) healthy and monitored
- Structured JSON logs with correlation IDs (request_id) for full request tracing
- Container restarts automatically on crash (< 30s recovery)
- Infrastructure as code: full stack deployable from a single command
- Monitoring dashboards covering: task throughput, error rates, API latency, resource usage

### Measurable Outcomes

| Metric | Target | Measurement |
|--------|--------|-------------|
| Generation success rate | > 95% | Completed / (Completed + Failed) |
| P95 generation latency | < 45s | Queue entry to session completed |
| Size rec P95 latency | < 3s | Request to response |
| Worker uptime | > 99.5% | Health check availability |
| Mean time to detect failure | < 5 min | Error to alert delivery |
| Credit accuracy | 100% | Deducted = completed + refunded |

## Product Scope

### MVP (Completed)

The following is implemented and deployed:

- Redis BRPOP consumer reading from `wearon:tasks:generation`
- Celery task processing: download images, resize to 1024px, call OpenAI GPT Image 1.5, upload to Supabase Storage
- B2B and B2C channel routing (different session tables, credit fields, storage paths)
- Credit management: deduct on queue entry, refund on failure
- Error handling: 429 retry (max 1), moderation block with user message, immediate fail for others
- Startup cleanup: stuck sessions marked failed with credit refund
- FastAPI size recommendation endpoint (POST /estimate-body) via MediaPipe pose estimation
- Health check endpoint (GET /health) with Redis and model status
- Docker multi-stage build
- GitHub Actions CI/CD: test on PR, deploy on push to main
- structlog JSON logging with correlation IDs

### Growth (Next Phase)

Production infrastructure and observability:

- **Production Docker Compose** (`docker-compose.prod.yml`): Orchestrate worker, Redis, Nginx, and monitoring stack as a single deployable unit
- **Nginx Reverse Proxy**: SSL termination (Let's Encrypt), rate limiting, route to worker and Grafana, only ports 80/443 exposed
- **Monitoring Stack**: Prometheus (metrics collection), Grafana (dashboards), Loki (log aggregation), Grafana Alloy (log shipping, replaces deprecated Promtail)
- **Application Metrics**: celery-exporter for Celery task metrics, prometheus-fastapi-instrumentator for HTTP metrics
- **Alerting**: Grafana alert rules with WhatsApp notification channel (via grafana-whatsapp-webhook bridge)
- **Log Retention**: 7-day retention policy for all logs
- **Automated Deployment**: First deploy and subsequent updates fully automated via CI/CD
- **Zero-Downtime Deploy**: Rolling container updates with health check validation

### Vision (Future)

- Horizontal scaling: multiple worker instances with Redis-based coordination
- GPU acceleration for MediaPipe pose estimation
- Model versioning and A/B testing for generation prompts
- Multi-region deployment for reduced latency
- Webhook notifications for B2B partners (generation complete callbacks)
- Batch processing mode for bulk generation requests

## User Journeys

### Journey 1: B2C Generation Request

**Actor:** End user via Next.js frontend

1. User uploads person photo and outfit photo to Supabase Storage
2. Frontend calls Next.js API which deducts 1 credit and LPUSHes task to `wearon:tasks:generation`
3. Worker consumer BRPOPs the task, validates payload, dispatches to Celery
4. Celery task marks session `processing`, downloads images, resizes to 1024px
5. OpenAI GPT Image 1.5 generates try-on result
6. Result uploaded to Supabase Storage (`generated/{user_id}/{session_id}.jpg`)
7. Session updated to `completed` with 6-hour signed URL
8. Supabase Realtime notifies frontend, user sees result

**Failure Path:** If any step fails after step 3, credits are refunded, session marked `failed` with error message. User receives real-time notification of failure.

### Journey 2: B2B Generation Request

**Actor:** Shopify store via B2B API

Identical to B2C except:
- Session table: `store_generation_sessions`
- Credit field: `store_id` instead of `user_id`
- Storage path: `stores/{store_id}/generated/{session_id}.jpg`

### Journey 3: Size Recommendation

**Actor:** Any client via HTTP

1. Client sends POST `/estimate-body` with `{image_url, height_cm}`
2. Worker downloads image, runs MediaPipe 33-landmark pose estimation
3. Calculates body measurements using height calibration
4. Returns size (XS-XXL), confidence score, body type, and measurements

### Journey 4: Worker Restart Recovery

**Actor:** System (automatic)

1. Worker process starts (crash, deploy, or manual restart)
2. `cleanup_stuck_sessions()` finds all `queued` and `processing` sessions
3. Each stuck session marked `failed` with credit refund
4. Celery subprocess started, consumer thread started, FastAPI binds port 8000
5. Normal operation resumes

## Functional Requirements

### FR-1: Generation Task Processing

| ID | Requirement | Priority |
|----|------------|----------|
| FR-1.1 | Worker MUST consume tasks from Redis queue `wearon:tasks:generation` via BRPOP | Must |
| FR-1.2 | Worker MUST validate task payloads against `GenerationTask` Pydantic model | Must |
| FR-1.3 | Worker MUST download input images with SSRF protection (no redirects, content-type validation, 10MB limit) | Must |
| FR-1.4 | Worker MUST resize images to 1024px max dimension before sending to OpenAI | Must |
| FR-1.5 | Worker MUST call OpenAI GPT Image 1.5 `/images/edits` endpoint | Must |
| FR-1.6 | Worker MUST upload generated image to Supabase Storage with correct channel-based path | Must |
| FR-1.7 | Worker MUST create 6-hour signed URL for generated image | Must |
| FR-1.8 | Worker MUST update session status through `queued` -> `processing` -> `completed`/`failed` | Must |

### FR-2: Credit Management

| ID | Requirement | Priority |
|----|------------|----------|
| FR-2.1 | Worker MUST refund credits on generation failure (except during 429 retry) | Must |
| FR-2.2 | Worker MUST NOT refund credits during 429 rate limit retry (prevents double-spend) | Must |
| FR-2.3 | Worker MUST refund credits for moderation-blocked content with user-friendly message | Must |
| FR-2.4 | Worker MUST refund credits for stuck sessions found during startup cleanup | Must |

### FR-3: Error Handling

| ID | Requirement | Priority |
|----|------------|----------|
| FR-3.1 | 429 rate limit errors MUST trigger Celery retry (max 1) with 10s countdown | Must |
| FR-3.2 | 400 moderation blocks MUST fail immediately with user-friendly error message | Must |
| FR-3.3 | 5xx server errors MUST use exponential backoff retry inside OpenAI client | Must |
| FR-3.4 | Consumer errors MUST use 5s sleep backoff to prevent tight-loop | Must |
| FR-3.5 | All other errors MUST fail immediately with no retry | Must |

### FR-4: Size Recommendation

| ID | Requirement | Priority |
|----|------------|----------|
| FR-4.1 | Worker MUST expose POST `/estimate-body` accepting `{image_url, height_cm}` | Must |
| FR-4.2 | Worker MUST validate height_cm between 100-250 cm | Must |
| FR-4.3 | Worker MUST return recommended_size (XS-XXL), measurements, confidence, body_type | Must |
| FR-4.4 | Worker MUST return 422 if full body pose cannot be detected | Must |

### FR-5: Health Monitoring

| ID | Requirement | Priority |
|----|------------|----------|
| FR-5.1 | Worker MUST expose GET `/health` returning MediaPipe and Redis status | Must |
| FR-5.2 | Health status MUST be `ok` only when both model and Redis are operational | Must |
| FR-5.3 | Health status MUST be `degraded` when any check fails | Must |

### FR-6: B2B/B2C Channel Routing

| ID | Requirement | Priority |
|----|------------|----------|
| FR-6.1 | Worker MUST route B2B tasks to `store_generation_sessions` table | Must |
| FR-6.2 | Worker MUST route B2C tasks to `generation_sessions` table | Must |
| FR-6.3 | Worker MUST use `store_id` for B2B credit operations and `user_id` for B2C | Must |
| FR-6.4 | Worker MUST use channel-specific storage paths for generated images | Must |

### FR-7: Production Infrastructure (Growth Phase)

| ID | Requirement | Priority |
|----|------------|----------|
| FR-7.1 | Production deployment MUST use docker-compose.prod.yml orchestrating all services | Must |
| FR-7.2 | Nginx MUST terminate SSL with auto-renewing Let's Encrypt certificates | Must |
| FR-7.3 | Nginx MUST reverse-proxy to worker (port 8000) and Grafana (port 3000) | Must |
| FR-7.4 | Only ports 80 and 443 MUST be exposed to the internet | Must |
| FR-7.5 | Grafana MUST provide unified dashboards for Celery tasks, API metrics, and logs | Should |
| FR-7.6 | Alerts MUST be delivered via WhatsApp using grafana-whatsapp-webhook bridge | Should |
| FR-7.7 | CI/CD MUST automate first deploy and all subsequent updates | Must |

## Non-Functional Requirements

### NFR-1: Performance

| ID | Requirement | Target |
|----|------------|--------|
| NFR-1.1 | Generation P95 latency (queue to completed) | < 45 seconds |
| NFR-1.2 | Size recommendation P95 latency | < 3 seconds |
| NFR-1.3 | Health check response time | < 200ms |
| NFR-1.4 | OpenAI API rate limit compliance | 300 requests/minute max |
| NFR-1.5 | Image download timeout | 30 seconds |

### NFR-2: Reliability

| ID | Requirement | Target |
|----|------------|--------|
| NFR-2.1 | Worker uptime | > 99.5% monthly |
| NFR-2.2 | Automatic restart on crash | < 30 seconds via Docker restart policy |
| NFR-2.3 | Stuck session cleanup on startup | All queued/processing sessions recovered |
| NFR-2.4 | Credit consistency | 100% accuracy (deducted = completed + refunded) |

### NFR-3: Security

| ID | Requirement | Target |
|----|------------|--------|
| NFR-3.1 | SSRF protection on image downloads | No HTTP redirects, content-type validation |
| NFR-3.2 | Image size limit | 10MB maximum per download |
| NFR-3.3 | Secret management | .env file never in Docker image or git |
| NFR-3.4 | Supabase access | Service role key, server-side only |
| NFR-3.5 | Network exposure | Only ports 80/443 internet-facing (via Nginx) |
| NFR-3.6 | SSL/TLS | All external traffic encrypted (Let's Encrypt) |
| NFR-3.7 | Grafana access | Built-in authentication, not publicly open |

### NFR-4: Observability

| ID | Requirement | Target |
|----|------------|--------|
| NFR-4.1 | Structured logging | JSON format with structlog |
| NFR-4.2 | Correlation IDs | request_id in all log lines for a task |
| NFR-4.3 | Metrics collection | Prometheus scraping Celery + FastAPI metrics |
| NFR-4.4 | Log aggregation | Loki with Grafana Alloy shipping |
| NFR-4.5 | Log retention | 7 days |
| NFR-4.6 | Alert latency | < 5 minutes from error to notification |

### NFR-5: Scalability

| ID | Requirement | Target |
|----|------------|--------|
| NFR-5.1 | Celery worker concurrency | Configurable via WORKER_CONCURRENCY (default 5) |
| NFR-5.2 | Task time limit | 300 seconds per task |
| NFR-5.3 | Celery acks_late | Tasks re-queued on worker crash |

## Technical Requirements

### Infrastructure Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Worker | Python 3.12 + Celery + FastAPI | Task processing + HTTP API |
| Queue Broker | Redis 7 Alpine | BRPOP consumer + Celery broker |
| Reverse Proxy | Nginx | SSL termination, routing, rate limiting |
| Metrics | Prometheus | Time-series metrics collection |
| Dashboards | Grafana | Visualization and alerting |
| Logs | Loki + Grafana Alloy | Log aggregation and shipping |
| Celery Metrics | celery-exporter | Export Celery task metrics to Prometheus |
| API Metrics | prometheus-fastapi-instrumentator | Export FastAPI metrics to Prometheus |
| Alerts | grafana-whatsapp-webhook | WhatsApp notification bridge |
| SSL | Let's Encrypt (certbot) | Auto-renewing TLS certificates |
| Container Runtime | Docker + Docker Compose | Service orchestration |
| CI/CD | GitHub Actions | Automated test, build, deploy |
| Image Registry | GHCR (ghcr.io) | Docker image storage |

### Resource Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 2 GB | 4 GB (worker + monitoring stack) |
| Disk | 5 GB | 20 GB (Docker images + 7-day logs + metrics) |
| Network | Outbound HTTPS | OpenAI API, Supabase, Redis |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| REDIS_URL | Yes | Redis connection string |
| SUPABASE_URL | Yes | Supabase project URL |
| SUPABASE_SERVICE_ROLE_KEY | Yes | Supabase service role key |
| OPENAI_API_KEY | Yes | OpenAI API key for GPT Image 1.5 |
| OPENAI_MAX_RETRIES | No | OpenAI retry count (default: 3) |
| WORKER_CONCURRENCY | No | Celery concurrency (default: 5) |

### Cross-Language Queue Contract

Queue key: `wearon:tasks:generation`
Protocol: LPUSH (Next.js producer) / BRPOP (Python consumer)

The Python `GenerationTask` Pydantic model MUST match the TypeScript `GenerationTaskPayload` in the Next.js monorepo. Fields: task_id, channel, store_id, user_id, session_id, image_urls, prompt, request_id, version, created_at.

## Constraints and Assumptions

### Constraints

- **OpenAI Rate Limit:** 300 requests/minute enforced by Celery `task_default_rate_limit`
- **Single VPS Deployment:** All services run on one VPS (no multi-node orchestration)
- **6-Hour Image Expiry:** Signed URLs expire after 6 hours; images are ephemeral
- **No Result Backend:** Celery runs without a result backend; status tracked via Supabase
- **Sync Celery Tasks:** Async operations (httpx, OpenAI) wrapped in `asyncio.new_event_loop()` due to Celery's sync model
- **MediaPipe System Dependencies:** Requires `libgl1` and `libglib2.0-0` at runtime

### Assumptions

- Redis is always available (co-located or networked)
- Supabase service role key has full database access
- OpenAI GPT Image 1.5 API remains available and backward-compatible
- Next.js frontend handles credit deduction before pushing to queue
- Supabase Realtime delivers status updates to frontend within 2 seconds
- VPS has Docker and Docker Compose installed
- GitHub Actions has SSH access to VPS for deployment

## Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| OpenAI API downtime | High — all generations blocked | Low | Health check detects, alert via WhatsApp, user sees degraded status |
| OpenAI moderation false positives | Medium — legitimate images blocked | Medium | User-friendly error message, credit refund, analytics tracking |
| Redis crash | High — queue lost, consumer stops | Low | Docker restart policy, startup cleanup recovers stuck sessions |
| Credit double-spend on 429 retry | High — financial integrity | Low | Retry-before-refund pattern prevents double-spend |
| VPS resource exhaustion | High — all services affected | Medium | Prometheus alerts on CPU/RAM/disk, Grafana dashboards for visibility |
| Promtail deprecation (EOL March 2026) | Medium — log shipping breaks | Certain | Already mitigated: using Grafana Alloy instead of Promtail |
| Docker image size growth | Low — slow deploys | Low | Multi-stage build, .dockerignore, regular base image updates |

## Appendix

### Session Status State Machine

```
queued → processing → completed
  ↓         ↓
  failed    failed
  (refund)  (refund)
```

### Storage Path Convention

- B2C: `generated/{user_id}/{session_id}.jpg`
- B2B: `stores/{store_id}/generated/{session_id}.jpg`

### Monitoring Architecture

```
                     Internet
                        │
                   ┌────┴────┐
                   │  Nginx  │ :80/:443
                   └────┬────┘
                   ┌────┴────────────────┐
                   │                     │
              ┌────┴────┐         ┌──────┴──────┐
              │ Worker  │         │  Grafana    │
              │ :8000   │         │  :3000      │
              └────┬────┘         └──────┬──────┘
                   │                     │
         ┌────────┬┴──────────┐    ┌─────┴──────┐
         │        │           │    │            │
    ┌────┴───┐ ┌──┴───┐ ┌────┴──┐ │            │
    │ Redis  │ │Prom- │ │celery-│ │            │
    │ :6379  │ │etheus│ │export │ │            │
    └────────┘ │:9090 │ │:9808  │ │            │
               └──────┘ └───────┘ │            │
                                  │            │
                          ┌───────┴──┐  ┌──────┴──┐
                          │  Loki    │  │  Alloy  │
                          │  :3100   │  │ (logs)  │
                          └──────────┘  └─────────┘
```

### References

- [Architecture](../../../docs/architecture.md)
- [API Contracts](../../../docs/api-contracts.md)
- [Data Models](../../../docs/data-models.md)
- [Deployment Guide](../../../docs/deployment-guide.md)
- [Story 1.4](../../../docs/1-4-python-worker-generation-pipeline.md)
