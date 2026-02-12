# wearon-worker

Python worker service for WearOn.

This repo hosts:
- FastAPI endpoint for synchronous size recommendation (`/estimate-body`)
- MediaPipe-based pose extraction service
- Shared worker-side services (Redis health checks, logging, etc.)

## Quick Start

```bash
make dev
```

## Test

```bash
make test
```

