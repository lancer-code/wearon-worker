import asyncio

import structlog

from models.task_payload import GenerationTask
from services.image_processor import download_and_resize
from services.openai_client import OpenAIImageError, generate_tryon
from services.supabase_client import get_supabase
from worker.celery_app import celery_app

logger = structlog.get_logger()


def _get_session_table(channel: str) -> str:
    return 'store_generation_sessions' if channel == 'b2b' else 'generation_sessions'


def _get_credit_id_field(channel: str) -> str:
    return 'store_id' if channel == 'b2b' else 'user_id'


def _get_owner_id(task: GenerationTask) -> str | None:
    return task.store_id if task.channel == 'b2b' else task.user_id


@celery_app.task(name='process_generation', bind=True, max_retries=1)
def process_generation(self, task_data: dict) -> None:  # type: ignore[no-untyped-def]
    """Process a virtual try-on generation task.

    1. Update session status to 'processing'
    2. Download and resize images
    3. Call OpenAI GPT Image 1.5
    4. Upload result to Supabase Storage
    5. Update session to 'completed'
    On failure: refund credits, mark 'failed'
    """
    task = GenerationTask(**task_data)
    log = logger.bind(
        request_id=task.request_id,
        session_id=task.session_id,
        channel=task.channel,
    )
    supabase = get_supabase()
    session_table = _get_session_table(task.channel)

    try:
        # 1. Mark as processing
        supabase.table(session_table).update({'status': 'processing'}).eq(
            'id', task.session_id
        ).execute()
        log.info('generation_processing')

        # 2. Download and resize images
        loop = asyncio.new_event_loop()
        try:
            image_buffers: list[tuple[str, bytes]] = []
            for i, url in enumerate(task.image_urls):
                name = 'model' if i == 0 else f'image_{i}'
                buf = loop.run_until_complete(download_and_resize(url, name))
                image_buffers.append((f'{name}.jpg', buf))

            # 3. Call OpenAI
            result_bytes = loop.run_until_complete(
                generate_tryon(
                    image_buffers=image_buffers,
                    prompt=task.prompt,
                    request_id=task.request_id,
                )
            )
        finally:
            loop.close()

        # 4. Upload result to Supabase Storage
        owner_id = _get_owner_id(task)
        if task.channel == 'b2b':
            storage_path = f'stores/{owner_id}/generated/{task.session_id}.jpg'
        else:
            storage_path = f'generated/{owner_id}/{task.session_id}.jpg'

        supabase.storage.from_('images').upload(
            storage_path,
            result_bytes,
            {'content-type': 'image/jpeg'},
        )

        # Create signed URL (6 hour expiry)
        signed = supabase.storage.from_('images').create_signed_url(storage_path, 21600)
        signed_url = signed.get('signedURL', '')

        # 5. Mark completed
        supabase.table(session_table).update(
            {'status': 'completed', 'result_image_url': signed_url}
        ).eq('id', task.session_id).execute()

        log.info('generation_completed')

    except OpenAIImageError as exc:
        log.warn('generation_failed', error=str(exc), moderation=exc.is_moderation_error)

        # Retry on rate limit (429) before refunding — avoids double-spend
        if exc.status_code == 429 and self.request.retries < self.max_retries:
            supabase.table(session_table).update(
                {'status': 'queued', 'error_message': 'Rate limited, retrying...'}
            ).eq('id', task.session_id).execute()
            raise self.retry(countdown=10)

        # Final failure — refund and mark failed
        _refund_credit(task, log)

        supabase.table(session_table).update(
            {'status': 'failed', 'error_message': str(exc)}
        ).eq('id', task.session_id).execute()

    except Exception as exc:
        log.exception('generation_error', error=str(exc))

        _refund_credit(task, log)

        supabase.table(session_table).update(
            {'status': 'failed', 'error_message': 'Internal error during generation'}
        ).eq('id', task.session_id).execute()


def _refund_credit(task: GenerationTask, log: structlog.stdlib.BoundLogger) -> None:
    """Refund 1 credit to the task owner."""
    try:
        supabase = get_supabase()
        id_field = _get_credit_id_field(task.channel)
        owner_id = _get_owner_id(task)
        if owner_id:
            supabase.rpc('refund_credits', {f'p_{id_field}': owner_id, 'p_amount': 1}).execute()
            log.info('credit_refunded', owner_id=owner_id)
    except Exception:
        log.exception('refund_error')
