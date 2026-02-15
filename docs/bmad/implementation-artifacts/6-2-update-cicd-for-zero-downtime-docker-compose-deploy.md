# Story 6.2: Update CI/CD for Zero-Downtime Docker Compose Deploy

Status: review

## Story

As a **platform operator**,
I want **the GitHub Actions pipeline to deploy using Docker Compose with zero downtime**,
So that **code pushes to main don't interrupt active generation tasks**.

## Existing Infrastructure (Already Implemented)

- `.github/workflows/ci-cd.yml` — Current pipeline: test → build → push to GHCR → SSH `docker run`
- Current deploy uses raw `docker pull` + `docker stop` + `docker rm` + `docker run` (causes downtime)
- `docker-compose.prod.yml` — Production compose with health checks (from Epics 1-4)

## Acceptance Criteria

1. **Given** a push to the main branch,
   **When** the deploy job runs,
   **Then** it SSHes to the VPS, pulls the new worker image, and runs `docker compose -f docker-compose.prod.yml up -d --wait` for zero-downtime update.

2. **Given** the new worker container starting,
   **When** Docker Compose validates the health check,
   **Then** the old container is stopped only after the new one is healthy.

3. **Given** tasks in the Redis queue during deployment,
   **When** the old container stops,
   **Then** pending tasks are picked up by the new container after startup cleanup.

## Tasks / Subtasks

- [x] Task 1: Update CI/CD deploy job
  - [x] 1.1 Replace `docker run` commands with Docker Compose commands
  - [x] 1.2 Add `docker compose -f docker-compose.prod.yml pull worker` (pull only worker image)
  - [x] 1.3 Add `docker compose -f docker-compose.prod.yml up -d --wait` (zero-downtime)
  - [x] 1.4 Add health check verification after deploy (curl + JSON status parse)
  - [x] 1.5 Set working directory to `/opt/wearon/` via `cd`

- [x] Task 2: Validation
  - [x] 2.1 All 15 existing tests pass (no regressions)
  - [ ] 2.2 Full deploy validation requires push to main + VPS

## Dev Notes

### Deploy Changes Summary

| Aspect | Before | After |
|--------|--------|-------|
| Method | `docker run` | `docker compose up -d --wait` |
| Downtime | Yes (stop → rm → run) | No (health check before swap) |
| Working dir | N/A | `/opt/wearon` |
| Image pull | All layers | Worker only |
| Health check | None | curl + JSON status check |

### Architecture References

- ADR-6: Zero-Downtime Deployment Strategy
- FR-7.7: CI/CD MUST automate all subsequent updates

## Dev Agent Record

- **Agent**: Claude Code (Opus)
- **Date**: 2026-02-15
- **Implementation Notes**: Replaced raw `docker run` deploy with Docker Compose zero-downtime deploy. New flow: `cd /opt/wearon` → `pull worker` → `up -d --wait` → health check verification. The `--wait` flag ensures compose waits for health checks before marking deploy complete.

## File List

| File | Action | Description |
|------|--------|-------------|
| `.github/workflows/ci-cd.yml` | Modified | Replaced docker run deploy with docker compose zero-downtime deploy |

## Change Log

- Replaced `docker stop/rm/run` deploy with `docker compose pull worker && up -d --wait`
- Added post-deploy health check verification via curl
- Set working directory to `/opt/wearon/`
