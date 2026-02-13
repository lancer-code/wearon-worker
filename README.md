# wearon-worker

Python worker for the WearOn virtual try-on platform. Consumes generation tasks from Redis, processes them via OpenAI GPT Image 1.5, and provides size recommendations via MediaPipe.

## Architecture

- **Redis consumer** — BRPOP loop on `wearon:tasks:generation` (matches LPUSH from Next.js API)
- **Celery** — Task execution with rate limiting (300 req/min OpenAI) and retries
- **FastAPI** — HTTP server for `/health` and `/estimate-body` endpoints
- **MediaPipe** — 33-landmark pose estimation for size recommendations

## Quick Start

```bash
# 1. Copy env file
cp .env.example .env
# Edit .env with your keys

# 2. Start Redis + worker
make dev
```

This runs `docker compose up --build` which starts:
- **redis** — Redis 7 Alpine with password auth
- **worker** — Python consumer + Celery + FastAPI on port 8000

## Local Development (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start a local Redis or point REDIS_URL to your instance
python main.py
```

## Commands

| Command | Description |
|---------|-------------|
| `make dev` | Build and start all containers (foreground) |
| `make up` | Build and start in detached mode |
| `make down` | Stop containers |
| `make logs` | Tail worker logs |
| `make test` | Run pytest |
| `make build` | Build Docker image only |

## Testing

```bash
make test
```

## Redis Queue Contract

The Next.js API pushes tasks via LPUSH with snake_case JSON:

```json
{
  "task_id": "uuid",
  "channel": "b2b | b2c",
  "store_id": "...",
  "user_id": "...",
  "session_id": "...",
  "image_urls": ["..."],
  "prompt": "...",
  "request_id": "req_...",
  "version": 1,
  "created_at": "2026-02-09T14:30:00Z"
}
```

Queue key: `wearon:tasks:generation`

## Health Check

```bash
curl http://localhost:8000/health
```

## Production Deployment

Build the Docker image and deploy to any VPS with Docker:

```bash
docker build -t wearon-worker .
docker run -d --env-file .env -p 8000:8000 wearon-worker
```

Run Redis alongside it (or use the same `docker-compose.yml`):

```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine redis-server --requirepass YOUR_PASSWORD
```

Set `REDIS_URL` in the Vercel web app to point to the VPS Redis endpoint.
