# Story 6.1: Create First-Deploy Script

Status: review

## Story

As a **platform operator**,
I want **a single script that sets up a fresh VPS from scratch**,
So that **the first deployment doesn't require manual container management**.

## Existing Infrastructure (Already Implemented)

- `docker-compose.prod.yml` — Complete production compose (from Epics 1-4)
- `.env.example` — All required environment variables documented
- CI/CD pushes worker image to `ghcr.io/lancer-code/wearon-worker:latest`
- SSL scripts from Story 3.2 (`scripts/init-ssl.sh`)

## Acceptance Criteria

1. **Given** a fresh VPS with Docker and Docker Compose installed,
   **When** `scripts/first-deploy.sh` is executed with the domain name as argument,
   **Then** it creates the `/opt/wearon/` directory, prompts for `.env` file configuration, pulls all Docker images, obtains SSL certificates via certbot, and starts all services.

2. **Given** the first-deploy script completes,
   **When** `curl https://{domain}/health` is called,
   **Then** it returns `{"status":"ok"}`.

## Tasks / Subtasks

- [x] Task 1: Create first-deploy script
  - [x] 1.1 Create `scripts/first-deploy.sh` (executable)
  - [x] 1.2 Accept domain name as CLI argument (`${1:?Usage}`)
  - [x] 1.3 Check prerequisites (docker, docker compose plugin)
  - [x] 1.4 Create `/opt/wearon/` directory structure with correct ownership
  - [x] 1.5 Copy docker-compose.prod.yml, nginx/, monitoring/, scripts/, .env.example
  - [x] 1.6 Create `.env` from template with DOMAIN pre-filled, prompt operator to edit
  - [x] 1.7 Pull all Docker images (`docker compose pull`)
  - [x] 1.8 Run SSL certificate provisioning (`scripts/init-ssl.sh`)
  - [x] 1.9 Start all services (`docker compose -f docker-compose.prod.yml up -d`)
  - [x] 1.10 Wait for health checks (120s timeout, 5s intervals)
  - [x] 1.11 Print success message with service URLs (health + Grafana)

- [x] Task 2: Certificate renewal cron
  - [x] 2.1 Deferred to Story 6.3 as designed

- [x] Task 3: Validation
  - [x] 3.1 Script passes `bash -n` syntax check
  - [x] 3.2 All 15 existing tests pass (no regressions)
  - [ ] 3.3 Full VPS deploy requires production environment

## Dev Notes

### Script Flow (8 steps)

1. Check prerequisites (docker, docker compose)
2. Create `/opt/wearon/` with user ownership
3. Copy config files from repo
4. Create `.env` from template (DOMAIN pre-filled), pause for operator edit
5. Pull Docker images
6. Run `init-ssl.sh` for certbot
7. Start services via docker compose
8. Wait for health checks (120s max), print URLs

### Idempotent Design

- `mkdir -p` for directory creation
- Skips `.env` creation if file already exists
- Safe to re-run after partial failure

### Architecture References

- ADR-2: Production Docker Compose Orchestration
- ADR-6: Zero-Downtime Deployment Strategy
- FR-7.7: CI/CD MUST automate first deploy

## Dev Agent Record

- **Agent**: Claude Code (Opus)
- **Date**: 2026-02-15
- **Implementation Notes**: Created `scripts/first-deploy.sh` — an 8-step idempotent deployment script. Checks Docker prerequisites, copies configs to `/opt/wearon/`, creates `.env` with DOMAIN pre-filled, pulls images, obtains SSL cert, starts services, and waits for health checks with 120s timeout.

## File List

| File | Action | Description |
|------|--------|-------------|
| `scripts/first-deploy.sh` | Created | First-deploy script for fresh VPS setup |

## Change Log

- Created `scripts/first-deploy.sh` with 8-step deployment flow
- Script is executable (`chmod +x`)
