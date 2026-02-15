# Story 5.1: Deploy WhatsApp Webhook Bridge

Status: review

## Story

As a **platform operator**,
I want **a grafana-whatsapp-webhook container running alongside Grafana**,
So that **Grafana alerts can be delivered to WhatsApp**.

## Existing Infrastructure (Already Implemented)

- `docker-compose.prod.yml` — Production compose with Grafana (Story 4.4)
- Grafana with provisioning support

## Acceptance Criteria

1. **Given** the grafana-whatsapp-webhook container,
   **When** it starts with WhatsApp Business API credentials,
   **Then** it listens for Grafana webhook payloads on an internal port.

2. **Given** a Grafana alert fires,
   **When** the webhook payload is sent to the WhatsApp bridge,
   **Then** the alert message is delivered to the configured WhatsApp number within 60 seconds.

## Tasks / Subtasks

- [x] Task 1: Add WhatsApp webhook bridge to docker-compose.prod.yml
  - [x] 1.1 Add `whatsapp-webhook` service (image: `ghcr.io/optiop/grafana-whatsapp-webhook:v0.1.5` — pinned version)
  - [x] 1.2 Configure `WHATSAPP_APP_TOKEN` from `.env`
  - [x] 1.3 Internal port only (NOT host-mapped) — port 8080 internal
  - [x] 1.4 Add health check (wget spider), restart: unless-stopped, 0.25 CPU / 128M memory
  - [x] 1.5 Add to `wearon-net` network

- [x] Task 2: Configure Grafana webhook contact point
  - [x] 2.1 Add contact point provisioning in `monitoring/grafana/provisioning/alerting/contactpoints.yml`
  - [x] 2.2 Configure webhook URL pointing to `http://whatsapp-webhook:8080/whatsapp/send/grafana-alert/user/{number}/{token}`
  - [x] 2.3 Set as default notification channel via `monitoring/grafana/provisioning/alerting/policies.yml`

- [x] Task 3: Update .env.example
  - [x] 3.1 Add `WHATSAPP_APP_TOKEN` variable (user-generated random token for auth)
  - [x] 3.2 Add `WHATSAPP_RECIPIENT_NUMBER` variable (target phone number)
  - Note: `WHATSAPP_PHONE_NUMBER_ID` not needed — optiop bridge uses WhatsApp Web protocol, not Business API

- [x] Task 4: Validation
  - [x] 4.1 `docker compose -f docker-compose.prod.yml config` validates successfully
  - [x] 4.2 All 15 existing tests pass (no regressions)
  - [ ] 4.3 Runtime validation (WhatsApp QR pairing + test alert) requires deployment environment

## Dev Notes

### Implementation Decision

Used `ghcr.io/optiop/grafana-whatsapp-webhook:v0.1.5` — the primary community solution for Grafana-to-WhatsApp alerting. This bridge uses the WhatsApp Web protocol (requires QR code pairing on first start) rather than the WhatsApp Business API. The image is pinned to v0.1.5 for security.

### First-Time Setup

After deployment, check container logs for QR code:
```bash
docker compose -f docker-compose.prod.yml logs whatsapp-webhook
```
Scan the QR code with WhatsApp to pair. Session data persists in `whatsapp-data` volume.

### Architecture References

- ADR-5: WhatsApp Alerting via Webhook Bridge
- NFR-4.6: Alert latency < 5 minutes from error to notification
- FR-7.6: Alerts MUST be delivered via WhatsApp

## Dev Agent Record

- **Agent**: Claude Code (Opus)
- **Date**: 2026-02-15
- **Implementation Notes**: Added optiop/grafana-whatsapp-webhook:v0.1.5 to docker-compose.prod.yml with health check, resource limits, and whatsapp-data volume. Created Grafana alerting provisioning (contactpoints.yml + policies.yml) to auto-configure WhatsApp as default notification channel.

## File List

| File | Action | Description |
|------|--------|-------------|
| `docker-compose.prod.yml` | Modified | Added whatsapp-webhook service + whatsapp-data volume |
| `monitoring/grafana/provisioning/alerting/contactpoints.yml` | Created | Grafana webhook contact point for WhatsApp bridge |
| `monitoring/grafana/provisioning/alerting/policies.yml` | Created | Notification policy setting WhatsApp as default |
| `.env.example` | Modified | Added WHATSAPP_APP_TOKEN, WHATSAPP_RECIPIENT_NUMBER |

## Change Log

- Added whatsapp-webhook service to docker-compose.prod.yml (ghcr.io/optiop/grafana-whatsapp-webhook:v0.1.5)
- Created Grafana alerting contact point provisioning (webhook → whatsapp-webhook:8080)
- Created notification policy setting WhatsApp as default receiver
- Added WhatsApp env vars to .env.example
