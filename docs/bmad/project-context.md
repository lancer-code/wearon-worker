---
project_name: 'wearon-worker'
user_name: 'ABaid'
date: '2026-02-17'
sections_completed: ['technology_stack']
existing_patterns_found: 12
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

- **Python 3.12** — mypy strict mode enabled (`ignore_missing_imports = true`)
- **Celery ≥5.4.0** with Redis broker — `acks_late=True`, 300s time limit, 300 req/min rate limit, no result backend
- **Redis ≥5.2.0** — dual role: Celery broker + BRPOP consumer queue (`wearon:tasks:generation`)
- **FastAPI ≥0.116.0** + **Uvicorn ≥0.34.0** — HTTP server on port 8000
- **Pydantic v2 ≥2.10.0** + **pydantic-settings ≥2.7.0** — all models & env config
- **OpenAI ≥1.68.0** — GPT Image 1.5 called via raw `httpx` POST to `/v1/images/edits`, NOT via the OpenAI Python SDK client class
- **Supabase ≥2.13.0** — `supabase-py` with service role key (server-side only)
- **MediaPipe ≥0.10.31** — PoseLandmarker full model (float16), pre-downloaded in Docker build
- **Pillow ≥11.0.0** — image processing (resize to 1024px max, JPEG output)
- **httpx ≥0.28.0** — async HTTP client for image downloads and OpenAI API calls
- **structlog ≥24.4.0** — all logging is JSON via `structlog.processors.JSONRenderer()`
- **Docker** — multi-stage build on `python:3.12-slim`, system deps: `libgl1`, `libglib2.0-0`
- **pytest ≥8.3.0** + **pytest-asyncio ≥0.24.0** — `asyncio_mode = "auto"`

## Critical Implementation Rules

### Language-Specific Rules

- **Type annotations required on all functions** — mypy strict mode; use `str | None` union syntax, not `Optional[str]`
- **Async/sync boundary in Celery**: Celery tasks are sync. Wrap async calls with `loop = asyncio.new_event_loop()` → `loop.run_until_complete(...)` → `loop.close()` in `finally` block. Never use `asyncio.run()` inside Celery tasks
- **Imports from project root** — e.g., `from config.settings import settings`, `from models.task_payload import GenerationTask`. No relative imports, no `__init__.py` re-exports
- **Pydantic v2 models** — use `model_dump()` not `.dict()`, `model_validate()` not `.parse_obj()`. Use `BaseModel` for data, `BaseSettings` for env config
- **Custom exceptions carry metadata** — include `status_code`, boolean flags (e.g., `is_moderation_error`) for downstream branching
- **Structured logging only** — `structlog.get_logger()` at module level; use `logger.bind(request_id=...)` for correlation; event names are `snake_case` strings (e.g., `'generation_completed'`)
- **`# type: ignore[...]`** — use sparingly with specific error codes, only for Celery decorator compatibility
