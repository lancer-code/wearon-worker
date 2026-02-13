from celery import Celery

from config.settings import settings

celery_app = Celery(
    'wearon_worker',
    broker=settings.redis_url,
    include=['worker.tasks'],
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=300,
    worker_concurrency=settings.worker_concurrency,
    worker_prefetch_multiplier=1,
    # Global OpenAI rate limit: 300 req/min
    task_default_rate_limit='300/m',
    # No result backend — results go to Supabase
    result_backend=None,
)
