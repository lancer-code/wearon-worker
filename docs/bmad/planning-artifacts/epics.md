---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
inputDocuments:
  - docs/bmad/planning-artifacts/prd.md
  - docs/bmad/planning-artifacts/architecture.md
status: complete
---

# wearon-worker - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for wearon-worker, decomposing the Growth-phase requirements from the PRD and Architecture into implementable stories. The MVP phase (generation pipeline, size recommendation, basic CI/CD) is already implemented per Story 1.4.

## Requirements Inventory

### Functional Requirements

FR-1.1: Worker MUST consume tasks from Redis queue `wearon:tasks:generation` via BRPOP
FR-1.2: Worker MUST validate task payloads against `GenerationTask` Pydantic model
FR-1.3: Worker MUST download input images with SSRF protection (no redirects, content-type validation, 10MB limit)
FR-1.4: Worker MUST resize images to 1024px max dimension before sending to OpenAI
FR-1.5: Worker MUST call OpenAI GPT Image 1.5 `/images/edits` endpoint
FR-1.6: Worker MUST upload generated image to Supabase Storage with correct channel-based path
FR-1.7: Worker MUST create 6-hour signed URL for generated image
FR-1.8: Worker MUST update session status through queued → processing → completed/failed
FR-2.1: Worker MUST refund credits on generation failure (except during 429 retry)
FR-2.2: Worker MUST NOT refund credits during 429 rate limit retry
FR-2.3: Worker MUST refund credits for moderation-blocked content with user-friendly message
FR-2.4: Worker MUST refund credits for stuck sessions found during startup cleanup
FR-3.1: 429 rate limit errors MUST trigger Celery retry (max 1) with 10s countdown
FR-3.2: 400 moderation blocks MUST fail immediately with user-friendly error message
FR-3.3: 5xx server errors MUST use exponential backoff retry inside OpenAI client
FR-3.4: Consumer errors MUST use 5s sleep backoff to prevent tight-loop
FR-3.5: All other errors MUST fail immediately with no retry
FR-4.1: Worker MUST expose POST /estimate-body accepting {image_url, height_cm}
FR-4.2: Worker MUST validate height_cm between 100-250 cm
FR-4.3: Worker MUST return recommended_size (XS-XXL), measurements, confidence, body_type
FR-4.4: Worker MUST return 422 if full body pose cannot be detected
FR-5.1: Worker MUST expose GET /health returning MediaPipe and Redis status
FR-5.2: Health status MUST be "ok" only when both model and Redis are operational
FR-5.3: Health status MUST be "degraded" when any check fails
FR-6.1: Worker MUST route B2B tasks to store_generation_sessions table
FR-6.2: Worker MUST route B2C tasks to generation_sessions table
FR-6.3: Worker MUST use store_id for B2B credit operations and user_id for B2C
FR-6.4: Worker MUST use channel-specific storage paths for generated images
FR-7.1: Production deployment MUST use docker-compose.prod.yml orchestrating all services
FR-7.2: Nginx MUST terminate SSL with auto-renewing Let's Encrypt certificates
FR-7.3: Nginx MUST reverse-proxy to worker (port 8000) and Grafana (port 3000)
FR-7.4: Only ports 80 and 443 MUST be exposed to the internet
FR-7.5: Grafana MUST provide unified dashboards for Celery tasks, API metrics, and logs
FR-7.6: Alerts MUST be delivered via WhatsApp using grafana-whatsapp-webhook bridge
FR-7.7: CI/CD MUST automate first deploy and all subsequent updates

### NonFunctional Requirements

