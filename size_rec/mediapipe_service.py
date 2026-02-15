from typing import Any, ClassVar

import numpy as np


class PoseEstimationError(Exception):
    pass


class ModelNotLoadedError(PoseEstimationError):
    pass


Landmark = dict[str, float]


class MediaPipeService:
    _instance: ClassVar['MediaPipeService | None'] = None

    def __init__(self) -> None:
        self._pose: Any | None = None
        self._model_loaded = False

        try:
            import mediapipe as mp

            self._pose = mp.solutions.pose.Pose(
                static_image_mode=True,
                model_complexity=1,
                enable_segmentation=False,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            self._model_loaded = True
        except Exception:
            self._pose = None
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
        if not self._model_loaded or self._pose is None:
            raise ModelNotLoadedError('MediaPipe model is not loaded')

        results = self._pose.process(image_rgb)
        source_landmarks = results.pose_world_landmarks or results.pose_landmarks

        if source_landmarks is None:
            raise PoseEstimationError('No pose landmarks detected')

        landmarks: list[Landmark] = []
        for landmark in source_landmarks.landmark:
            landmarks.append(
                {
                    'x': float(landmark.x),
                    'y': float(landmark.y),
                    'z': float(getattr(landmark, 'z', 0.0)),
                    'visibility': float(getattr(landmark, 'visibility', 1.0)),
                }
            )

        if len(landmarks) != 33:
            raise PoseEstimationError(f'Expected 33 landmarks, got {len(landmarks)}')

        return landmarks

