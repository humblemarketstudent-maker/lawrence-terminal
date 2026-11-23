"""Runtime settings. Optional vendor keys are read from the environment only."""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    data_provider: str = "yfinance"
    finnhub_api_key: str | None = None
    fmp_api_key: str | None = None
    alphavantage_api_key: str | None = None
    twelvedata_api_key: str | None = None
    fred_api_key: str | None = None
    sec_user_agent: str = "APEX Terminal research@apex-terminal.local"
    cache_ttl_quotes: int = 20
    cache_ttl_history: int = 600
    cache_ttl_fundamentals: int = 21600
    cache_ttl_news: int = 180
    cache_ttl_macro: int = 3600
    cache_ttl_filings: int = 3600
    disable_live: bool = Field(default=False)

    def model_post_init(self, __context: object) -> None:
        flag = os.getenv("APEX_DISABLE_LIVE", "")
        if flag.lower() in {"1", "true", "yes"}:
            object.__setattr__(self, "disable_live", True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