NFR-1.1: Generation P95 latency (queue to completed) < 45 seconds
NFR-1.2: Size recommendation P95 latency < 3 seconds
NFR-1.3: Health check response time < 200ms
NFR-1.4: OpenAI API rate limit compliance — 300 requests/minute max
NFR-1.5: Image download timeout — 30 seconds
NFR-2.1: Worker uptime > 99.5% monthly
NFR-2.2: Automatic restart on crash < 30 seconds via Docker restart policy
NFR-2.3: Stuck session cleanup on startup — all queued/processing sessions recovered
NFR-2.4: Credit consistency — 100% accuracy
NFR-3.1: SSRF protection on image downloads
NFR-3.2: Image size limit — 10MB maximum per download
NFR-3.3: Secret management — .env file never in Docker image or git
NFR-3.4: Supabase access — service role key, server-side only
NFR-3.5: Network exposure — only ports 80/443 internet-facing
NFR-3.6: SSL/TLS — all external traffic encrypted
NFR-3.7: Grafana access — built-in authentication, not publicly open
NFR-4.1: Structured logging — JSON format with structlog
NFR-4.2: Correlation IDs — request_id in all log lines
NFR-4.3: Metrics collection — Prometheus scraping Celery + FastAPI
NFR-4.4: Log aggregation — Loki with Grafana Alloy shipping
NFR-4.5: Log retention — 7 days
NFR-4.6: Alert latency < 5 minutes from error to notification
NFR-5.1: Celery worker concurrency configurable via WORKER_CONCURRENCY
NFR-5.2: Task time limit — 300 seconds per task
NFR-5.3: Celery acks_late — tasks re-queued on worker crash

### Additional Requirements

From Architecture:
- ADR-2: Production Docker Compose must orchestrate all services with health check dependencies
- ADR-3: Nginx is the security boundary — internal services only on Docker network
- ADR-4: Monitoring stack uses Grafana Alloy (not Promtail, which is EOL March 2, 2026)
- ADR-5: WhatsApp alerting via grafana-whatsapp-webhook bridge container
- ADR-6: Zero-downtime deployment using Docker Compose --wait with health checks
- ADR-7: Loki configured with 7-day retention and automatic compaction
- Pattern 1: All logs must use structlog with request_id binding
- Pattern 6: Services must declare health check dependencies in docker-compose.prod.yml
- Pattern 7: All secrets in .env file, never hardcoded

### FR Coverage Map

| FR | Epic | Story |
|----|------|-------|
| FR-1.1 through FR-1.8 | MVP (Done) | Story 1.4 |
| FR-2.1 through FR-2.4 | MVP (Done) | Story 1.4 |
| FR-3.1 through FR-3.5 | MVP (Done) | Story 1.4 |
| FR-4.1 through FR-4.4 | MVP (Done) | Story 1.4 |
| FR-5.1 through FR-5.3 | MVP (Done) | Story 1.4 |
| FR-6.1 through FR-6.4 | MVP (Done) | Story 1.4 |
| FR-7.1 | Epic 1 | Story 2.1, 2.2 |
| FR-7.2 | Epic 2 | Story 3.1, 3.2 |
| FR-7.3 | Epic 2 | Story 3.1 |
| FR-7.4 | Epic 2 | Story 3.1 |
| FR-7.5 | Epic 3 | Story 4.3, 4.4 |
| FR-7.6 | Epic 4 | Story 5.1, 5.2 |
| FR-7.7 | Epic 5 | Story 6.1, 6.2 |
| NFR-2.1, NFR-2.2 | Epic 1 | Story 2.2 |
| NFR-3.5, NFR-3.6, NFR-3.7 | Epic 2 | Story 3.1, 3.2 |
| NFR-4.3 | Epic 3 | Story 4.1, 4.2 |
| NFR-4.4, NFR-4.5 | Epic 3 | Story 4.3 |
| NFR-4.6 | Epic 4 | Story 5.1, 5.2 |

## Epic List

| Epic | Title | Stories | Priority |
|------|-------|---------|----------|
| Epic 1 | Production Docker Compose Foundation | 2 | P0 — Foundation |
| Epic 2 | Nginx Reverse Proxy & SSL | 2 | P0 — Security |
| Epic 3 | Metrics & Monitoring | 4 | P1 — Observability |
| Epic 4 | Alerting | 2 | P1 — Operations |
| Epic 5 | Deployment Automation | 3 | P0 — CI/CD |

---

## Epic 1: Production Docker Compose Foundation

**Goal:** Replace raw `docker run` deployment with a Docker Compose orchestration that manages all production services as a single deployable unit with proper health checks and service dependencies.

**References:** FR-7.1, NFR-2.1, NFR-2.2, ADR-2, Pattern 6

### Story 2.1: Create Production Docker Compose Configuration

