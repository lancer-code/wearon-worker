# Edge Cases & Error Handling Review

Date: 2026-02-15
Scope: Runtime services, workers, deploy scripts, CI workflow, and test coverage in this repository.
Reviewer: Senior Developer Review (AI)

## Method

- Performed static review of `main.py`, `worker/*`, `services/*`, `size_rec/*`, `scripts/*`, `.github/workflows/ci-cd.yml`, and related models/tests.
- Focused on unhandled exceptions, edge-case logic holes, misleading error mapping, and operational failure paths.

## Findings (Ordered by Severity)

### 1) CRITICAL: Invalid task payload can bypass task error handling entirely
- Evidence: `worker/tasks.py:37` parses `GenerationTask(**task_data)` before entering the main `try` block.
- Why it matters: malformed task payloads raise before status updates/refunds/failure marking, causing silent drops and inconsistent session state.
- Recommended fix: move payload parsing inside protected block and on validation failure update session to failed (if session id available) with explicit error.

### 2) CRITICAL: Channel ownership constraints are not enforced at model level
- Evidence: `models/task_payload.py:14`, `models/task_payload.py:15`, `models/task_payload.py:17`.
- Why it matters: `b2b` can arrive without `store_id` and `b2c` without `user_id`; `worker/tasks.py:74` then builds storage paths with `None` and refund logic may skip (`worker/tasks.py:130`).
- Recommended fix: add cross-field validation rules:
  - `channel=b2b` => `store_id` required, `user_id` forbidden.
  - `channel=b2c` => `user_id` required, `store_id` forbidden.
  - `image_urls` must be non-empty.

### 3) HIGH: Startup cleanup may incorrectly fail/refund legitimate queued work
- Evidence: `worker/startup.py:23` includes both `queued` and `processing` for forced failure/refund.
- Why it matters: queued jobs that are still valid can be marked failed/refunded at startup, then processed later if still in Redis, causing credit inconsistency and state churn.
- Recommended fix: only auto-recover `processing` sessions (or apply age threshold + queue membership check before refunding `queued`).

### 4) HIGH: CI deploy health check uses `curl` inside worker container that does not include curl
- Evidence: `.github/workflows/ci-cd.yml:122`, `Dockerfile:18`-`Dockerfile:27` (no curl installation).
- Why it matters: deploy health verification can fail even when service is healthy, blocking releases.
- Recommended fix: replace with Python-based check (consistent with compose healthcheck), e.g. `python -c "import urllib.request..."`.

### 5) HIGH: First-deploy script is not truly idempotent when rerun from target host path
- Evidence: `scripts/first-deploy.sh:38`-`scripts/first-deploy.sh:41` copies source directories into `/opt/wearon`; script itself is copied into that same path.
- Why it matters: reruns from `/opt/wearon` can copy directories into themselves and fail mid-deploy.
- Recommended fix: detect when source and target are identical and skip copy, or use rsync with excludes and safe overwrite semantics.

### 6) HIGH: SSRF mitigation is incomplete (redirects blocked, but internal host access still allowed)
- Evidence: `services/image_processor.py:18`, `size_rec/image_processing.py:21` set `follow_redirects=False` but do not validate destination host/IP.
- Why it matters: attacker can supply direct URLs to internal/private endpoints (metadata service, RFC1918 hosts), enabling SSRF.
- Recommended fix: resolve and block private/link-local/loopback ranges and optionally enforce allowlist domains.

### 7) HIGH: Model-not-loaded condition is reported to API caller as 422 user input issue
- Evidence: `size_rec/mediapipe_service.py:50` raises `PoseEstimationError('MediaPipe model is not loaded')`; `size_rec/app.py:62`-`size_rec/app.py:64` maps all `PoseEstimationError` to HTTP 422.
- Why it matters: internal service failure appears as user fault, hindering alerting and client behavior.
- Recommended fix: distinguish “model unavailable” from “no pose detected”; return 503/500 for internal readiness failures.

### 8) MEDIUM: Main shutdown path can raise on Celery termination timeout
- Evidence: `main.py:69` uses `celery_proc.wait(timeout=10)` without timeout handling.
- Why it matters: unhandled timeout on shutdown can leave zombie worker process or crash finalizer path.
- Recommended fix: catch `subprocess.TimeoutExpired`, log, then force kill and wait.

### 9) MEDIUM: Consumer thread health is not supervised
- Evidence: `main.py:57` starts daemon consumer thread and never checks liveness.
- Why it matters: thread can die silently while process still serves API and appears up, causing stalled queue processing.
- Recommended fix: add watchdog/liveness check and include consumer/celery state in health endpoint.

### 10) MEDIUM: First-deploy health polling parser is brittle across compose output formats
- Evidence: `scripts/first-deploy.sh:82`-`scripts/first-deploy.sh:83` assumes stream parsing behavior for `docker compose ps --format json`.
- Why it matters: compose output format differences can cause false negatives and unnecessary timeout warnings.
- Recommended fix: parse with `docker compose ps --format json | python -c 'json.load(...)'` robustly for array shape.

### 11) MEDIUM: OpenAI 400 handling assumes JSON body and retries on parsing/programming errors
- Evidence: `services/openai_client.py:84` calls `response.json()` inside 400 handling; broad exception retry at `services/openai_client.py:118`.
- Why it matters: non-JSON 4xx responses and local logic errors get retried as transient, increasing latency and noise.
- Recommended fix: guard JSON decode separately; retry only network/5xx classes; fail fast on deterministic client/schema errors.

### 12) MEDIUM: Renewal script may fail in cron due interactive exec assumptions
- Evidence: `scripts/renew-certs.sh:18` uses `docker compose exec nginx ...` without `-T`.
- Why it matters: cron non-interactive context can fail depending on docker/compose behavior.
- Recommended fix: use `docker compose exec -T nginx ...` and handle container-not-running case with clear exit code/log.

### 13) LOW: Refund failures are logged but not surfaced for compensating action
- Evidence: `worker/tasks.py:133`-`worker/tasks.py:134` swallows refund exception after logging.
- Why it matters: potential long-tail credit mismatches can accumulate without automatic remediation queue.
- Recommended fix: emit structured compensating event/queue for retryable refund reconciliation.

### 14) LOW: Test suite does not cover several high-risk failure paths
- Evidence:
  - No tests for `services/openai_client.py` retry/error classification.
  - No tests for `scripts/first-deploy.sh` and `scripts/renew-certs.sh` behavior.
  - No tests enforcing channel ownership invariants in `models/task_payload.py`.
- Why it matters: regressions in critical error paths likely to go undetected.
- Recommended fix: add targeted unit/integration tests for failure branches and deploy scripts (shellcheck + bats or equivalent).

## Priority Fix Order

1. Fix payload/channel invariants and task failure handling (`models/task_payload.py`, `worker/tasks.py`).
2. Fix deploy reliability (`.github/workflows/ci-cd.yml`, `scripts/first-deploy.sh`, `scripts/renew-certs.sh`).
3. Fix startup cleanup credit safety (`worker/startup.py`).
4. Harden SSRF and service-readiness error mapping (`services/image_processor.py`, `size_rec/image_processing.py`, `size_rec/app.py`).
5. Improve observability/supervision and test coverage for failure paths.
