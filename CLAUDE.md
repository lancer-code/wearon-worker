# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**wearon-worker** is the Python backend worker for the WearOn virtual try-on platform. It runs three services in a single process:

1. **Redis consumer** — BRPOP loop reading generation tasks from `wearon:tasks:generation` (pushed via LPUSH from the Next.js API in the main wearon monorepo)
2. **Celery worker** — Processes generation tasks (download images, call OpenAI GPT Image 1.5, upload results to Supabase Storage)
3. **FastAPI server** — HTTP endpoints for `/health` and `/estimate-body` (size recommendation via MediaPipe pose estimation)

**Tech stack:** Python 3.12, Celery + Redis, FastAPI + Uvicorn, OpenAI API (httpx), Supabase (supabase-py), Pillow, MediaPipe, Pydantic v2, structlog, Docker.

## Commands

```bash
# Local development (without Docker)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py                    # Starts all three services

# Docker development
make dev                          # docker compose up --build (foreground)
make up                           # docker compose up -d --build (detached)
make down                         # docker compose down
make logs                         # docker compose logs -f worker

# Testing
make test                         # python -m pytest tests/ -v
python -m pytest tests/test_consumer.py -v          # Single test file
python -m pytest tests/test_consumer.py::test_name  # Single test

# Docker build
make build                        # docker build -t wearon-worker .
```

## Architecture

### Process Model (`main.py`)

`main.py` is the unified entrypoint. On startup it:
1. Runs `cleanup_stuck_sessions()` — marks any `queued`/`processing` sessions as `failed` and refunds credits
2. Starts Celery as a **subprocess** (`celery -A worker.celery_app worker`)
3. Starts the Redis consumer in a **daemon thread**
4. Starts FastAPI via uvicorn on port 8000 (blocks main thread)
5. On shutdown, terminates the Celery subprocess

### Generation Pipeline

The Next.js API (from the main wearon repo) pushes tasks to Redis via LPUSH. The flow:

1. `worker/consumer.py` — BRPOP reads JSON from `wearon:tasks:generation`, validates with `GenerationTask` Pydantic model, dispatches to Celery via `.delay()`
2. `worker/tasks.py` — `process_generation` Celery task: updates session to `processing`, downloads + resizes images (1024px max), calls OpenAI GPT Image 1.5, uploads result to Supabase Storage, updates session to `completed`. On failure: refunds credits, marks `failed`.
3. `worker/celery_app.py` — Celery config: `acks_late=True`, 300s time limit, 300 req/min rate limit, no result backend.

### B2B vs B2C Channels

Tasks have a `channel` field (`b2b` or `b2c`). This determines:
- **Session table**: `store_generation_sessions` (b2b) vs `generation_sessions` (b2c)
- **Credit ID field**: `store_id` (b2b) vs `user_id` (b2c)
- **Storage path**: `stores/{id}/generated/` (b2b) vs `generated/{id}/` (b2c)

### Size Recommendation (`size_rec/`)

FastAPI endpoint `POST /estimate-body` accepts `{image_url, height_cm}`, downloads the image, runs MediaPipe 33-landmark pose estimation, calculates body measurements, and returns a size recommendation (XS-XXL) with confidence score.

- `size_rec/app.py` — FastAPI app with lifespan (pre-loads MediaPipe model)
- `size_rec/mediapipe_service.py` — Singleton MediaPipe Pose wrapper
- `size_rec/size_calculator.py` — Converts landmarks to measurements and size recommendation
- `size_rec/image_processing.py` — Download + prepare images for pose estimation

### Key Error Handling Patterns

- **429 rate limit**: Celery retries (max 1 retry) with 10s countdown. Session set back to `queued`. Credits are NOT refunded until final failure (prevents double-spend).
- **Moderation block**: OpenAI returns 400 with `moderation_blocked` code. Credits refunded, user-friendly error message stored.
- **All other errors**: No retry. Credits refunded immediately, session marked `failed`.
- **Consumer errors**: 5s sleep backoff to prevent tight-loop on Redis failures.
- **OpenAI retries**: Exponential backoff (2^attempt seconds) for 5xx and transient errors, handled inside `services/openai_client.py`.