As a **platform operator**,
I want **a docker-compose.prod.yml that orchestrates the worker and Redis with health checks**,
So that **production deployment is a single command and services start in the correct order**.

**Acceptance Criteria:**

**Given** the production Docker Compose file `docker-compose.prod.yml`,
**When** `docker compose -f docker-compose.prod.yml up -d` is run on a VPS with Docker Compose installed,
**Then** the worker and Redis containers start with the worker depending on Redis being healthy.

**Given** the Redis service in docker-compose.prod.yml,
**When** the container starts,
**Then** Redis runs with password authentication and a health check (`redis-cli ping`).

**Given** the worker service in docker-compose.prod.yml,
**When** Redis is healthy,
**Then** the worker starts with `--restart unless-stopped`, loads env vars from `.env` file, and exposes port 8000 internally on the Docker network (not to host).

**Given** the Docker network configuration,
**When** services are running,
**Then** all services communicate over a dedicated Docker bridge network (`wearon-net`), with no ports exposed to the host except through Nginx (added in Epic 2).

**Tasks:**
- [ ] Create `docker-compose.prod.yml` with worker and Redis services
- [ ] Configure Redis with password auth and health check
- [ ] Configure worker with `depends_on: redis: condition: service_healthy`
- [ ] Create Docker bridge network `wearon-net`
- [ ] Test: `docker compose -f docker-compose.prod.yml up -d` starts both services
- [ ] Test: Worker health check returns `{"status":"ok"}` after startup

### Story 2.2: Add Service Restart Policies and Resource Limits

As a **platform operator**,
I want **restart policies and resource limits on all production containers**,
So that **services recover from crashes automatically and don't exhaust VPS resources**.

**Acceptance Criteria:**

**Given** any production container crashes,
**When** Docker detects the container has stopped,
**Then** Docker restarts it within 30 seconds (`restart: unless-stopped`).

**Given** the worker container,
**When** it is running under load,
**Then** it is limited to the configured CPU and memory limits (preventing OOM from affecting other services).

**Given** Redis container,
**When** it restarts after crash,
**Then** the worker consumer reconnects automatically via its 5s backoff loop.

**Tasks:**
- [ ] Add `restart: unless-stopped` to all services
- [ ] Add `deploy.resources.limits` for CPU and memory
- [ ] Test: Kill worker container, verify auto-restart within 30s
- [ ] Test: Kill Redis, verify worker reconnects after Redis restarts

---

## Epic 2: Nginx Reverse Proxy & SSL

**Goal:** Deploy Nginx as the security boundary, terminating SSL with Let's Encrypt and routing traffic to internal services, with only ports 80/443 exposed to the internet.

**References:** FR-7.2, FR-7.3, FR-7.4, NFR-3.5, NFR-3.6, NFR-3.7, ADR-3

### Story 3.1: Create Nginx Reverse Proxy Configuration

As a **platform operator**,
I want **Nginx to reverse-proxy all HTTP traffic to the worker and Grafana**,
So that **only ports 80 and 443 are exposed to the internet and internal services are protected**.

**Acceptance Criteria:**

**Given** a request to `/health` or `/estimate-body` on ports 80/443,
**When** Nginx receives the request,
**Then** it proxies to the worker container on port 8000 over the internal Docker network.

**Given** a request to `/grafana/*` on ports 80/443,
**When** Nginx receives the request,
**Then** it proxies to the Grafana container on port 3000 over the internal Docker network.

**Given** any direct access attempt to ports 8000, 3000, 9090, 6379, or 3100 from the internet,
**When** the connection is attempted,
**Then** it is refused because only ports 80/443 are mapped to the host.

**Given** the Nginx service in docker-compose.prod.yml,
**When** all upstream services are healthy,
**Then** Nginx starts and serves traffic on ports 80 and 443.

**Tasks:**
- [ ] Create `nginx/nginx.conf` with upstream definitions
- [ ] Create `nginx/conf.d/default.conf` with server block routing
- [ ] Add Nginx service to docker-compose.prod.yml (ports 80:80, 443:443)
- [ ] Configure `depends_on: worker: condition: service_healthy`
- [ ] Test: `curl http://localhost/health` returns worker health response
- [ ] Test: Direct access to port 8000 from outside is refused

