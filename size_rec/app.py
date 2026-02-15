import hashlib
from contextlib import asynccontextmanager
from uuid import uuid4

import structlog
from fastapi import FastAPI, Header, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator

from models.size_rec import EstimateBodyRequest, EstimateBodyResponse, HealthResponse
from services.redis_client import RedisHealthClient
from size_rec.image_processing import ImageDownloadError, download_and_prepare_image
from size_rec.mediapipe_service import MediaPipeService, PoseEstimationError
from size_rec.size_calculator import calculate_size_recommendation

structlog.configure(processors=[structlog.processors.JSONRenderer()])

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Load once and keep warm in memory for low-latency /estimate-body requests.
    get_mediapipe_service()
    yield


app = FastAPI(title='WearOn Worker Size Recommendation API', lifespan=lifespan)
Instrumentator().instrument(app).expose(app)

_mediapipe_service: MediaPipeService | None = None
_redis_client = RedisHealthClient.from_env()


def get_mediapipe_service() -> MediaPipeService:
    global _mediapipe_service
    if _mediapipe_service is None:
        _mediapipe_service = MediaPipeService.get_instance()
    return _mediapipe_service


@app.post('/estimate-body', response_model=EstimateBodyResponse)
async def estimate_body(
    payload: EstimateBodyRequest,
    x_request_id: str | None = Header(default=None),
) -> EstimateBodyResponse:
    request_id = x_request_id or f'req_{uuid4()}'
    log = structlog.get_logger().bind(request_id=request_id)

    image_hash = hashlib.sha256(str(payload.image_url).encode('utf-8')).hexdigest()[:12]
    log.info('size_rec_request_started', image_url_hash=image_hash, height_cm=payload.height_cm)

    try:
        image_rgb = await download_and_prepare_image(str(payload.image_url), timeout_seconds=5.0)
        landmarks = get_mediapipe_service().extract_landmarks(image_rgb)
        response = calculate_size_recommendation(landmarks, payload.height_cm)
        log.info(
            'size_rec_request_succeeded',
            recommended_size=response.recommended_size,
            confidence=response.confidence,
        )
        return response
    except ImageDownloadError as exc:
        log.warning('size_rec_image_download_failed', error=str(exc))
        raise HTTPException(status_code=400, detail='Invalid or inaccessible image URL') from exc
    except PoseEstimationError as exc:
        log.warning('size_rec_pose_estimation_failed', error=str(exc))
        raise HTTPException(status_code=422, detail='Could not detect full body pose from image') from exc
    except Exception as exc:
        log.error('size_rec_unexpected_error', error=str(exc))
        raise HTTPException(status_code=500, detail='Failed to estimate body measurements') from exc


@app.get('/health', response_model=HealthResponse)
async def health() -> HealthResponse:
    model_loaded = get_mediapipe_service().is_loaded
    redis_connected = await _redis_client.ping()
    status = 'ok' if model_loaded and redis_connected else 'degraded'

    return HealthResponse(
        status=status,
        model_loaded=model_loaded,
        redis_connected=redis_connected,
    )
