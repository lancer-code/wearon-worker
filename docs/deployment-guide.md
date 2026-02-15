# Deployment Guide — WearOn Worker

## Docker Build

Multi-stage Dockerfile optimized for production:

**Builder stage**: Installs Python deps + system build tools
**Runtime stage**: Minimal image with only production deps and `libgl1`, `libglib2.0-0` (MediaPipe)

```bash
docker build -t wearon-worker .
```

### .dockerignore

Excludes: `.git`, `tests/`, `.env`, `docs/`, `.venv/`, IDE files — prevents secrets and unnecessary files from leaking into the image.

## CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/ci-cd.yml`):

### On Pull Request → `test` job

1. Checkout code
2. Setup Python 3.12 with pip cache
3. Install system deps (`libgl1`, `libglib2.0-0`)
4. Install Python deps
5. Run `python -m pytest tests/ -v`
6. Validate Docker build (`docker build -t wearon-worker:test .`)

Uses placeholder env vars for pydantic-settings import (tests mock all externals).

### On Push to Main → `deploy` job

1. Checkout code
2. Setup Docker Buildx
3. Login to GHCR (`ghcr.io`)
4. Build and push image:
   - `ghcr.io/lancer-code/wearon-worker:latest`
   - `ghcr.io/lancer-code/wearon-worker:<commit-sha>`
   - Uses GitHub Actions cache (`type=gha`)
5. SSH deploy to VPS:
   - Pull latest image
   - Stop and remove existing container
   - Start new container with `--restart unless-stopped`
   - Env vars loaded from `/opt/wearon/.env` on VPS

## Required GitHub Secrets

| Secret | Purpose |
|--------|---------|
| `VPS_HOST` | SSH deploy target hostname |
| `VPS_USERNAME` | SSH user |
| `VPS_SSH_KEY` | SSH private key |
| `GITHUB_TOKEN` | Automatic — GHCR authentication |

Application secrets (OPENAI_API_KEY, SUPABASE keys, etc.) are stored on the VPS at `/opt/wearon/.env` — never in GitHub.

## Production Deployment

### Manual Deploy

```bash
# Build and push
docker build -t wearon-worker .
docker run -d \
  --name wearon-worker \
  --restart unless-stopped \
  --env-file /opt/wearon/.env \
  -p 8000:8000 \
  wearon-worker
```

### Redis Setup

```bash
docker run -d \
  --name redis \
  -p 6379:6379 \
  redis:7-alpine redis-server --requirepass YOUR_PASSWORD
```

Set `REDIS_URL` in the Next.js web app to point to the VPS Redis endpoint.

## Health Monitoring

```bash
curl http://localhost:8000/health
# Returns: {"status":"ok","model_loaded":true,"redis_connected":true}
```

- `status: "ok"` — Both MediaPipe model and Redis are operational
- `status: "degraded"` — One or both health checks failing

## Infrastructure Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 1 vCPU | 2+ vCPU |
| RAM | 1 GB | 2+ GB (MediaPipe model + Celery workers) |
| Disk | 1 GB | 5 GB (Docker images + logs) |
| Network | Outbound HTTPS | OpenAI API, Supabase, Redis |
| Port | 8000 | FastAPI HTTP endpoint |