### Story 3.2: Set Up Let's Encrypt SSL with Auto-Renewal

As a **platform operator**,
I want **automatic SSL certificate provisioning and renewal via Let's Encrypt**,
So that **all traffic is encrypted and certificates never expire**.

**Acceptance Criteria:**

**Given** a fresh VPS deployment with a domain pointing to the VPS IP,
**When** the first-deploy script runs,
**Then** certbot obtains an initial SSL certificate for the domain.

**Given** the Nginx configuration,
**When** SSL is configured,
**Then** HTTP (port 80) redirects to HTTPS (port 443) except for ACME challenge paths.

**Given** a certificate nearing expiry (< 30 days),
**When** the renewal cron job runs,
**Then** certbot renews the certificate and Nginx reloads to use the new certificate.

**Tasks:**
- [ ] Create `scripts/renew-certs.sh` for certificate renewal
- [ ] Configure Nginx for SSL termination with certificate paths
- [ ] Add HTTP → HTTPS redirect (except `/.well-known/acme-challenge/`)
- [ ] Add certbot volume mounts in docker-compose.prod.yml
- [ ] Document initial certificate provisioning in first-deploy.sh
- [ ] Test: HTTPS works with valid certificate
- [ ] Test: HTTP redirects to HTTPS

---

## Epic 3: Metrics & Monitoring

**Goal:** Deploy Prometheus, Grafana, Loki, and Alloy to provide full observability into the worker's task processing, API performance, and logs.

**References:** FR-7.5, NFR-4.3, NFR-4.4, NFR-4.5, ADR-4, ADR-7, Pattern 1

### Story 4.1: Add Application Metrics to Worker

As a **platform operator**,
I want **the worker to expose Prometheus metrics for FastAPI requests and Celery tasks**,
So that **Prometheus can scrape and store performance data**.

**Acceptance Criteria:**

**Given** the FastAPI application,
**When** `prometheus-fastapi-instrumentator` middleware is added,
**Then** a `/metrics` endpoint is exposed with HTTP request metrics (count, latency, status codes).

**Given** the worker's `requirements.txt`,
**When** `prometheus-fastapi-instrumentator` is added,
**Then** the dependency is installed and the middleware is initialized in `size_rec/app.py`.

**Given** the `/metrics` endpoint,
**When** Prometheus scrapes it,
**Then** metrics are returned in Prometheus exposition format.

**Tasks:**
- [ ] Add `prometheus-fastapi-instrumentator` to requirements.txt
- [ ] Add instrumentator middleware to `size_rec/app.py`
- [ ] Verify `/metrics` endpoint returns Prometheus format data
- [ ] Test: Metrics increment after API requests

### Story 4.2: Deploy Prometheus and Celery Exporter

As a **platform operator**,
I want **Prometheus collecting metrics from the worker and celery-exporter**,
So that **I can visualize task throughput, error rates, and API latency**.

**Acceptance Criteria:**

**Given** the Prometheus configuration `monitoring/prometheus/prometheus.yml`,
**When** Prometheus starts,
**Then** it scrapes the worker's `/metrics` endpoint and celery-exporter on port 9808.

**Given** the celery-exporter container,
**When** it connects to Redis,
**Then** it exports Celery task metrics (task success/failure counts, queue depths, latencies).

**Given** Prometheus and celery-exporter in docker-compose.prod.yml,
**When** the stack starts,
**Then** both containers are healthy and scraping metrics.

**Tasks:**
- [ ] Create `monitoring/prometheus/prometheus.yml` with scrape configs
- [ ] Add Prometheus service to docker-compose.prod.yml (internal port 9090)
- [ ] Add celery-exporter service to docker-compose.prod.yml (internal port 9808)
- [ ] Configure celery-exporter to connect to Redis
- [ ] Test: Prometheus targets page shows worker and celery-exporter as UP

### Story 4.3: Deploy Loki and Grafana Alloy for Log Aggregation

As a **platform operator**,
I want **all container logs shipped to Loki via Grafana Alloy with 7-day retention**,
So that **I can search and filter logs from Grafana without SSH access**.

**Acceptance Criteria:**

