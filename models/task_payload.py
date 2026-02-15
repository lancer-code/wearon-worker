from typing import Literal

from pydantic import BaseModel, model_validator


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

    @model_validator(mode='after')
    def validate_channel_ownership(self) -> 'GenerationTask':
        if self.channel == 'b2b' and not self.store_id:
            raise ValueError('b2b channel requires store_id')
        if self.channel == 'b2c' and not self.user_id:
            raise ValueError('b2c channel requires user_id')
        if not self.image_urls:
            raise ValueError('image_urls must not be empty')
        return self
