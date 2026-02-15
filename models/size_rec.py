from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class EstimateBodyRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')

    image_url: HttpUrl
    height_cm: float = Field(ge=100, le=250)


class Measurements(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')

    chest_cm: float = Field(gt=0)
    waist_cm: float = Field(gt=0)
    hip_cm: float = Field(gt=0)
    shoulder_cm: float = Field(gt=0)


class SizeRange(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')

    lower: Literal['XS', 'S', 'M', 'L', 'XL', 'XXL']
    upper: Literal['XS', 'S', 'M', 'L', 'XL', 'XXL']


class EstimateBodyResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')

    recommended_size: Literal['XS', 'S', 'M', 'L', 'XL', 'XXL']
    measurements: Measurements
    confidence: float = Field(ge=0, le=1)
    body_type: Literal['athletic', 'slim', 'average', 'broad']
    size_range: SizeRange


class HealthResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')

    status: Literal['ok', 'degraded']
    size_rec_model_loaded: bool
    redis_connected: bool
    celery_connected: bool