**Given** the Loki configuration `monitoring/loki/loki-config.yml`,
**When** Loki starts,
**Then** it accepts log entries and retains them for 7 days with automatic compaction.

**Given** the Alloy configuration `monitoring/alloy/config.alloy`,
**When** Alloy starts,
**Then** it discovers Docker container logs and ships them to Loki with container labels.

**Given** a worker log entry with JSON structure,
**When** it is shipped to Loki,
**Then** the `request_id`, `level`, and `event` fields are searchable in Grafana.

**Tasks:**
- [ ] Create `monitoring/loki/loki-config.yml` with 7-day retention
- [ ] Create `monitoring/alloy/config.alloy` with Docker log discovery
- [ ] Add Loki service to docker-compose.prod.yml (internal port 3100)
- [ ] Add Alloy service to docker-compose.prod.yml with Docker socket mount
- [ ] Test: Worker logs appear in Loki within 30 seconds
- [ ] Test: Logs older than 7 days are automatically deleted

### Story 4.4: Deploy Grafana with Auto-Provisioned Dashboards

As a **platform operator**,
I want **Grafana pre-configured with Prometheus and Loki datasources and dashboards for Celery, FastAPI, and system overview**,
So that **I have immediate visibility after deployment without manual setup**.

**Acceptance Criteria:**

**Given** Grafana with provisioning files in `monitoring/grafana/provisioning/`,
**When** Grafana starts,
**Then** Prometheus and Loki datasources are automatically configured.

**Given** the dashboard provisioning config,
**When** Grafana starts,
**Then** three dashboards are auto-loaded: Celery tasks, FastAPI metrics, and system overview.

**Given** Grafana configured with `grafana.ini`,
**When** a user navigates to `/grafana/` via Nginx,
**Then** they see the Grafana login page with built-in authentication enabled.

**Tasks:**
- [ ] Create `monitoring/grafana/provisioning/datasources/datasources.yml`
- [ ] Create `monitoring/grafana/provisioning/dashboards/dashboards.yml`
- [ ] Create `monitoring/grafana/provisioning/dashboards/celery.json`
- [ ] Create `monitoring/grafana/provisioning/dashboards/fastapi.json`
- [ ] Create `monitoring/grafana/provisioning/dashboards/overview.json`
- [ ] Create `monitoring/grafana/grafana.ini` (root_url, auth settings)
- [ ] Add Grafana service to docker-compose.prod.yml (internal port 3000)
- [ ] Test: Grafana loads with all datasources and dashboards pre-configured
- [ ] Test: Celery dashboard shows task success/failure rates

---

## Epic 4: Alerting

**Goal:** Configure Grafana alert rules with WhatsApp notification delivery for critical system events.

**References:** FR-7.6, NFR-4.6, ADR-5

### Story 5.1: Deploy WhatsApp Webhook Bridge

As a **platform operator**,
I want **a grafana-whatsapp-webhook container running alongside Grafana**,
So that **Grafana alerts can be delivered to WhatsApp**.

**Acceptance Criteria:**

**Given** the grafana-whatsapp-webhook container,
**When** it starts with WhatsApp Business API credentials,
**Then** it listens for Grafana webhook payloads on an internal port.

**Given** a Grafana alert fires,
**When** the webhook payload is sent to the WhatsApp bridge,
**Then** the alert message is delivered to the configured WhatsApp number within 60 seconds.

**Tasks:**
- [ ] Add grafana-whatsapp-webhook service to docker-compose.prod.yml
- [ ] Configure WhatsApp Business API credentials in .env
- [ ] Add webhook contact point in Grafana provisioning
- [ ] Test: Send test alert, verify WhatsApp message received

### Story 5.2: Create Grafana Alert Rules

As a **platform operator**,
I want **alert rules for critical system events (errors, health failures, resource exhaustion)**,
So that **I'm notified within 5 minutes of any production issue**.

**Acceptance Criteria:**

**Given** the Celery task error rate exceeds 10% over 5 minutes,
**When** Grafana evaluates the alert rule,
**Then** an alert fires and is sent to WhatsApp.

**Given** the worker health check returns "degraded",
**When** the health check fails for more than 2 minutes,
**Then** an alert fires with the specific failing component (Redis or MediaPipe).

