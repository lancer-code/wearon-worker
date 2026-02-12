import math

from models.size_rec import EstimateBodyResponse, Measurements, SizeRange

SIZE_ORDER = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
SIZE_THRESHOLDS = {
    'XS': 84.0,
    'S': 92.0,
    'M': 100.0,
    'L': 108.0,
    'XL': 116.0,
}

LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_HIP = 23
RIGHT_HIP = 24


def _distance(landmarks: list[dict[str, float]], first: int, second: int) -> float:
    a = landmarks[first]
    b = landmarks[second]
    dx = a['x'] - b['x']
    dy = a['y'] - b['y']
    dz = a['z'] - b['z']
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def _choose_size(chest_cm: float, waist_cm: float, hip_cm: float) -> str:
    reference = max(chest_cm, waist_cm, hip_cm)
    for size, threshold in SIZE_THRESHOLDS.items():
        if reference <= threshold:
            return size
    return 'XXL'


def _body_type(shoulder_cm: float, hip_cm: float) -> str:
    ratio = shoulder_cm / max(hip_cm, 1.0)
    if ratio > 1.12:
        return 'broad'
    if ratio > 1.03:
        return 'athletic'
    if ratio < 0.93:
        return 'slim'
    return 'average'


def _size_range(size: str, confidence: float) -> SizeRange:
    index = SIZE_ORDER.index(size)
    if confidence >= 0.8:
        return SizeRange(lower=size, upper=size)

    lower = SIZE_ORDER[max(0, index - 1)]
    upper = SIZE_ORDER[min(len(SIZE_ORDER) - 1, index + 1)]
    return SizeRange(lower=lower, upper=upper)


def calculate_size_recommendation(
    landmarks: list[dict[str, float]],
    height_cm: float,
) -> EstimateBodyResponse:
    min_y = min(landmark['y'] for landmark in landmarks)
    max_y = max(landmark['y'] for landmark in landmarks)
    body_height_units = max(max_y - min_y, 0.25)

    cm_per_unit = height_cm / body_height_units

    shoulder_width_cm = _distance(landmarks, LEFT_SHOULDER, RIGHT_SHOULDER) * cm_per_unit
    hip_width_cm = _distance(landmarks, LEFT_HIP, RIGHT_HIP) * cm_per_unit

    shoulder_cm = _clamp(shoulder_width_cm, 30.0, 65.0)
    chest_cm = _clamp(shoulder_width_cm * 2.15, 70.0, 150.0)
    waist_cm = _clamp(hip_width_cm * 1.55, 58.0, 140.0)
    hip_cm = _clamp(hip_width_cm * 1.95, 70.0, 160.0)

    visibility_avg = sum(landmark.get('visibility', 1.0) for landmark in landmarks) / len(landmarks)
    confidence = _clamp(0.55 + 0.35 * visibility_avg, 0.4, 0.98)

    recommended_size = _choose_size(chest_cm, waist_cm, hip_cm)
    body_type = _body_type(shoulder_cm, hip_cm)
    size_range = _size_range(recommended_size, confidence)

    return EstimateBodyResponse(
        recommended_size=recommended_size,
        measurements=Measurements(
            chest_cm=round(chest_cm, 1),
            waist_cm=round(waist_cm, 1),
            hip_cm=round(hip_cm, 1),
            shoulder_cm=round(shoulder_cm, 1),
        ),
        confidence=round(confidence, 3),
        body_type=body_type,
        size_range=size_range,
    )

