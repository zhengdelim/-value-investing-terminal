from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    fmp_api_key: str = ""
    anthropic_api_key: str = ""
    database_url: str = "postgresql://valuescreen:valuescreen_pass@localhost:5432/valuescreen"
    redis_url: str = "redis://localhost:6379"
    cache_ttl: int = 3600
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
