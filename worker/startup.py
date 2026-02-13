import structlog

from services.supabase_client import get_supabase

logger = structlog.get_logger()


def cleanup_stuck_sessions() -> None:
    """Clean up sessions stuck in 'processing' or 'queued' status from previous runs.

    Refunds credits and marks sessions as failed. Runs once on worker startup.
    """
    supabase = get_supabase()

    for table, id_field in [
        ('generation_sessions', 'user_id'),
        ('store_generation_sessions', 'store_id'),
    ]:
        try:
            result = (
                supabase.table(table)
                .select('id, ' + id_field)
                .in_('status', ['queued', 'processing'])
                .execute()
            )
            stuck = result.data or []

            if not stuck:
                continue

            logger.info('cleanup_stuck_sessions', table=table, count=len(stuck))

            for session in stuck:
                session_id = session['id']

                # Mark session as failed
                supabase.table(table).update(
                    {'status': 'failed', 'error_message': 'Worker restarted — job did not complete'}
                ).eq('id', session_id).execute()

                # Refund credit
                owner_id = session.get(id_field)
                if owner_id:
                    supabase.rpc('refund_credits', {'p_' + id_field: owner_id, 'p_amount': 1}).execute()

                logger.info('session_cleaned', session_id=session_id, table=table)

        except Exception:
            logger.exception('cleanup_error', table=table)
