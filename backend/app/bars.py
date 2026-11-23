"""OHLCV slicing and yield-index scaling shared by live and fixture paths."""

from __future__ import annotations

from datetime import datetime, timezone

from app.symbols import RATE_SYMBOLS

RANGES = ("1D", "5D", "1M", "6M", "YTD", "1Y", "5Y")

RANGE_TO_YF = {
    "1D": ("5d", "5m"),
    "5D": ("5d", "15m"),
    "1M": ("1mo", "1d"),
    "6M": ("6mo", "1d"),
    "YTD": ("ytd", "1d"),
    "1Y": ("1y", "1d"),
    "5Y": ("5y", "1d"),
}


def scale_value(symbol: str, value: float | None) -> float | None:
    """CBOE yield indexes are sometimes quoted as yield × 10. Leave true percents alone."""
    if value is None:
        return None
    if symbol in RATE_SYMBOLS and abs(value) > 20:
        return value / 10.0
    return value


def scale_bar(symbol: str, bar: dict) -> dict:
    return {
        "time": bar["time"],
        "open": scale_value(symbol, float(bar["open"])) or 0.0,
        "high": scale_value(symbol, float(bar["high"])) or 0.0,
        "low": scale_value(symbol, float(bar["low"])) or 0.0,
        "close": scale_value(symbol, float(bar["close"])) or 0.0,
        "volume": float(bar.get("volume") or 0),
    }


def _day_key(stamp: int | str) -> str:
    if isinstance(stamp, str):
        return stamp[:10]
    return datetime.fromtimestamp(int(stamp), tz=timezone.utc).date().isoformat()


def last_session(bars: list[dict]) -> list[dict]:
    if not bars:
        return []
    day = _day_key(bars[-1]["time"])
    session = [bar for bar in bars if _day_key(bar["time"]) == day]
    return session or bars[-1:]


def slice_range(daily: list[dict], intraday: list[dict], range_key: str) -> tuple[list[dict], str]:
    key = range_key if range_key in RANGES else "1Y"
    if key == "1D":
        session = last_session(intraday)
        if len(session) >= 4:
            return session, "15m" if _looks_fifteen(session) else "5m"
        return daily[-2:], "1d"
    if key == "5D":
        if len(intraday) >= 8:
            return intraday, "15m" if _looks_fifteen(intraday) else "5m"
        return daily[-6:], "1d"
    if not daily:
        return [], "1d"
    if key == "1M":
        return daily[-22:], "1d"
    if key == "6M":
        return daily[-132:], "1d"
    if key == "YTD":
        year = str(daily[-1]["time"])[:4]
        year_bars = [bar for bar in daily if str(bar["time"]).startswith(year)]
        return (year_bars or daily[-22:]), "1d"
    if key == "5Y":
        return daily, "1d"
    return daily[-252:], "1d"


def _looks_fifteen(bars: list[dict]) -> bool:
    if len(bars) < 3 or not isinstance(bars[-1]["time"], (int, float)):
        return True
    gap = int(bars[-1]["time"]) - int(bars[-2]["time"])
    return gap >= 600


def ytd_return(daily: list[dict]) -> float | None:
    if len(daily) < 2:
        return None
    year = str(daily[-1]["time"])[:4]
    prior = [bar for bar in daily if str(bar["time"])[:4] < year]
    base = prior[-1]["close"] if prior else daily[0]["close"]
    last = daily[-1]["close"]
    if not base:
        return None
    return (last / base - 1.0) * 100.0
