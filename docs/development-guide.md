# Development Guide — WearOn Worker

## Prerequisites

- **Python 3.12+** (required by `pyproject.toml`)
- **Docker & Docker Compose** (for containerized development)
- **Redis** (provided via docker-compose or external instance)
- **System libraries**: `libgl1`, `libglib2.0-0` (required by MediaPipe)

## Environment Setup

```bash
# 1. Clone the repository
git clone <repo-url>
cd wearon-worker

# 2. Create environment file
cp .env.example .env
# Edit .env with your actual keys:
#   REDIS_URL, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY
```

### Required Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | Yes | `redis://localhost:6379/0` | Redis connection string |
| `SUPABASE_URL` | Yes | — | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | — | Supabase service role key |
| `OPENAI_API_KEY` | Yes | — | OpenAI API key |
| `OPENAI_MAX_RETRIES` | No | 3 | Retry count for OpenAI API |
| `WORKER_CONCURRENCY` | No | 5 | Celery worker concurrency |
| `REDIS_PASSWORD` | No | `devpassword` | Redis password (local docker-compose only) |

## Running Locally

### Option A: Docker (recommended)

```bash
make dev        # docker compose up --build (foreground)
# or
make up         # docker compose up -d --build (detached)
```

This starts Redis 7-alpine + the worker on port 8000.

### Option B: Without Docker

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install system deps (Ubuntu/Debian)
sudo apt-get install -y libgl1 libglib2.0-0

# Ensure Redis is running, then start
python main.py
```

## Commands Reference

| Command | Description |
|---------|-------------|
| `make dev` | Build and start all containers (foreground) |
| `make up` | Build and start in detached mode |
| `make down` | Stop containers |
| `make logs` | Tail worker logs |
| `make test` | Run pytest (`python -m pytest tests/ -v`) |
| `make build` | Build Docker image only |

## Testing

```bash
# Run all tests
make test

# Run specific test file
python -m pytest tests/test_consumer.py -v

# Run specific test
python -m pytest tests/test_consumer.py::test_name -v
```

All tests mock external services (OpenAI, Supabase, Redis). No real API calls are made during testing.

### Test Files

| File | Coverage |
|------|----------|
| `test_consumer.py` | Redis BRPOP consumer: valid dispatch, invalid JSON |
| `test_task_payload.py` | B2B/B2C validation, channel rejection, default version |
| `test_tasks.py` | Celery task payload serialization roundtrip |
| `test_size_rec_app.py` | FastAPI endpoint tests |
| `test_mediapipe_service.py` | MediaPipe landmark extraction |
| `test_size_calculator.py` | Size calculation and body type logic |

## Code Conventions

- **Logging**: `structlog.get_logger()` with `.bind(request_id=...)` for correlation. All output is JSON.
- **Async in Celery**: Celery tasks are synchronous. Async functions use `asyncio.new_event_loop()` with `loop.close()` in `finally`.
- **Singletons**: `MediaPipeService` and Supabase client use lazy singleton pattern.
- **HTTP client**: `httpx` (async) for all HTTP calls. Image downloads disable redirects (SSRF protection).
- **Type hints**: All functions have type annotations. `mypy --strict` configured in `pyproject.toml`.

## Startup Sequence

When `python main.py` runs:

1. `setup_logging()` — Configure structlog JSON formatter
2. `cleanup_stuck_sessions()` — Mark stuck sessions as failed, refund credits
3. `start_celery_worker()` — Launch Celery as subprocess
4. `start_consumer_thread()` — Start Redis BRPOP consumer in daemon thread
5. `start_fastapi()` — Start uvicorn on port 8000 (blocks main thread)
6. On shutdown: terminate Celery subprocess
