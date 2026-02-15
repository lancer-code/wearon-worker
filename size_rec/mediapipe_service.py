import os
from typing import Any, ClassVar

import numpy as np
import structlog

logger = structlog.get_logger()

MODEL_PATH = os.environ.get(
    'MEDIAPIPE_MODEL_PATH',
    os.path.join(os.path.dirname(__file__), '..', 'models', 'pose_landmarker_full.task'),
)


class PoseEstimationError(Exception):
    pass


class ModelNotLoadedError(PoseEstimationError):
    pass


Landmark = dict[str, float]


class MediaPipeService:
    _instance: ClassVar['MediaPipeService | None'] = None

    def __init__(self) -> None:
        self._landmarker: Any | None = None
        self._model_loaded = False

        try:
            import mediapipe as mp

            base_options = mp.tasks.BaseOptions(model_asset_path=MODEL_PATH)
            options = mp.tasks.vision.PoseLandmarkerOptions(
                base_options=base_options,
                running_mode=mp.tasks.vision.RunningMode.IMAGE,
            )
            self._landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)
            self._mp = mp
            self._model_loaded = True
        except Exception as exc:
            logger.error('mediapipe_load_failed', error=str(exc), exc_type=type(exc).__name__)
            self._landmarker = None
            self._model_loaded = False

    @classmethod
    def get_instance(cls) -> 'MediaPipeService':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_for_tests(cls) -> None:
        cls._instance = None

    @property
    def is_loaded(self) -> bool:
        return self._model_loaded

    def extract_landmarks(self, image_rgb: np.ndarray) -> list[Landmark]:
        if not self._model_loaded or self._landmarker is None:
            raise ModelNotLoadedError('MediaPipe model is not loaded')

        mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=image_rgb)
        result = self._landmarker.detect(mp_image)

        if not result.pose_world_landmarks and not result.pose_landmarks:
            raise PoseEstimationError('No pose landmarks detected')

        source = result.pose_world_landmarks[0] if result.pose_world_landmarks else result.pose_landmarks[0]

        landmarks: list[Landmark] = []
        for lm in source:
            landmarks.append(
                {
                    'x': float(lm.x),
                    'y': float(lm.y),
                    'z': float(getattr(lm, 'z', 0.0)),
                    'visibility': float(getattr(lm, 'visibility', 1.0)),
                }
            )

        if len(landmarks) != 33:
            raise PoseEstimationError(f'Expected 33 landmarks, got {len(landmarks)}')

        return landmarks
