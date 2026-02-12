from size_rec.size_calculator import calculate_size_recommendation


def make_landmarks(visibility: float) -> list[dict[str, float]]:
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


def test_calculate_size_recommendation_returns_definitive_range_for_high_confidence():
    response = calculate_size_recommendation(make_landmarks(visibility=1.0), height_cm=175)

    assert response.confidence >= 0.8
    assert response.size_range.lower == response.recommended_size
    assert response.size_range.upper == response.recommended_size


def test_calculate_size_recommendation_returns_size_range_for_low_confidence():
    response = calculate_size_recommendation(make_landmarks(visibility=0.0), height_cm=175)

    assert response.confidence < 0.8
    assert response.size_range.lower != response.size_range.upper
