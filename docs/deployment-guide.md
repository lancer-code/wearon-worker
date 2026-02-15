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
3. Login to Docker Hub
4. Build and push image:
   - `knocs/wearon-worker:latest`
   - `knocs/wearon-worker:<commit-sha>`
   - Uses GitHub Actions cache (`type=gha`)
5. Sync config files to VPS (docker-compose, nginx, monitoring, scripts)
6. Write `.env` to VPS from GitHub Secrets
7. Setup VPS prerequisites (Docker, firewall)
8. Deploy: first-deploy detection vs rolling update, SSL cert, health check

## Required GitHub Secrets

| Secret | Purpose |
|--------|---------|
| `VPS_HOST` | SSH deploy target hostname |
| `VPS_USERNAME` | SSH user |
| `VPS_SSH_KEY` | SSH private key |
| `DOCKERHUB_USERNAME` | Docker Hub login |
| `DOCKERHUB_TOKEN` | Docker Hub access token |
| `REDIS_URL` | Upstash Redis connection string (`rediss://...`) |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key |
| `OPENAI_API_KEY` | OpenAI API key |
| `DOMAIN` | Production domain (e.g. `worker.wearonai.com`) |
| `CERTBOT_EMAIL` | Email for SSL certificate |
| `GF_SECURITY_ADMIN_PASSWORD` | Grafana admin password |
| `WHATSAPP_APP_TOKEN` | WhatsApp webhook token |
| `WHATSAPP_RECIPIENT_NUMBER` | WhatsApp alert recipient |

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

### Redis (Upstash)

Production uses Upstash Redis (managed, TLS-enabled). Both the worker and Next.js API connect to the same Upstash instance.

Set `REDIS_URL` to your Upstash `rediss://` connection string in both the worker `.env` and the Next.js web app environment.

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