**Given** VPS CPU exceeds 85% or available disk drops below 2 GB,
**When** the condition persists for 5 minutes,
**Then** a resource alert fires.

**Given** no generation tasks have been processed for 30 minutes during business hours,
**When** Grafana evaluates the rule,
**Then** a "queue stalled" alert fires.

**Tasks:**
- [ ] Create alert rule: High task error rate (> 10% for 5 min)
- [ ] Create alert rule: Worker health degraded (> 2 min)
- [ ] Create alert rule: High CPU (> 85% for 5 min)
- [ ] Create alert rule: Low disk space (< 2 GB for 5 min)
- [ ] Create alert rule: Queue stalled (0 tasks processed for 30 min)
- [ ] Configure notification policy to route all alerts to WhatsApp
- [ ] Test: Trigger each alert condition and verify WhatsApp delivery

---

## Epic 5: Deployment Automation

**Goal:** Automate first deploy and all subsequent deploys via CI/CD, achieving zero-downtime updates.

**References:** FR-7.7, ADR-6

### Story 6.1: Create First-Deploy Script

As a **platform operator**,
I want **a single script that sets up a fresh VPS from scratch**,
So that **the first deployment doesn't require manual container management**.

**Acceptance Criteria:**

**Given** a fresh VPS with Docker and Docker Compose installed,
**When** `scripts/first-deploy.sh` is executed with the domain name as argument,
**Then** it creates the `/opt/wearon/` directory, prompts for `.env` file configuration, pulls all Docker images, obtains SSL certificates via certbot, and starts all services.

**Given** the first-deploy script completes,
**When** `curl https://{domain}/health` is called,
**Then** it returns `{"status":"ok"}`.

**Tasks:**
- [ ] Create `scripts/first-deploy.sh`
- [ ] Install Docker and Docker Compose if not present
- [ ] Create `/opt/wearon/` directory structure
- [ ] Prompt for .env file with required variables
- [ ] Pull all Docker images
- [ ] Obtain initial Let's Encrypt certificate
- [ ] Start all services via docker-compose.prod.yml
- [ ] Verify health check passes
- [ ] Test: Run on fresh VPS, verify full stack operational

### Story 6.2: Update CI/CD for Zero-Downtime Docker Compose Deploy

As a **platform operator**,
I want **the GitHub Actions pipeline to deploy using Docker Compose with zero downtime**,
So that **code pushes to main don't interrupt active generation tasks**.

**Acceptance Criteria:**

**Given** a push to the main branch,
**When** the deploy job runs,
**Then** it SSHes to the VPS, pulls the new worker image, and runs `docker compose -f docker-compose.prod.yml up -d --wait` for zero-downtime update.

**Given** the new worker container starting,
**When** Docker Compose validates the health check,
**Then** the old container is stopped only after the new one is healthy.

**Given** tasks in the Redis queue during deployment,
**When** the old container stops,
**Then** pending tasks are picked up by the new container after startup cleanup.

**Tasks:**
- [ ] Update `.github/workflows/ci-cd.yml` deploy job
- [ ] Replace `docker run` commands with `docker compose` commands
- [ ] Use `--wait` flag for health check validation
- [ ] Add `docker compose -f docker-compose.prod.yml pull worker` before up
- [ ] Test: Deploy with active queue, verify no tasks lost
- [ ] Test: Health check passes within 60 seconds of deploy

### Story 6.3: Add Certificate Renewal Cron Job

As a **platform operator**,
I want **SSL certificates to auto-renew before expiry**,
So that **HTTPS never goes down due to expired certificates**.

**Acceptance Criteria:**

**Given** the VPS cron configuration,
**When** the renewal script runs daily at 3 AM,
**Then** certbot checks certificate expiry and renews if needed (< 30 days remaining).

**Given** a successful certificate renewal,
**When** certbot obtains the new certificate,
**Then** Nginx is reloaded to use the new certificate without downtime.

**Tasks:**
- [ ] Create `scripts/renew-certs.sh` with certbot renew + nginx reload
- [ ] Add cron job setup to first-deploy.sh (daily at 3 AM)
- [ ] Test: Run renewal script, verify Nginx picks up new certs
