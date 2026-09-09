from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    xai_api_key: str
    grok_model: str = "grok-4.6"
    xai_base_url: str = "https://api.x.ai/v1"
    system_prompt: str = (
        "You are Grok, built by xAI. Be helpful, direct, and a little witty."
    )

    telegram_bot_token: str = ""
    telegram_allowed_user_ids: str = ""

    discord_bot_token: str = ""
    discord_channel_ids: str = ""

    web_enabled: bool = True
    web_host: str = "0.0.0.0"
    web_port: int = 8080
    web_access_key: str = "change-me"

    max_history_turns: int = 20
    max_output_tokens: int = 4096
    temperature: float = 0.7

    @property
    def telegram_allowlist(self) -> List[int]:
        raw = self.telegram_allowed_user_ids.strip()
        if not raw:
            return []
        return [int(x.strip()) for x in raw.split(",") if x.strip()]

    @property
    def discord_channels(self) -> List[int]:
        raw = self.discord_channel_ids.strip()
        if not raw:
            return []
        return [int(x.strip()) for x in raw.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
