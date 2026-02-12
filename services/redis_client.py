import os


class RedisHealthClient:
    def __init__(self, url: str | None) -> None:
        self.url = url

    @classmethod
    def from_env(cls) -> 'RedisHealthClient':
        return cls(os.getenv('REDIS_URL'))

    async def ping(self) -> bool:
        if not self.url:
            return False

        try:
            import redis.asyncio as redis
        except Exception:
            return False

        try:
            client = redis.from_url(self.url, decode_responses=True)
            result = await client.ping()
            await client.aclose()
            return bool(result)
        except Exception:
            return False

