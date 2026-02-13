import io

import httpx
import structlog
from PIL import Image

logger = structlog.get_logger()

MAX_IMAGE_DIMENSION = 1024
JPEG_QUALITY = 85


async def download_image(url: str) -> bytes:
    """Download image from a signed URL."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content


def resize_image(image_bytes: bytes, name: str) -> bytes:
    """Resize image to max 1024px on longest side, convert to JPEG.

    Matches the cost optimization logic from the TypeScript openai-image.ts service.
    """
    img = Image.open(io.BytesIO(image_bytes))
    width, height = img.size
    longest = max(width, height)

    if longest > MAX_IMAGE_DIMENSION:
        scale = MAX_IMAGE_DIMENSION / longest
        new_width = round(width * scale)
        new_height = round(height * scale)
        img = img.resize((new_width, new_height), Image.LANCZOS)
        logger.info(
            'image_resized',
            name=name,
            original=f'{width}x{height}',
            resized=f'{new_width}x{new_height}',
        )

    # Convert to RGB (handles RGBA/palette) and save as JPEG
    if img.mode in ('RGBA', 'P', 'LA'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1])
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=JPEG_QUALITY)
    return buf.getvalue()


async def download_and_resize(url: str, name: str) -> bytes:
    """Download and resize an image for cost-optimal OpenAI input."""
    raw = await download_image(url)
    return resize_image(raw, name)
