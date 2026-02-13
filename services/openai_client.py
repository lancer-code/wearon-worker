import asyncio
import base64

import httpx
import structlog

from config.settings import settings

logger = structlog.get_logger()

OPENAI_API_BASE_URL = 'https://api.openai.com/v1'

MODERATION_ERROR_MESSAGE = (
    'Your image was flagged by the safety filter. '
    'Please use different images that comply with content guidelines.'
)


class OpenAIImageError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        is_moderation_error: bool = False,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.is_moderation_error = is_moderation_error


async def generate_tryon(
    image_buffers: list[tuple[str, bytes]],
    prompt: str,
    request_id: str,
    quality: str = 'medium',
    size: str = '1024x1536',
) -> bytes:
    """Call OpenAI GPT Image 1.5 /images/edits with multiple images.

    Args:
        image_buffers: List of (filename, image_bytes) tuples.
        prompt: The generation prompt.
        request_id: Correlation ID for logging.
        quality: Image quality setting.
        size: Output image size.

    Returns:
        Raw bytes of the generated image (decoded from base64).

    Raises:
        OpenAIImageError: On API errors including moderation blocks.
    """
    log = logger.bind(request_id=request_id)
    max_retries = settings.openai_max_retries

    for attempt in range(1, max_retries + 1):
        try:
            log.info('openai_attempt', attempt=attempt, max_retries=max_retries)

            files = []
            for filename, buf in image_buffers:
                files.append(('image[]', (filename, buf, 'image/jpeg')))

            data = {
                'model': 'gpt-image-1.5',
                'prompt': prompt,
                'quality': quality,
                'size': size,
                'n': '1',
            }

            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    f'{OPENAI_API_BASE_URL}/images/edits',
                    headers={'Authorization': f'Bearer {settings.openai_api_key}'},
                    data=data,
                    files=files,
                )

            if response.status_code == 429:
                raise OpenAIImageError('Rate limit exceeded', 429)

            if response.status_code == 400:
                body = response.json()
                error_code = body.get('error', {}).get('code', '')
                if error_code == 'moderation_blocked':
                    log.warn('openai_moderation_blocked')
                    raise OpenAIImageError(MODERATION_ERROR_MESSAGE, 400, is_moderation_error=True)

            response.raise_for_status()

            body = response.json()
            b64_data = body['data'][0].get('b64_json')
            if b64_data:
                log.info('openai_success', format='base64')
                return base64.b64decode(b64_data)

            image_url = body['data'][0].get('url')
            if image_url:
                log.info('openai_success', format='url')
                async with httpx.AsyncClient(timeout=30.0) as dl:
                    dl_resp = await dl.get(image_url)
                    dl_resp.raise_for_status()
                    return dl_resp.content

            raise OpenAIImageError('No image data in response')

        except OpenAIImageError:
            raise
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status >= 500 and attempt < max_retries:
                delay = 2 ** attempt
                log.warn('openai_server_error', status=status, retry_delay=delay)
                await asyncio.sleep(delay)
                continue
            raise OpenAIImageError(f'API error: {exc}', status)
        except Exception as exc:
            if attempt < max_retries:
                delay = 2 ** attempt
                log.warn('openai_error', error=str(exc), retry_delay=delay)
                await asyncio.sleep(delay)
                continue
            raise OpenAIImageError(f'Unexpected error: {exc}')

    raise OpenAIImageError('Failed after all retries')
