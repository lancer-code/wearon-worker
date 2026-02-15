import sys

import structlog
from pydantic import ValidationError
from pydantic_settings import BaseSettings

logger = structlog.get_logger()

# Required env vars with human-readable descriptions
_REQUIRED_VARS = {
    'supabase_url': 'SUPABASE_URL (Supabase project URL, e.g. https://xxx.supabase.co)',
    'supabase_service_role_key': 'SUPABASE_SERVICE_ROLE_KEY (Supabase service role key, starts with eyJ...)',
    'openai_api_key': 'OPENAI_API_KEY (OpenAI API key, starts with sk-)',
}


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

    model_config = {'env_file': '.env', 'env_file_encoding': 'utf-8', 'extra': 'ignore'}


def _load_settings() -> Settings:
    """Load settings with clear error messages for missing variables."""
    try:
        return Settings()
    except ValidationError as e:
        missing = []
        for error in e.errors():
            field = error['loc'][0] if error['loc'] else 'unknown'
            desc = _REQUIRED_VARS.get(str(field), str(field).upper())
            missing.append(desc)

        logger.error(
            'missing_env_variables',
            missing=missing,
            hint='Add these to your .env file or set as environment variables. See .env.example for reference.',
        )
        for var in missing:
            logger.error('missing_variable', variable=var)

        sys.exit(1)


settings = _load_settings()
