# Source Tree Analysis — WearOn Worker

## Annotated Directory Tree

```
wearon-worker/
├── main.py                  # ENTRY POINT — Starts all 3 services sequentially
│                            #   1. cleanup_stuck_sessions()
│                            #   2. Celery subprocess
│                            #   3. Redis consumer daemon thread
│                            #   4. FastAPI uvicorn (blocks main thread)
│
├── config/                  # Application configuration
│   ├── __init__.py
│   ├── settings.py          # Pydantic Settings — env vars (REDIS_URL, SUPABASE_*, OPENAI_*)
│   └── logging_config.py    # structlog JSON formatter with ISO timestamps
│
├── models/                  # Pydantic data models
│   ├── __init__.py
│   ├── task_payload.py      # GenerationTask — cross-language Redis queue contract
│   ├── generation.py        # SessionStatus, SessionUpdate — session lifecycle
│   └── size_rec.py          # EstimateBodyRequest/Response, Measurements, HealthResponse
│
├── services/                # External service integrations
│   ├── __init__.py
│   ├── openai_client.py     # GPT Image 1.5 via httpx — retries, moderation handling
│   ├── supabase_client.py   # Lazy singleton supabase-py client (service role key)
│   ├── image_processor.py   # Download (SSRF protection) + resize to 1024px JPEG
│   └── redis_client.py      # Async Redis health check client
│
├── worker/                  # Celery task queue + Redis consumer
│   ├── __init__.py
│   ├── celery_app.py        # Celery config — acks_late, 300s timeout, 300/m rate limit
│   ├── consumer.py          # BRPOP loop → Pydantic validation → Celery dispatch
│   ├── tasks.py             # process_generation — download → resize → OpenAI → upload
│   └── startup.py           # Cleanup stuck sessions on worker restart (refund credits)
│
├── size_rec/                # FastAPI size recommendation service
│   ├── __init__.py
│   ├── app.py               # FastAPI app — /estimate-body, /health endpoints
│   ├── mediapipe_service.py # MediaPipe Pose singleton (33 landmarks)
│   ├── size_calculator.py   # Landmarks → measurements → size recommendation
│   └── image_processing.py  # Image download + preparation for pose estimation
│
├── tests/                   # pytest test suite (mocks all external services)
│   ├── conftest.py          # Adds project root to sys.path
│   ├── test_consumer.py     # Consumer: valid dispatch, invalid JSON skip
│   ├── test_task_payload.py # B2B/B2C validation, invalid channel rejection
│   ├── test_tasks.py        # Payload roundtrip serialization
│   ├── test_size_rec_app.py # FastAPI endpoint tests
│   ├── test_mediapipe_service.py  # MediaPipe landmark extraction
│   └── test_size_calculator.py    # Size calculation logic
│
├── .github/
│   └── workflows/
│       └── ci-cd.yml        # CI/CD: test on PR, deploy on push to main
│
├── Dockerfile               # Multi-stage build (builder → runtime with libgl1, libglib2.0-0)
├── docker-compose.yml       # Redis 7-alpine + worker service
├── Makefile                 # dev, up, down, logs, test, build commands
├── requirements.txt         # Python dependencies
├── pyproject.toml           # Project metadata, pytest config, mypy settings
├── .env.example             # Environment variable template
├── .dockerignore            # Excludes .git, tests, .env, docs
├── .gitignore               # Standard Python patterns
├── README.md                # Project readme
└── CLAUDE.md                # AI assistant context document
```

## Critical Folders

| Folder | Purpose | Key Patterns |
|--------|---------|--------------|
| `config/` | Settings and logging | Pydantic Settings from `.env` |
| `models/` | Data validation contracts | Pydantic v2 models with strict typing |
| `services/` | External integrations | Singleton clients, async HTTP, retry logic |
| `worker/` | Task processing pipeline | Celery + Redis BRPOP consumer |
| `size_rec/` | Body measurement API | FastAPI + MediaPipe + math-based sizing |
| `tests/` | Test suite | pytest with full mocking, no external calls |

## Key Integration Points

| Source | Target | Protocol | Description |
|--------|--------|----------|-------------|
| Next.js API | Redis queue | LPUSH/BRPOP | Generation task dispatch |
| Worker | Supabase DB | REST API | Session status updates, credit refunds |
| Worker | Supabase Storage | REST API | Upload generated images |
| Worker | OpenAI API | HTTP POST | GPT Image 1.5 image edits |
| Frontend | FastAPI | HTTP POST | Size recommendation requests |
