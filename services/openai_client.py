import asyncio
import base64
from dataclasses import dataclass

import httpx
import structlog

from config.settings import settings

logger = structlog.get_logger()

OPENAI_API_BASE_URL = 'https://api.openai.com/v1'

MODERATION_ERROR_MESSAGE = (
    'Your image was flagged by the safety filter. '
    'Please use different images that comply with content guidelines.'
)

DEFAULT_TRYON_PROMPT = (
    'Virtual try-on: model.jpg is the person photo and image_1.jpg is the clothing photo. '
    'Dress the model in model.jpg with the clothing from image_1.jpg. '
    'Maintain the model\'s original pose, body shape, skin tone, background, and lighting from model.jpg. '
    'The clothing should fit naturally and look realistic.'
)

# GPT Image 1.5 pricing per 1M tokens (USD)
_TEXT_INPUT_PRICE = 5.00
_TEXT_OUTPUT_PRICE = 10.00
_IMAGE_INPUT_PRICE = 8.00
_IMAGE_OUTPUT_PRICE = 32.00


def _estimate_cost(usage: dict) -> float | None:
    """Calculate estimated cost from API usage data."""
    input_details = usage.get('input_tokens_details', {})
    output_details = usage.get('output_tokens_details', {})

    text_in = input_details.get('text_tokens', 0)
    image_in = input_details.get('image_tokens', 0)
    text_out = output_details.get('text_tokens', 0)
    image_out = output_details.get('image_tokens', 0)

    cost = (
        text_in * _TEXT_INPUT_PRICE
        + image_in * _IMAGE_INPUT_PRICE
        + text_out * _TEXT_OUTPUT_PRICE
        + image_out * _IMAGE_OUTPUT_PRICE
    ) / 1_000_000

    return round(cost, 6)


@dataclass
class GenerationResult:
    image_bytes: bytes
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None


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
    prompt: str = '',
    request_id: str = '',
    quality: str = 'medium',
    size: str = '1024x1536',
) -> GenerationResult:
    """Call OpenAI GPT Image 1.5 /images/edits with multiple images.

    Args:
        image_buffers: List of (filename, image_bytes) tuples.
        prompt: The generation prompt.
        request_id: Correlation ID for logging.
        quality: Image quality setting.
        size: Output image size.

    Returns:
        GenerationResult with image bytes and token usage data.

    Raises:
        OpenAIImageError: On API errors including moderation blocks.
    """
    prompt = prompt.strip() if prompt else ''
    if not prompt:
        prompt = DEFAULT_TRYON_PROMPT

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
                try:
                    body = response.json()
                    error_code = body.get('error', {}).get('code', '')
                except (ValueError, KeyError):
                    error_code = ''
                if error_code == 'moderation_blocked':
                    log.warn('openai_moderation_blocked')
                    raise OpenAIImageError(MODERATION_ERROR_MESSAGE, 400, is_moderation_error=True)

            response.raise_for_status()

            body = response.json()

            # Log token usage and estimated cost
            usage = body.get('usage', {})
            if usage:
                input_details = usage.get('input_tokens_details', {})
                output_details = usage.get('output_tokens_details', {})
                cost = _estimate_cost(usage)
                log.info(
                    'openai_usage',
                    total_tokens=usage.get('total_tokens'),
                    input_tokens=usage.get('input_tokens'),
                    output_tokens=usage.get('output_tokens'),
                    text_input_tokens=input_details.get('text_tokens'),
                    image_input_tokens=input_details.get('image_tokens'),
                    text_output_tokens=output_details.get('text_tokens'),
                    image_output_tokens=output_details.get('image_tokens'),
                    estimated_cost_usd=cost,
                )

            usage_result = GenerationResult(
                image_bytes=b'',
                input_tokens=usage.get('input_tokens'),
                output_tokens=usage.get('output_tokens'),
                estimated_cost_usd=cost if usage else None,
            )

            b64_data = body['data'][0].get('b64_json')
            if b64_data:
                log.info('openai_success', format='base64')
                usage_result.image_bytes = base64.b64decode(b64_data)
                return usage_result

            image_url = body['data'][0].get('url')
            if image_url:
                log.info('openai_success', format='url')
                async with httpx.AsyncClient(timeout=30.0) as dl:
                    dl_resp = await dl.get(image_url)
                    dl_resp.raise_for_status()
                    usage_result.image_bytes = dl_resp.content
                    return usage_result

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
        except (httpx.TransportError, httpx.TimeoutException, ConnectionError, OSError) as exc:
            if attempt < max_retries:
                delay = 2 ** attempt
                log.warn('openai_network_error', error=str(exc), retry_delay=delay)
                await asyncio.sleep(delay)
                continue
            raise OpenAIImageError(f'Network error: {exc}')
        except Exception as exc:
            raise OpenAIImageError(f'Unexpected error: {exc}')

    raise OpenAIImageError('Failed after all retries')
