from pydantic_settings import BaseSettings, SettingsConfigDict


class WSSettings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    channel_prefix: str = "upload"
    state_ttl: int = 3600

    model_config = SettingsConfigDict(
        env_prefix="WS_",
        extra="ignore",
    )
