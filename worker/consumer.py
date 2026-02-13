import json
import os

import redis
import structlog

from models.task_payload import GenerationTask
from worker.tasks import process_generation

logger = structlog.get_logger()

QUEUE_KEY = 'wearon:tasks:generation'
BRPOP_TIMEOUT = 5  # seconds


def get_redis_consumer() -> redis.Redis:
    url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    return redis.from_url(url, decode_responses=True)


def run_consumer() -> None:
    """Blocking Redis BRPOP consumer loop.

    Reads tasks from the same queue that the Next.js API pushes to via LPUSH.
    Validates with Pydantic, then dispatches to the Celery task.
    """
    r = get_redis_consumer()
    logger.info('consumer_started', queue=QUEUE_KEY)

    while True:
        try:
            result = r.brpop(QUEUE_KEY, timeout=BRPOP_TIMEOUT)
            if result is None:
                continue

            _, raw_payload = result

            try:
                data = json.loads(raw_payload)
            except json.JSONDecodeError:
                logger.error('invalid_json', payload=raw_payload[:200])
                continue

            try:
                task = GenerationTask(**data)
            except Exception as exc:
                request_id = data.get('request_id', 'unknown')
                logger.error('invalid_task_payload', request_id=request_id, error=str(exc))
                continue

            logger.info(
                'task_received',
                request_id=task.request_id,
                session_id=task.session_id,
                channel=task.channel,
            )

            # Dispatch to Celery for processing with retries and rate limiting
            process_generation.delay(task.model_dump())

        except KeyboardInterrupt:
            logger.info('consumer_shutdown')
            break
        except Exception:
            logger.exception('consumer_error')
