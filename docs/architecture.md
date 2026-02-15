# Architecture — WearOn Worker

## Executive Summary

wearon-worker is a Python backend service that processes virtual try-on image generation tasks and provides body size recommendations. It runs three co-located services in a single process: a Redis BRPOP consumer, a Celery task worker, and a FastAPI HTTP server.

## Architecture Pattern

**Multi-service single-process worker** with task queue pattern.

This is not a microservice — it is a single deployable unit that runs three logical services:

1. **Redis Consumer** — Event-driven queue reader (BRPOP blocking pop)
2. **Celery Worker** — Task execution engine with rate limiting and retries
3. **FastAPI Server** — Synchronous HTTP API for health checks and size recommendations

The process model is orchestrated by `main.py` which starts each service in sequence: cleanup → Celery subprocess → consumer daemon thread → FastAPI (blocks main thread).

## System Context

```
┌─────────────┐     LPUSH      ┌─────────────────────────────────┐
│  Next.js    │ ──────────────→│         wearon-worker            │
│  Frontend   │                │                                   │
│  (API)      │                │  ┌──────────┐  ┌──────────────┐  │
└─────────────┘                │  │  Redis    │→│  Celery      │  │
                               │  │  Consumer │  │  Tasks       │  │
                               │  └──────────┘  └──────┬───────┘  │
                               │                       │          │
                               │  ┌──────────────┐     │          │
                               │  │  FastAPI      │     │          │
                               │  │  /health      │     │          │
                               │  │  /estimate-   │     │          │
                               │  │   body        │     │          │
                               │  └──────────────┘     │          │
                               └───────────────────────┼──────────┘
                                                       │
                              ┌─────────────┐          │         ┌──────────┐
                              │  Supabase   │←─────────┘────────→│  OpenAI  │
                              │  DB/Storage │                    │  GPT     │
                              └─────────────┘                    │  Image   │
                                                                 └──────────┘
```

## Component Architecture

### Config Layer (`config/`)

- `settings.py` — Pydantic Settings loading from `.env` file. Single `settings` instance used throughout.
- `logging_config.py` — structlog JSON formatter. Called once at startup.

### Models Layer (`models/`)

Pure data validation, no business logic:
- `task_payload.py` — `GenerationTask` cross-language contract
- `generation.py` — `SessionStatus` literal type, `SessionUpdate` model
- `size_rec.py` — Request/response models for size recommendation API

### Services Layer (`services/`)

External integration clients:
- `openai_client.py` — `generate_tryon()` async function. Sends images to GPT Image 1.5 `/images/edits`. Handles base64 response, moderation blocks (400), rate limits (429), server errors (5xx) with exponential backoff.
- `supabase_client.py` — Lazy singleton `get_supabase()`. Uses service role key for full database access.
- `image_processor.py` — `download_and_resize()` downloads images via httpx (SSRF protection: no redirects, content-type validation, 10MB limit), resizes to 1024px max JPEG.
- `redis_client.py` — Async Redis health check for `/health` endpoint.

### Worker Layer (`worker/`)

Task processing pipeline:
- `celery_app.py` — Celery configuration: `acks_late=True`, 300s time limit, 300/m rate limit, no result backend.
- `consumer.py` — BRPOP loop reading from `wearon:tasks:generation`. Validates JSON → Pydantic → dispatches to Celery via `.delay()`. 5s backoff on errors.
- `tasks.py` — `process_generation` Celery task: mark processing → download images → resize → call OpenAI → upload to Supabase Storage → create signed URL → mark completed. On failure: refund credits via `refund_credits` RPC.
- `startup.py` — `cleanup_stuck_sessions()` runs on startup. Finds queued/processing sessions, marks failed, refunds credits.

### Size Recommendation Layer (`size_rec/`)

Independent FastAPI application:
- `app.py` — FastAPI with lifespan (pre-loads MediaPipe). Two endpoints: `POST /estimate-body`, `GET /health`.
- `mediapipe_service.py` — Singleton MediaPipe Pose wrapper. Extracts 33 landmarks from full-body images.
- `size_calculator.py` — Converts 3D landmarks to body measurements using height calibration. Returns size (XS-XXL), confidence, body type.
- `image_processing.py` — Downloads and prepares images for pose estimation.

## Error Handling Strategy

| Error Type | Behavior | Credits |
|-----------|----------|---------|
| **429 Rate Limit** | Celery retry (max 1), session → `queued` | NOT refunded until final failure |
| **400 Moderation Block** | Immediate fail, user-friendly message | Refunded |
| **5xx Server Error** | Exponential backoff retry in OpenAI client | Refunded on final failure |
| **All Other Errors** | No retry, session → `failed` | Refunded immediately |
| **Consumer Errors** | 5s sleep backoff, continue loop | N/A |
| **Stuck Sessions** | Cleanup on startup | Refunded |

## Security Measures

- **SSRF Protection**: Image downloads disable HTTP redirects, validate `image/*` content-type
- **Size Limits**: 10MB max per downloaded image
- **Rate Limiting**: 300 requests/minute to OpenAI API via Celery `task_default_rate_limit`
- **Secret Management**: `.env` file excluded from Docker image via `.dockerignore`
- **Service Role Key**: Supabase accessed with service role (server-side only, never exposed)
- **Correlation IDs**: `request_id` propagated through all log entries for tracing

## Data Flow

### Generation Pipeline

1. Next.js API → LPUSH task JSON to `wearon:tasks:generation`
2. Consumer → BRPOP reads, validates with Pydantic, dispatches to Celery
3. Celery task → updates session to `processing`
4. Downloads images from Supabase Storage signed URLs
5. Resizes to 1024px max (cost optimization)
6. Sends to OpenAI GPT Image 1.5 `/images/edits`
7. Decodes base64 response
8. Uploads result to Supabase Storage (`images` bucket)
9. Creates 6-hour signed URL
10. Updates session to `completed` with result URL
11. Supabase Realtime notifies frontend

### Size Recommendation

1. Client → POST `/estimate-body` with `{image_url, height_cm}`
2. Download and prepare image
3. MediaPipe extracts 33 body landmarks
4. Calculate measurements using height calibration
5. Map to size (XS-XXL) with confidence score
6. Return recommendation with body type classification

## Deployment Architecture

Single Docker container deployed to VPS via GitHub Actions:
- **CI**: pytest + Docker build validation on PR
- **CD**: Build → GHCR push → SSH deploy on push to main
- **Runtime**: `docker run` with `--restart unless-stopped` and env-file
- **Redis**: Separate container (or docker-compose for local dev)
