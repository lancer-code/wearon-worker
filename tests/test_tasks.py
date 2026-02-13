from models.task_payload import GenerationTask

SAMPLE_TASK = {
    'task_id': 'test-1',
    'channel': 'b2c',
    'user_id': 'user-1',
    'session_id': 'sess-1',
    'image_urls': ['https://example.com/img.jpg'],
    'prompt': 'Try on this outfit',
    'request_id': 'req_test',
    'version': 1,
    'created_at': '2026-02-09T14:30:00Z',
}


def test_task_payload_roundtrip():
    """Verify GenerationTask serializes/deserializes correctly for Celery."""
    task = GenerationTask(**SAMPLE_TASK)
    dumped = task.model_dump()
    restored = GenerationTask(**dumped)
    assert restored.session_id == 'sess-1'
    assert restored.channel == 'b2c'
