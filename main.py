import signal
import subprocess
import sys
import threading

import structlog
import uvicorn

from config.logging_config import setup_logging
from config.settings import settings
from worker.consumer import run_consumer
from worker.startup import cleanup_stuck_sessions

setup_logging()
logger = structlog.get_logger()

_shutdown = threading.Event()


def _signal_handler(sig: int, frame: object) -> None:
    logger.info('shutdown_signal', signal=sig)
    _shutdown.set()


def start_celery_worker() -> subprocess.Popen:  # type: ignore[type-arg]
    """Start Celery worker as a subprocess."""
    cmd = [
        sys.executable, '-m', 'celery',
        '-A', 'worker.celery_app',
        'worker',
        '--loglevel=info',
        f'--concurrency={settings.worker_concurrency}',
    ]
    return subprocess.Popen(cmd)


def start_consumer_thread() -> threading.Thread:
    """Start the Redis BRPOP consumer in a daemon thread."""
    t = threading.Thread(target=run_consumer, daemon=True)
    t.start()
    return t


def start_fastapi() -> None:
    """Start FastAPI via uvicorn (blocks until shutdown)."""
    uvicorn.run(
        'size_rec.app:app',
        host='0.0.0.0',
        port=8000,
        log_level='info',
    )


def main() -> None:
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    logger.info('worker_starting')

    # 1. Cleanup stuck sessions from previous runs
    cleanup_stuck_sessions()

    # 2. Start Celery worker subprocess
    celery_proc = start_celery_worker()
    logger.info('celery_started', pid=celery_proc.pid)

    # 3. Start Redis consumer thread
    consumer_thread = start_consumer_thread()
    logger.info('consumer_started')

    # 4. Start FastAPI (blocks main thread)
    logger.info('fastapi_starting', port=8000)
    try:
        start_fastapi()
    except Exception:
        logger.exception('fastapi_error')
    finally:
        logger.info('shutting_down')
        celery_proc.terminate()
        celery_proc.wait(timeout=10)
        logger.info('worker_stopped')


if __name__ == '__main__':
    main()