## Project Layout

```
main.py              — Unified entrypoint (startup cleanup → Celery → consumer → FastAPI)
config/
  settings.py        — Pydantic Settings (env vars: REDIS_URL, SUPABASE_*, OPENAI_*, WORKER_CONCURRENCY)
  logging_config.py  — structlog JSON formatter
models/
  task_payload.py    — GenerationTask (matches TypeScript queue contract)
  generation.py      — SessionStatus, SessionUpdate
  size_rec.py        — Request/response models for /estimate-body
services/
  openai_client.py   — GPT Image 1.5 via httpx with retries and moderation handling
  supabase_client.py — Lazy singleton supabase-py client (service role key)
  image_processor.py — Download (content-type/size validation, no redirects) + resize to 1024px JPEG
  redis_client.py    — Async Redis health check client
worker/
  celery_app.py      — Celery config (rate limit, acks_late, time limit)
  consumer.py        — BRPOP loop → Pydantic validation → Celery dispatch
  tasks.py           — process_generation task (download → resize → OpenAI → upload → update)
  startup.py         — Cleanup stuck sessions on worker restart
size_rec/
  app.py             — FastAPI app (/estimate-body, /health)
  mediapipe_service.py — MediaPipe Pose singleton
  size_calculator.py — Landmark → measurement → size recommendation
  image_processing.py — Image download + preparation for pose estimation
tests/               — pytest tests (conftest.py adds project root to sys.path)
```

## Cross-Language Queue Contract

Queue key: `wearon:tasks:generation`

The TypeScript side (Next.js API at `packages/api/src/types/queue.ts`) serializes to snake_case JSON before LPUSH. The Python `GenerationTask` model must match this contract exactly:

```python
class GenerationTask(BaseModel):
    task_id: str
    channel: Literal['b2b', 'b2c']
    store_id: str | None = None
    user_id: str | None = None
    session_id: str
    image_urls: list[str]
    prompt: str
    request_id: str          # Correlation ID — include in all log lines
    version: int = 1
    created_at: str
```

## Environment Variables

Managed via pydantic-settings (`config/settings.py`), loaded from `.env` file. See `.env.example` for all required values.

| Variable | Required | Description |
|----------|----------|-------------|
| `REDIS_URL` | Yes | Redis connection string |
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Supabase service role key (server-side only) |
| `OPENAI_API_KEY` | Yes | OpenAI API key for GPT Image 1.5 |
| `OPENAI_MAX_RETRIES` | No | Retry count for OpenAI API (default: 3) |
| `WORKER_CONCURRENCY` | No | Celery worker concurrency (default: 5) |

## CI/CD

GitHub Actions (`.github/workflows/ci-cd.yml`):
- **PR to main**: Runs pytest + validates Docker build (uses placeholder env vars for pydantic-settings import)
- **Push to main**: Builds Docker image, pushes to GHCR (`ghcr.io/lancer-code/wearon-worker`), deploys to VPS via SSH

System dependencies required for tests and runtime: `libgl1`, `libglib2.0-0` (for MediaPipe).

## Testing

Tests mock all external services (OpenAI, Supabase, Redis). The `conftest.py` adds the project root to `sys.path`. Test files:
- `test_consumer.py` — Valid task dispatch, invalid JSON skip
- `test_task_payload.py` — B2B/B2C validation, invalid channel rejection
- `test_tasks.py` — Payload roundtrip serialization
- `test_size_rec_app.py`, `test_mediapipe_service.py`, `test_size_calculator.py` — Size recommendation tests

## Conventions

- **Logging**: Use `structlog.get_logger()` with `.bind(request_id=...)` for correlation. All logs are JSON.
- **Async in Celery**: Celery tasks are sync. Async functions (image download, OpenAI calls) run via `asyncio.new_event_loop()` + `loop.run_until_complete()`, with `loop.close()` in `finally`.
- **Singletons**: Both `MediaPipeService` and Supabase client use lazy singleton pattern.
- **HTTP client**: Use `httpx` (async) for image downloads and OpenAI calls. Image downloads disable redirects for SSRF protection.
