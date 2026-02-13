from io import BytesIO

import httpx
import numpy as np
from PIL import Image, UnidentifiedImageError


class ImageDownloadError(Exception):
    pass


async def download_and_prepare_image(
    image_url: str,
    timeout_seconds: float = 5.0,
    max_dimension_px: int = 512,
    max_content_length_mb: int = 10,
) -> np.ndarray:
    try:
        timeout = httpx.Timeout(timeout_seconds)
        # LOW #3 FIX: Disable redirects to prevent SSRF amplification
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.get(image_url)
            response.raise_for_status()
    except (httpx.TimeoutException, httpx.RequestError) as exc:
        raise ImageDownloadError('Image download timed out or failed') from exc
    except httpx.HTTPStatusError as exc:
        raise ImageDownloadError('Image URL returned a non-success status') from exc

    # MEDIUM #1 FIX: Validate Content-Type before processing
    content_type = response.headers.get('content-type', '').lower()
    if not content_type.startswith('image/'):
        raise ImageDownloadError(f'URL returned non-image content-type: {content_type}')

    # MEDIUM #2 FIX: Enforce response size limit to prevent memory exhaustion
    content_length = len(response.content)
    max_bytes = max_content_length_mb * 1024 * 1024
    if content_length > max_bytes:
        raise ImageDownloadError(f'Image size ({content_length} bytes) exceeds {max_content_length_mb}MB limit')

    try:
        image = Image.open(BytesIO(response.content)).convert('RGB')
        image.thumbnail((max_dimension_px, max_dimension_px), Image.Resampling.LANCZOS)
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageDownloadError('Image URL did not return a valid image') from exc

    return np.asarray(image)

