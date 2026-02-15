# Data Models — WearOn Worker

All models use Pydantic v2 with strict validation.

## Generation Pipeline Models

### GenerationTask (`models/task_payload.py`)

Cross-language queue contract matching `packages/api/src/types/queue.ts` from the Next.js monorepo.

```python
class GenerationTask(BaseModel):
    task_id: str
    channel: Literal['b2b', 'b2c']
    store_id: str | None = None
    user_id: str | None = None
    session_id: str
    image_urls: list[str]
    prompt: str
    request_id: str          # Correlation ID for all log lines
    version: int = 1
    created_at: str
```

**Validation rules:**
- `channel` must be exactly `'b2b'` or `'b2c'`
- `store_id` expected when channel is `b2b`
- `user_id` expected when channel is `b2c`
- `request_id` is the correlation ID included in all structured log entries

### SessionStatus (`models/generation.py`)

```python
SessionStatus = Literal['queued', 'processing', 'completed', 'failed']
```

Status machine: `queued` → `processing` → `completed` | `failed`
On 429 retry: `processing` → `queued` → `processing` (avoids credit double-spend)

### SessionUpdate (`models/generation.py`)

```python
class SessionUpdate(BaseModel):
    status: SessionStatus
    result_image_url: str | None = None
    error_message: str | None = None
```

---

## Size Recommendation Models (`models/size_rec.py`)

### EstimateBodyRequest

```python
class EstimateBodyRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')
    image_url: HttpUrl
    height_cm: float = Field(ge=100, le=250)
```

### EstimateBodyResponse

```python
class EstimateBodyResponse(BaseModel):
    recommended_size: Literal['XS', 'S', 'M', 'L', 'XL', 'XXL']
    measurements: Measurements
    confidence: float = Field(ge=0, le=1)
    body_type: Literal['athletic', 'slim', 'average', 'broad']
    size_range: SizeRange
```

### Measurements

```python
class Measurements(BaseModel):
    chest_cm: float = Field(gt=0)
    waist_cm: float = Field(gt=0)
    hip_cm: float = Field(gt=0)
    shoulder_cm: float = Field(gt=0)
```

### SizeRange

```python
class SizeRange(BaseModel):
    lower: Literal['XS', 'S', 'M', 'L', 'XL', 'XXL']
    upper: Literal['XS', 'S', 'M', 'L', 'XL', 'XXL']
```

### HealthResponse

```python
class HealthResponse(BaseModel):
    status: Literal['ok', 'degraded']
    model_loaded: bool
    redis_connected: bool
```

---

## Configuration Model (`config/settings.py`)

```python
class Settings(BaseSettings):
    redis_url: str = 'redis://localhost:6379/0'
    supabase_url: str                    # Required
    supabase_service_role_key: str       # Required
    openai_api_key: str                  # Required
    openai_max_retries: int = 3
    worker_concurrency: int = 5
```

Loaded from `.env` file via pydantic-settings.

---

## Size Calculation Constants (`size_rec/size_calculator.py`)

| Size | Chest Threshold (cm) |
|------|---------------------|
| XS | ≤ 84 |
| S | ≤ 92 |
| M | ≤ 100 |
| L | ≤ 108 |
| XL | ≤ 116 |
| XXL | > 116 |

Body type classification based on shoulder-to-hip ratio:
- **broad**: ratio > 1.12
- **athletic**: ratio > 1.03
- **average**: ratio 0.93-1.03
- **slim**: ratio < 0.93
