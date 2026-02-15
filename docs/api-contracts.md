# API Contracts — WearOn Worker

## HTTP Endpoints (FastAPI)

Base URL: `http://localhost:8000`

### POST /estimate-body

Body size recommendation using MediaPipe pose estimation.

**Request:**
```json
{
  "image_url": "https://example.com/photo.jpg",
  "height_cm": 175.0
}
```

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `image_url` | HttpUrl | Required, valid URL | Full-body photo URL |
| `height_cm` | float | 100-250 | User's height in centimeters |

**Response (200):**
```json
{
  "recommended_size": "M",
  "measurements": {
    "chest_cm": 96.5,
    "waist_cm": 82.3,
    "hip_cm": 98.1,
    "shoulder_cm": 44.2
  },
  "confidence": 0.847,
  "body_type": "athletic",
  "size_range": {
    "lower": "M",
    "upper": "M"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `recommended_size` | XS/S/M/L/XL/XXL | Best-fit size |
| `measurements` | object | Estimated body measurements in cm |
| `confidence` | float (0-1) | Prediction confidence score |
| `body_type` | athletic/slim/average/broad | Detected body type |
| `size_range` | object | Size range (narrows with higher confidence) |

**Error Responses:**
| Status | Condition | Detail |
|--------|-----------|--------|
| 400 | Invalid/inaccessible image | "Invalid or inaccessible image URL" |
| 422 | Pose not detected | "Could not detect full body pose from image" |
| 500 | Internal error | "Failed to estimate body measurements" |

**Headers:** `X-Request-Id` (optional) — correlation ID for logging.

---

### GET /health

Health check endpoint.

**Response (200):**
```json
{
  "status": "ok",
  "model_loaded": true,
  "redis_connected": true
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | "ok" / "degraded" | Overall health ("ok" only when both checks pass) |
| `model_loaded` | boolean | MediaPipe model initialized |
| `redis_connected` | boolean | Redis ping succeeded |

---

## Redis Queue Contract (Inbound)

Queue key: `wearon:tasks:generation`
Protocol: LPUSH (producer, Next.js) / BRPOP (consumer, this worker)

**Task Payload:**
```json
{
  "task_id": "uuid",
  "channel": "b2b",
  "store_id": "store-uuid",
  "user_id": null,
  "session_id": "session-uuid",
  "image_urls": ["https://signed-url-1", "https://signed-url-2"],
  "prompt": "Virtual try-on: place this outfit on the person",
  "request_id": "req_abc123",
  "version": 1,
  "created_at": "2026-02-09T14:30:00Z"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `task_id` | str | Yes | Unique task identifier |
| `channel` | "b2b" / "b2c" | Yes | Determines session table and storage path |
| `store_id` | str / null | B2B only | Store identifier for B2B channel |
| `user_id` | str / null | B2C only | User identifier for B2C channel |
| `session_id` | str | Yes | Generation session ID in Supabase |
| `image_urls` | list[str] | Yes | Signed download URLs for input images |
| `prompt` | str | Yes | Generation prompt for OpenAI |
| `request_id` | str | Yes | Correlation ID (included in all logs) |
| `version` | int | No (default: 1) | Payload version |
| `created_at` | str | Yes | ISO 8601 timestamp |

---

## Supabase Integration (Outbound)

### Session Status Updates

Tables: `generation_sessions` (B2C) / `store_generation_sessions` (B2B)

Status transitions: `queued` → `processing` → `completed` / `failed`

### Storage Uploads

Bucket: `images`
- B2B path: `stores/{store_id}/generated/{session_id}.jpg`
- B2C path: `generated/{user_id}/{session_id}.jpg`
- Signed URL expiry: 6 hours (21600 seconds)

### Credit Operations (via RPC)

- `refund_credits(p_user_id/p_store_id, p_amount)` — Refunds credits on failure
