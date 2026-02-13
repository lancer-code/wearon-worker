from typing import Literal

from pydantic import BaseModel


class GenerationTask(BaseModel):
    """Pydantic model matching the Redis queue contract from packages/api/src/types/queue.ts.

    The TypeScript side serializes to snake_case JSON via toSnakeCase() before LPUSH.
    """

    task_id: str
    channel: Literal['b2b', 'b2c']
    store_id: str | None = None
    user_id: str | None = None
    session_id: str
    image_urls: list[str]
    prompt: str
    request_id: str
    version: int = 1
    created_at: str
