from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Redis
    redis_url: str = 'redis://localhost:6379/0'

    # Supabase
    supabase_url: str
    supabase_service_role_key: str

    # OpenAI
    openai_api_key: str
    openai_max_retries: int = 3

    # Worker
    worker_concurrency: int = 5

    model_config = {'env_file': '.env', 'env_file_encoding': 'utf-8'}


settings = Settings()
