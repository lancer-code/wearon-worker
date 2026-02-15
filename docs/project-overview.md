# WearOn Worker — Project Overview

## Purpose

**wearon-worker** is the Python backend worker for the WearOn virtual try-on platform. It processes AI image generation tasks and provides body size recommendations. The Next.js frontend (separate repo) pushes generation jobs to Redis; this worker consumes and processes them.

## Executive Summary

| Field | Value |
|-------|-------|
| **Project Type** | Backend worker service |
| **Language** | Python 3.12 |
| **Architecture** | Multi-service single-process (Redis consumer + Celery + FastAPI) |
| **Repository** | Monolith |
| **Entry Point** | `main.py` |
| **Port** | 8000 (FastAPI) |

## Technology Stack

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| Language | Python | 3.12 | Runtime |
| Web Framework | FastAPI | 0.116+ | HTTP API (`/health`, `/estimate-body`) |
| Task Queue | Celery | 5.4+ | Distributed task processing with rate limiting |
| Queue Broker | Redis | 5.2+ | BRPOP consumer + Celery broker |
| HTTP Client | httpx | 0.28+ | Async HTTP for image downloads and OpenAI API |
| AI Generation | OpenAI GPT Image 1.5 | via httpx | Virtual try-on image generation |
| Pose Estimation | MediaPipe | 0.10+ | 33-landmark body pose detection |
| Image Processing | Pillow | 11+ | Resize, format conversion |
| Database/Storage | Supabase | 2.13+ | Session state, file storage, credit management |
| Data Validation | Pydantic | 2.10+ | Request/response models, settings |
| Logging | structlog | 24.4+ | JSON structured logging |
| Server | uvicorn | 0.34+ | ASGI server |
| Testing | pytest + pytest-asyncio | 8.3+ | Unit tests with async support |
| Container | Docker | Multi-stage | Production deployment |
| CI/CD | GitHub Actions | — | Test → Build → Deploy to VPS |

## Architecture Overview

The worker runs **three services in a single process**, started by `main.py`:

1. **Redis Consumer** (`worker/consumer.py`) — BRPOP loop reading generation tasks from `wearon:tasks:generation` queue. Validates payloads with Pydantic and dispatches to Celery.

2. **Celery Worker** (`worker/tasks.py`) — Processes generation tasks: downloads images, resizes to 1024px, sends to OpenAI GPT Image 1.5, uploads results to Supabase Storage, updates session status. Handles credit refunds on failure.

3. **FastAPI Server** (`size_rec/app.py`) — HTTP endpoints:
   - `POST /estimate-body` — Body size recommendation via MediaPipe pose estimation
   - `GET /health` — Health check (model loaded + Redis connected)

## Cross-System Integration

This worker is part of the larger WearOn platform:

- **Upstream**: Next.js API pushes tasks to Redis via LPUSH (`wearon:tasks:generation`)
- **Downstream**: Results written to Supabase (session updates + Storage uploads)
- **Realtime**: Supabase Realtime notifies the frontend when generation completes
- **Queue Contract**: Python `GenerationTask` Pydantic model must match TypeScript `GenerationTaskPayload`

## B2B vs B2C Channels

Tasks carry a `channel` field (`b2b` or `b2c`) that determines:
- **Session table**: `store_generation_sessions` (b2b) vs `generation_sessions` (b2c)
- **Credit ID field**: `store_id` (b2b) vs `user_id` (b2c)
- **Storage path**: `stores/{id}/generated/` (b2b) vs `generated/{id}/` (b2c)
