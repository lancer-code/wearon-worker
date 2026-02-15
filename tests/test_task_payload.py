import pytest
from pydantic import ValidationError

from models.task_payload import GenerationTask


def test_valid_b2c_task():
    task = GenerationTask(
        task_id='abc-123',
        channel='b2c',
        user_id='user-1',
        session_id='sess-1',
        image_urls=['https://example.com/img1.jpg'],
        prompt='Try on this outfit',
        request_id='req_abc',
        version=1,
        created_at='2026-02-09T14:30:00Z',
    )
    assert task.channel == 'b2c'
    assert task.store_id is None
    assert task.user_id == 'user-1'


def test_valid_b2b_task():
    task = GenerationTask(
        task_id='abc-456',
        channel='b2b',
        store_id='store-1',
        session_id='sess-2',
        image_urls=['https://example.com/img1.jpg', 'https://example.com/img2.jpg'],
        prompt='Virtual try-on',
        request_id='req_def',
        version=1,
        created_at='2026-02-09T14:30:00Z',
    )
    assert task.channel == 'b2b'
    assert task.store_id == 'store-1'
    assert task.user_id is None


def test_invalid_channel_rejected():
    with pytest.raises(ValidationError):
        GenerationTask(
            task_id='abc-789',
            channel='invalid',
            session_id='sess-3',
            image_urls=[],
            prompt='test',
            request_id='req_ghi',
            created_at='2026-02-09T14:30:00Z',
        )


def test_missing_required_fields():
    with pytest.raises(ValidationError):
        GenerationTask(
            task_id='abc-000',
            channel='b2c',
        )


def test_default_version():
    task = GenerationTask(
        task_id='abc-111',
        channel='b2c',
        user_id='user-1',
        session_id='sess-4',
        image_urls=['https://example.com/img.jpg'],
        prompt='test',
        request_id='req_jkl',
        created_at='2026-02-09T14:30:00Z',
    )
    assert task.version == 1


def test_b2c_requires_user_id():
    with pytest.raises(ValidationError, match='b2c channel requires user_id'):
        GenerationTask(
            task_id='abc-222',
            channel='b2c',
            session_id='sess-5',
            image_urls=['https://example.com/img.jpg'],
            prompt='test',
            request_id='req_mno',
            created_at='2026-02-09T14:30:00Z',
        )


def test_b2b_requires_store_id():
    with pytest.raises(ValidationError, match='b2b channel requires store_id'):
        GenerationTask(
            task_id='abc-333',
            channel='b2b',
            session_id='sess-6',
            image_urls=['https://example.com/img.jpg'],
            prompt='test',
            request_id='req_pqr',
            created_at='2026-02-09T14:30:00Z',
        )


def test_empty_image_urls_rejected():
    with pytest.raises(ValidationError, match='image_urls must not be empty'):
        GenerationTask(
            task_id='abc-444',
            channel='b2c',
            user_id='user-1',
            session_id='sess-7',
            image_urls=[],
            prompt='test',
            request_id='req_stu',
            created_at='2026-02-09T14:30:00Z',
        )
