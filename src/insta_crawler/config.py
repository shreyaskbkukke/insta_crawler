from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    # Profiles are kept in memory and snapshotted here as JSON. Empty = memory only.
    data_dir: Path | None = Path("./data")

    @field_validator("data_dir", mode="before")
    @classmethod
    def _empty_means_memory(cls, v):
        return None if v == "" else v

    # Graph API credentials: a Facebook-Login user/system token with access to an
    # Instagram Business/Creator account, and that account's IG user id.
    ig_access_token: str = ""
    ig_user_id: str = ""
    graph_api_version: str = "v23.0"
    graph_page_size: int = 25

    # Collection behaviour
    collection_max_retries: int = 5
    collection_retry_base_seconds: float = 2.0
    collection_page_delay_seconds: float = 0.5


@lru_cache
def get_settings() -> Settings:
    return Settings()
