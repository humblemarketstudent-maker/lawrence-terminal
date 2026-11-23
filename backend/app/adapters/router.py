"""Selects the configured quote provider and falls back to yfinance."""

from __future__ import annotations

import asyncio
import logging

from app.adapters.keyed import keyed_adapter
from app.adapters.yfinance_adapter import download_fundamentals, download_history, download_options, download_quotes, executor
from app.config import Settings
from app.schemas import Quote

log = logging.getLogger(__name__)


class ProviderError(RuntimeError):
    pass


class MarketRouter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._keyed = keyed_adapter(
            settings.data_provider.lower().strip(),
            {
                "finnhub": settings.finnhub_api_key,
                "fmp": settings.fmp_api_key,
                "alphavantage": settings.alphavantage_api_key,
                "twelvedata": settings.twelvedata_api_key,
            },
        )

    @property
    def active_name(self) -> str:
        if self._keyed and self.settings.data_provider.lower() != "yfinance":
            return self._keyed.name
        return "yfinance"

    async def _run(self, fn, timeout: float):
        loop = asyncio.get_running_loop()
        return await asyncio.wait_for(loop.run_in_executor(executor(), fn), timeout)

    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        errors: list[str] = []
        quotes: list[Quote] = []
        if self._keyed is not None and self.settings.data_provider.lower() != "yfinance":
            try:
                quotes = await self._keyed.get_quotes(symbols)
            except Exception as exc:
                errors.append(f"{self._keyed.name}: {exc}")
                log.warning("keyed quotes failed: %s", exc)
        found = {quote.symbol for quote in quotes}
        missing = [symbol for symbol in symbols if symbol not in found]
        if missing:
            chunk_size = 40
            for i in range(0, len(missing), chunk_size):
                chunk = missing[i : i + chunk_size]
                try:
                    quotes.extend(await self._run(lambda c=chunk: download_quotes(c), 40))
                except Exception as exc:
                    errors.append(f"yfinance: {exc}")
                    log.warning("yfinance quotes chunk failed: %s", exc)
        if quotes:
            return quotes
        raise ProviderError("; ".join(errors) or "no quote provider returned data")

    async def get_history(self, symbol: str, range_key: str) -> tuple[list[dict], str]:
        return await self._run(lambda: download_history(symbol, range_key), 22)

    async def get_fundamentals(self, symbol: str) -> dict:
        return await self._run(lambda: download_fundamentals(symbol), 45)

    async def get_options(self, symbol: str, spot: float | None) -> dict | None:
        try:
            return await self._run(lambda: download_options(symbol, spot), 12)
        except Exception as exc:
            log.info("options %s skipped: %s", symbol, exc)
            return None
