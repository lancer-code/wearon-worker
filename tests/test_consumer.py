import json
from unittest.mock import MagicMock, patch

from worker.consumer import QUEUE_KEY


def test_valid_task_dispatched():
    """Verify that a valid JSON task from Redis is dispatched to Celery."""
    task_data = {
        'task_id': 'test-1',
        'channel': 'b2c',
        'user_id': 'user-1',
        'session_id': 'sess-1',
        'image_urls': ['https://example.com/img.jpg'],
        'prompt': 'Try on',
        'request_id': 'req_test',
        'version': 1,
        'created_at': '2026-02-09T14:30:00Z',
    }

    mock_redis = MagicMock()
    # BRPOP returns (key, value) then raises to break loop
    mock_redis.brpop.side_effect = [
        (QUEUE_KEY, json.dumps(task_data)),
        KeyboardInterrupt(),
    ]

    with (
        patch('worker.consumer.get_redis_consumer', return_value=mock_redis),
        patch('worker.consumer.process_generation') as mock_task,
    ):
        from worker.consumer import run_consumer

        run_consumer()
        mock_task.delay.assert_called_once()
        call_args = mock_task.delay.call_args[0][0]
        assert call_args['session_id'] == 'sess-1'


def test_invalid_json_skipped():
    """Verify that malformed JSON is logged and skipped."""
    mock_redis = MagicMock()
    mock_redis.brpop.side_effect = [
        (QUEUE_KEY, 'not valid json{{{'),
        KeyboardInterrupt(),
    ]

    with (
        patch('worker.consumer.get_redis_consumer', return_value=mock_redis),
        patch('worker.consumer.process_generation') as mock_task,
    ):
        from worker.consumer import run_consumer

        run_consumer()
        mock_task.delay.assert_not_called()
