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
) -> np.ndarray:
    try:
        timeout = httpx.Timeout(timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(image_url)
            response.raise_for_status()
    except (httpx.TimeoutException, httpx.RequestError) as exc:
        raise ImageDownloadError('Image download timed out or failed') from exc
    except httpx.HTTPStatusError as exc:
        raise ImageDownloadError('Image URL returned a non-success status') from exc

    try:
        image = Image.open(BytesIO(response.content)).convert('RGB')
        image.thumbnail((max_dimension_px, max_dimension_px), Image.Resampling.LANCZOS)
    except (UnidentifiedImageError, OSError) as exc:
        raise ImageDownloadError('Image URL did not return a valid image') from exc

    return np.asarray(image)

