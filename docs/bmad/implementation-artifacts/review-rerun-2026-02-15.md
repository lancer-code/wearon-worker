# Full Review Rerun (From Scratch)

Date: 2026-02-15
Scope: Stories 2.1 through 6.3 in `docs/bmad/implementation-artifacts`
Reviewer: Senior Developer Review (AI)

## Baseline Constraints

- `docker compose -f docker-compose.prod.yml config` is not reproducible in this workspace because `.env` is missing and required vars are unset.
- Local test execution is not reproducible because `pytest` is not installed in this environment.

## Story-by-Story Findings

### Story 2.1 - Create Production Docker Compose Configuration

- HIGH: Validation claim (`docker compose ... config` successful) is not reproducible in current environment due missing `.env`/required vars.
- MEDIUM: Story file-level traceability is stale versus current compose scope (many additional services now present), reducing audit clarity for Story 2.1 boundaries.
- LOW: No attached validation artifact/log proving AC validation outcomes.

### Story 2.2 - Add Service Restart Policies and Resource Limits

- HIGH: AC for restart within 30 seconds is not runtime-verified; only config-level assertions are documented.
- MEDIUM: Validation language references “both services” while production stack now includes multiple additional services and health dependencies.
- LOW: Resource-limit validation evidence is descriptive only; no preserved command output.

### Story 3.1 - Create Nginx Reverse Proxy Configuration

- HIGH: Story states HTTP-only bootstrap path, but current Nginx template already includes HTTPS termination behavior.
- MEDIUM: Documentation references `nginx/conf.d/default.conf`, while implementation uses `nginx/templates/default.conf.template`.
- MEDIUM: Compose validation claim is not reproducible in current environment without `.env`.

### Story 3.2 - Set Up Let's Encrypt SSL with Auto-Renewal

- HIGH: `init-ssl.sh` requires `CERTBOT_EMAIL` from process env; first-deploy flow can fail if operator only edits `.env` and does not export variable.
- MEDIUM: Runtime certificate issuance/renewal evidence is not attached (no successful certbot run logs linked).
- LOW: Story narrative still depends on assumptions from previous story state and needs synchronization with current deployment flow.

### Story 4.1 - Add Application Metrics to Worker

- HIGH: Story objective text says FastAPI and Celery metrics, but implementation in this story instruments FastAPI only (Celery delegated to 4.2).
- MEDIUM: No direct automated test for `/metrics` payload correctness was added.
- LOW: “All tests pass” claim has no attached output artifact in story record.

### Story 4.2 - Deploy Prometheus and Celery Exporter

- HIGH: Compose validation marked done, but currently not reproducible in this environment due `.env` prerequisites.
- MEDIUM: No preserved evidence that Prometheus targets are actually UP at runtime.
- LOW: Story-level validation remains dependent on infrastructure runtime checks not recorded in artifact.

### Story 4.3 - Deploy Loki and Grafana Alloy for Log Aggregation

- HIGH: AC expects searchable `request_id`, `level`, `event`, but Alloy config only relabels container/service labels and does not explicitly extract JSON fields.
- MEDIUM: No runtime evidence demonstrating end-to-end log shipping and queryability in Grafana.
- LOW: Monitoring images are pinned to `latest`, reducing reproducibility.

### Story 4.4 - Deploy Grafana with Auto-Provisioned Dashboards

- HIGH: Dashboard files use API-wrapper shape (`{"dashboard": ...}`), which can fail file provisioning expectations.
- HIGH: Dashboards reference datasource UIDs (`prometheus`, `loki`) without explicit UID definitions in datasource provisioning.
- MEDIUM: Runtime sub-path validation (`/grafana/` login/assets) has no attached proof artifact.

### Story 5.1 - Deploy WhatsApp Webhook Bridge

- HIGH: AC wording expects Business API credentials, but implementation uses WhatsApp Web QR bridge (`ghcr.io/optiop/grafana-whatsapp-webhook`).
- MEDIUM: Alert delivery SLA (within 60 seconds) remains unverified in story validation.
- LOW: Current path-based token usage in webhook URL increases accidental secret exposure risk in logs/history.

### Story 5.2 - Create Grafana Alert Rules

- HIGH: Worker degraded alert does not identify failing component (Redis vs MediaPipe) as required.
- HIGH: Queue-stalled rule is missing business-hours conditioning required by AC.
- MEDIUM: Story marked done while runtime delivery validation remains pending.

### Story 6.1 - Create First-Deploy Script

- HIGH: `first-deploy.sh` calls `init-ssl.sh`, but certificate email handling can fail without exported env var.
- HIGH: Health wait parser may be brittle across compose JSON output variants.
- MEDIUM: AC requiring final `curl https://{domain}/health` success is not explicitly executed in script.

### Story 6.2 - Update CI/CD for Zero-Downtime Deploy

- HIGH: Post-deploy health check uses host `http://localhost:8000/health` even though port 8000 is not host-exposed in production compose.
- HIGH: Claimed zero downtime is not guaranteed by current single-instance compose update strategy.
- MEDIUM: CI deploy step does not sync compose/config artifacts to `/opt/wearon`, so infra drift can occur.

### Story 6.3 - Add Certificate Renewal Cron Job

- HIGH: Cron command path exists, but runtime validation of cron execution and Nginx reload success is still missing.
- MEDIUM: `docker compose exec` in cron contexts can be fragile without non-interactive safeguards.
- LOW: Story marked done while production validation task remains unresolved.

## Recommended Next Execution Order

1. Fix deploy reliability blockers first: Story 6.1, 6.2, 6.3.
2. Align alerting and WhatsApp delivery semantics: Story 5.1, 5.2.
3. Stabilize monitoring correctness/provisioning: Story 4.4, 4.3, 4.2, 4.1.
4. Cleanup historical documentation drift for Stories 2.x and 3.x.
