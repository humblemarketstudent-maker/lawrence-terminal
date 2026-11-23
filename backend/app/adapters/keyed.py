"""Optional keyed quote adapters. Used only when the operator selects one and supplies a key."""

from __future__ import annotations

import logging

import httpx

from app.schemas import Quote
from app.symbols import bloomberg_label, classify, currency_for, exchange_for, name_for
from app.util import iso, num

log = logging.getLogger(__name__)


def _base_quote(symbol: str, **fields) -> Quote:
    payload = {
        "symbol": symbol,
        "name": name_for(symbol),
        "label": bloomberg_label(symbol),
        "assetClass": classify(symbol),
        "currency": currency_for(symbol),
        "exchange": exchange_for(symbol),
        "status": "ok",
        "sample": False,
        "asOf": iso(),
    }
    payload.update(fields)
    return Quote(**payload)


class KeyedQuotes:
    name = "keyed"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        raise NotImplementedError


class FinnhubQuotes(KeyedQuotes):
    name = "finnhub"

    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        quotes: list[Quote] = []
        async with httpx.AsyncClient(timeout=8.0) as client:
            for symbol in symbols:
                response = await client.get(
                    "https://finnhub.io/api/v1/quote",
                    params={"symbol": symbol, "token": self.api_key},
                )
                response.raise_for_status()
                payload = response.json()
                price = num(payload.get("c"))
                if not price:
                    continue
                previous = num(payload.get("pc"))
                change = num(payload.get("d"))
                if change is None and previous is not None:
                    change = price - previous
                quotes.append(
                    _base_quote(
                        symbol,
                        price=price,
                        change=change,
                        changePct=num(payload.get("dp")),
                        open=num(payload.get("o")),
                        high=num(payload.get("h")),
                        low=num(payload.get("l")),
                        previousClose=previous,
                    )
                )
        return quotes


class FmpQuotes(KeyedQuotes):
    name = "fmp"

    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        if not symbols:
            return []
        joined = ",".join(symbols)
        urls = [
            f"https://financialmodelingprep.com/stable/quote?symbol={joined}&apikey={self.api_key}",
            f"https://financialmodelingprep.com/api/v3/quote/{joined}?apikey={self.api_key}",
        ]
        payload = None
        async with httpx.AsyncClient(timeout=8.0) as client:
            for url in urls:
                response = await client.get(url)
                if response.status_code >= 400:
                    continue
                data = response.json()
                if isinstance(data, list) and data:
                    payload = data
                    break
        if not payload:
            return []
        quotes: list[Quote] = []
        for row in payload:
            symbol = str(row.get("symbol") or "")
            price = num(row.get("price"))
            if not symbol or price is None:
                continue
            previous = num(row.get("previousClose"))
            change = num(row.get("change"))
            quotes.append(
                _base_quote(
                    symbol,
                    price=price,
                    change=change if change is not None else (price - previous if previous is not None else None),
                    changePct=num(row.get("changesPercentage") or row.get("changePercentage")),
                    open=num(row.get("open")),
                    high=num(row.get("dayHigh")),
                    low=num(row.get("dayLow")),
                    previousClose=previous,
                    volume=num(row.get("volume")),
                    avgVolume30d=num(row.get("avgVolume")),
                    marketCap=num(row.get("marketCap")),
                    week52High=num(row.get("yearHigh")),
                    week52Low=num(row.get("yearLow")),
                    name=name_for(symbol, row.get("name")),
                )
            )
        return quotes


class AlphaVantageQuotes(KeyedQuotes):
    name = "alphavantage"

    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        quotes: list[Quote] = []
        async with httpx.AsyncClient(timeout=10.0) as client:
            for symbol in symbols[:8]:
                response = await client.get(
                    "https://www.alphavantage.co/query",
                    params={"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": self.api_key},
                )
                response.raise_for_status()
                raw = (response.json() or {}).get("Global Quote") or {}
                price = num(raw.get("05. price"))
                if price is None:
                    continue
                previous = num(raw.get("08. previous close"))
                change = num(raw.get("09. change"))
                pct = raw.get("10. change percent")
                pct_num = num(str(pct).replace("%", "")) if pct is not None else None
                quotes.append(
                    _base_quote(
                        symbol,
                        price=price,
                        change=change,
                        changePct=pct_num,
                        open=num(raw.get("02. open")),
                        high=num(raw.get("03. high")),
                        low=num(raw.get("04. low")),
                        previousClose=previous,
                        volume=num(raw.get("06. volume")),
                    )
                )
        return quotes


class TwelveDataQuotes(KeyedQuotes):
    name = "twelvedata"

    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        if not symbols:
            return []
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.twelvedata.com/quote",
                params={"symbol": ",".join(symbols), "apikey": self.api_key},
            )
            response.raise_for_status()
            payload = response.json()
        rows = payload if isinstance(payload, list) else [payload] if isinstance(payload, dict) and payload.get("symbol") else []
        if isinstance(payload, dict) and isinstance(payload.get("data"), list):
            rows = payload["data"]
        quotes: list[Quote] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("symbol") or "")
            price = num(row.get("close") or row.get("price"))
            if not symbol or price is None:
                continue
            previous = num(row.get("previous_close"))
            change = num(row.get("change"))
            quotes.append(
                _base_quote(
                    symbol,
                    price=price,
                    change=change if change is not None else (price - previous if previous is not None else None),
                    changePct=num(row.get("percent_change")),
                    open=num(row.get("open")),
                    high=num(row.get("high")),
                    low=num(row.get("low")),
                    previousClose=previous,
                    volume=num(row.get("volume")),
                    name=name_for(symbol, row.get("name")),
                )
            )
        return quotes


def keyed_adapter(provider: str, keys: dict[str, str | None]) -> KeyedQuotes | None:
    mapping = {
        "finnhub": (FinnhubQuotes, keys.get("finnhub")),
        "fmp": (FmpQuotes, keys.get("fmp")),
        "alphavantage": (AlphaVantageQuotes, keys.get("alphavantage")),
        "twelvedata": (TwelveDataQuotes, keys.get("twelvedata")),
    }
    factory, key = mapping.get(provider, (None, None))
    if factory is None or not key:
        return None
    return factory(key)
