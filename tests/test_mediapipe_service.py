from size_rec.mediapipe_service import MediaPipeService


def test_mediapipe_service_is_singleton(monkeypatch):
    MediaPipeService.reset_for_tests()
    init_calls = {'count': 0}

    def fake_init(self):
        init_calls['count'] += 1
        self._pose = object()
        self._model_loaded = True

    monkeypatch.setattr(MediaPipeService, '__init__', fake_init)

    first = MediaPipeService.get_instance()
    second = MediaPipeService.get_instance()

    assert first is second
    assert init_calls['count'] == 1

    MediaPipeService.reset_for_tests()
