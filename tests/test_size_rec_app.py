import importlib

import numpy as np
import pytest
from fastapi import HTTPException

from models.size_rec import EstimateBodyRequest
from size_rec.image_processing import ImageDownloadError

app_module = importlib.import_module('size_rec.app')


class StubMediaPipeService:
    def __init__(self, landmarks: list[dict[str, float]], loaded: bool = True) -> None:
        self._landmarks = landmarks
        self.is_loaded = loaded

    def extract_landmarks(self, _image_rgb: np.ndarray) -> list[dict[str, float]]:
        return self._landmarks


class StubRedisClient:
    def __init__(self, connected: bool) -> None:
        self._connected = connected

    async def ping(self) -> bool:
        return self._connected


def make_landmarks(visibility: float = 1.0) -> list[dict[str, float]]:
    points: list[dict[str, float]] = []
    for index in range(33):
        points.append(
            {
                'x': 0.5,
                'y': index / 32,
                'z': 0.0,
                'visibility': visibility,
            }
        )

    points[11]['x'] = 0.4
    points[12]['x'] = 0.6
    points[23]['x'] = 0.41
    points[24]['x'] = 0.59
    return points


@pytest.mark.asyncio
async def test_estimate_body_returns_valid_measurements(monkeypatch):
    async def fake_download(_image_url: str, timeout_seconds: float = 5.0):
        assert timeout_seconds == 5.0
        return np.zeros((64, 64, 3), dtype=np.uint8)

    monkeypatch.setattr(app_module, '_mediapipe_service', StubMediaPipeService(make_landmarks()))
    monkeypatch.setattr(app_module, '_redis_client', StubRedisClient(True))
    monkeypatch.setattr(app_module, 'download_and_prepare_image', fake_download)

    payload = EstimateBodyRequest(
        image_url='https://example.com/model.jpg',
        height_cm=175.0,
    )
    response = await app_module.estimate_body(payload, x_request_id='req_test_estimate_body')

    assert response.recommended_size in {'XS', 'S', 'M', 'L', 'XL', 'XXL'}
    assert 0 <= response.confidence <= 1
    assert response.body_type in {'athletic', 'slim', 'average', 'broad'}
    assert response.measurements.chest_cm > 0
    assert response.measurements.waist_cm > 0
    assert response.measurements.hip_cm > 0
    assert response.measurements.shoulder_cm > 0


class StubCeleryControl:
    def __init__(self, alive: bool) -> None:
        self._alive = alive

    def ping(self, timeout: float = 2.0) -> list:
        if self._alive:
            return [{'celery@worker': {'ok': 'pong'}}]
        return []


class StubCeleryApp:
    def __init__(self, alive: bool) -> None:
        self.control = StubCeleryControl(alive)


@pytest.mark.asyncio
async def test_health_endpoint_reports_model_and_redis_status(monkeypatch):
    monkeypatch.setattr(app_module, '_mediapipe_service', StubMediaPipeService(make_landmarks(), loaded=True))
    monkeypatch.setattr(app_module, '_redis_client', StubRedisClient(True))
    monkeypatch.setattr(app_module, 'celery_app', StubCeleryApp(alive=True))

    response = await app_module.health()
    assert response.size_rec_model_loaded is True
    assert response.redis_connected is True
    assert response.celery_connected is True
    assert response.status == 'ok'


@pytest.mark.asyncio
async def test_health_endpoint_reports_degraded_when_dependencies_not_ready(monkeypatch):
    monkeypatch.setattr(app_module, '_mediapipe_service', StubMediaPipeService(make_landmarks(), loaded=False))
    monkeypatch.setattr(app_module, '_redis_client', StubRedisClient(False))
    monkeypatch.setattr(app_module, 'celery_app', StubCeleryApp(alive=False))

    response = await app_module.health()
    assert response.size_rec_model_loaded is False
    assert response.redis_connected is False
    assert response.celery_connected is False
    assert response.status == 'degraded'


@pytest.mark.asyncio
async def test_estimate_body_returns_400_on_image_timeout(monkeypatch):
    async def fake_download(_image_url: str, timeout_seconds: float = 5.0):
        raise ImageDownloadError('Image download timed out or failed')

    monkeypatch.setattr(app_module, '_mediapipe_service', StubMediaPipeService(make_landmarks()))
    monkeypatch.setattr(app_module, '_redis_client', StubRedisClient(True))
    monkeypatch.setattr(app_module, 'download_and_prepare_image', fake_download)

    payload = EstimateBodyRequest(
        image_url='https://example.com/slow-image.jpg',
        height_cm=175.0,
    )

    with pytest.raises(HTTPException) as exc_info:
        await app_module.estimate_body(payload)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == 'Invalid or inaccessible image URL'

