from typing import Literal

from pydantic import BaseModel

SessionStatus = Literal['queued', 'processing', 'completed', 'failed']


class SessionUpdate(BaseModel):
    status: SessionStatus
    result_image_url: str | None = None
    error_message: str | None = None
