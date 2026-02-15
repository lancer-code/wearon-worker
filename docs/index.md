# WearOn Worker — Project Documentation Index

> Generated: 2026-02-15 | Scan Level: Deep | Mode: Initial Scan

## Project Overview

- **Type:** Monolith backend worker service
- **Language:** Python 3.12
- **Architecture:** Multi-service single-process (Redis consumer + Celery + FastAPI)
- **Purpose:** Processes virtual try-on generation tasks and body size recommendations for the WearOn platform

### Quick Reference

- **Entry Point:** `main.py`
- **Port:** 8000 (FastAPI)
- **Queue:** `wearon:tasks:generation` (Redis BRPOP)
- **External APIs:** OpenAI GPT Image 1.5, Supabase (DB + Storage)
- **Tech Stack:** FastAPI, Celery, Redis, httpx, Pydantic v2, MediaPipe, Pillow, structlog

## Generated Documentation

- [Project Overview](./project-overview.md) — Executive summary, tech stack, architecture overview, cross-system integration
- [Architecture](./architecture.md) — System context, component architecture, error handling, security, data flow
- [Source Tree Analysis](./source-tree-analysis.md) — Annotated directory tree, critical folders, integration points
- [API Contracts](./api-contracts.md) — HTTP endpoints, Redis queue contract, Supabase integration
- [Data Models](./data-models.md) — Pydantic models, validation rules, size calculation constants
- [Development Guide](./development-guide.md) — Setup, environment variables, commands, testing, conventions
- [Deployment Guide](./deployment-guide.md) — Docker build, CI/CD pipeline, GitHub secrets, production deploy

## Existing Documentation

- [README.md](../README.md) — Quick start, commands, queue contract, health check
- [CLAUDE.md](../CLAUDE.md) — Comprehensive AI assistant context (architecture, conventions, pipeline details)
- [Story 1.4](./1-4-python-worker-generation-pipeline.md) — Completed implementation record (tasks, acceptance criteria, dev notes)
- [.env.example](../.env.example) — Environment variable template

## Getting Started

```bash
# 1. Copy and configure environment
cp .env.example .env
# Edit .env with REDIS_URL, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY

# 2. Start with Docker (recommended)
make dev

# 3. Or run locally
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py

# 4. Health check
curl http://localhost:8000/health

# 5. Run tests
make test
```

## Key Concepts

| Concept | Location | Description |
|---------|----------|-------------|
| Generation Pipeline | `worker/tasks.py` | Download → Resize → OpenAI → Upload → Update session |
| Redis Queue Contract | `models/task_payload.py` | Must match TypeScript `GenerationTaskPayload` |
| B2B vs B2C | `worker/tasks.py` | Channel determines session table, credit field, storage path |
| Size Recommendation | `size_rec/` | MediaPipe 33-landmark pose → measurements → size (XS-XXL) |
| Startup Cleanup | `worker/startup.py` | Marks stuck sessions as failed, refunds credits |
| Error Strategy | `services/openai_client.py` | 429 → retry, moderation → refund, others → fail immediately |
