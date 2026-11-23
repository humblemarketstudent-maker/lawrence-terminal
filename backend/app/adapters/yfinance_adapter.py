"""Zero-key market data via yfinance. Unofficial and delayed; failures fall back upstream."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from app.bars import RANGE_TO_YF, last_session, scale_bar, scale_value
from app.schemas import Quote
from app.symbols import bloomberg_label, classify, currency_for, exchange_for, name_for
from app.util import iso, num

log = logging.getLogger(__name__)
_POOL = ThreadPoolExecutor(max_workers=3, thread_name_prefix="apex-yf")


def executor() -> ThreadPoolExecutor:
    return _POOL


def _frame_for(df: pd.DataFrame | None, symbol: str) -> pd.DataFrame | None:
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        levels0 = {str(value) for value in df.columns.get_level_values(0)}
        levels1 = {str(value) for value in df.columns.get_level_values(1)}
        if symbol in levels0:
            sub = df[symbol]
        elif symbol in levels1:
            sub = df.xs(symbol, axis=1, level=1)
        else:
            return None
    else:
        sub = df
    sub = sub.dropna(how="all")
    return None if sub.empty else sub


def _bars(frame: pd.DataFrame | None, symbol: str, intraday: bool) -> list[dict]:
    if frame is None:
        return []
    rows = []
    for idx, row in frame.iterrows():
        close = num(row.get("Close"))
        if close is None:
            continue
        stamp = pd.Timestamp(idx)
        if intraday:
            if stamp.tzinfo is None:
                stamp = stamp.tz_localize("UTC")
            time_value: int | str = int(stamp.tz_convert("UTC").timestamp())
        else:
            time_value = stamp.strftime("%Y-%m-%d")
        bar = scale_bar(
            symbol,
            {
                "time": time_value,
                "open": num(row.get("Open")) or close,
                "high": num(row.get("High")) or close,
                "low": num(row.get("Low")) or close,
                "close": close,
                "volume": num(row.get("Volume")) or 0.0,
            },
        )
        rows.append(bar)
    return rows


def _quote_from_daily(symbol: str, daily: list[dict]) -> Quote | None:
    if len(daily) < 1:
        return None
    last = daily[-1]
    previous = daily[-2]["close"] if len(daily) > 1 else None
    price = last["close"]
    change = price - previous if previous is not None else None
    change_pct = (change / previous * 100.0) if change is not None and previous else None
    window = daily[-252:]
    vol_window = [bar["volume"] for bar in daily[-30:] if bar.get("volume")]
    avg = sum(vol_window) / len(vol_window) if vol_window else None
    return Quote(
        symbol=symbol,
        name=name_for(symbol),
        label=bloomberg_label(symbol),
        assetClass=classify(symbol),
        currency=currency_for(symbol),
        exchange=exchange_for(symbol),
        price=price,
        change=change,
        changePct=change_pct,
        open=last["open"],
        high=last["high"],
        low=last["low"],
        previousClose=previous,
        volume=last["volume"] or None,
        avgVolume30d=avg,
        volumeRatio=(last["volume"] / avg) if last["volume"] and avg else None,
        week52High=max(bar["high"] for bar in window),
        week52Low=min(bar["low"] for bar in window),
        sparkline=[bar["close"] for bar in daily[-32:]],
        status="ok",
        sample=False,
        asOf=iso(),
    )


def apply_previous_close(quote: Quote, previous: float | None, volume: float | None = None) -> Quote:
    """Fill change versus a real previous close. Never invents the prior print."""
    if quote.price is None or quote.previousClose is not None or previous is None or previous <= 0:
        return quote
    change = quote.price - previous
    updates: dict = {
        "previousClose": previous,
        "change": change,
        "changePct": change / previous * 100.0,
    }
    if quote.volume is None and volume:
        updates["volume"] = volume
    return quote.model_copy(update=updates)


def _fill_thin_previous(symbol: str, quote: Quote) -> Quote:
    """Yahoo sometimes returns a last price with only one daily bar (CSI 300)."""
    if quote.previousClose is not None or quote.price is None:
        return quote
    try:
        import yfinance as yf

        previous = scale_value(symbol, num(yf.Ticker(symbol).fast_info.previous_close))
    except Exception as exc:
        log.info("previous close %s: %s", symbol, exc)
        return quote
    return apply_previous_close(quote, previous)


def download_quotes(symbols: list[str]) -> list[Quote]:
    import yfinance as yf

    if not symbols:
        return []
    quotes: list[Quote] = []
    chunk_size = 40
    for i in range(0, len(symbols), chunk_size):
        chunk = symbols[i : i + chunk_size]
        try:
            frame = yf.download(
                " ".join(chunk),
                period="1y",
                interval="1d",
                group_by="ticker",
                auto_adjust=False,
                progress=False,
                threads=False,
                timeout=20,
            )
        except Exception as exc:
            log.warning("yfinance download chunk failed: %s", exc)
            frame = None
        for symbol in chunk:
            daily = _bars(_frame_for(frame, symbol), symbol, intraday=False) if frame is not None else []
            if len(daily) < 2:
                try:
                    single = yf.Ticker(symbol).history(period="1y", interval="1d", auto_adjust=False, timeout=20)
                    daily = _bars(single, symbol, intraday=False)
                except Exception as exc:
                    log.info("yfinance history fallback %s: %s", symbol, exc)
            quote = _quote_from_daily(symbol, daily)
            if quote is not None and quote.previousClose is None:
                quote = _fill_thin_previous(symbol, quote)
            if quote:
                quotes.append(quote)
    return quotes


def download_history(symbol: str, range_key: str) -> tuple[list[dict], str]:
    import yfinance as yf

    period, interval = RANGE_TO_YF.get(range_key, ("1y", "1d"))
    ticker = yf.Ticker(symbol)
    frame = ticker.history(period=period, interval=interval, auto_adjust=False, timeout=20)
    intraday = interval.endswith("m") or interval.endswith("h")
    bars = _bars(frame, symbol, intraday=intraday)
    if range_key == "1D":
        bars = last_session(bars)
        if len(bars) < 4:
            frame = ticker.history(period="5d", interval="15m", auto_adjust=False, timeout=20)
            bars = last_session(_bars(frame, symbol, intraday=True))
            interval = "15m"
    if range_key == "5D" and len(bars) < 8:
        frame = ticker.history(period="1mo", interval="1d", auto_adjust=False, timeout=20)
        bars = _bars(frame, symbol, intraday=False)[-6:]
        interval = "1d"
    return bars, interval


def _statement_block(frame: pd.DataFrame | None) -> dict | None:
    if frame is None or frame.empty:
        return None
    columns = list(reversed(list(frame.columns)))
    periods = [str(pd.Timestamp(col).date()) for col in columns]
    lines: dict[str, list] = {}
    for name, row in frame.iterrows():
        values = []
        series = list(reversed(list(row.tolist())))
        for value in series:
            values.append(None if pd.isna(value) else float(value))
        lines[str(name)] = values
    return {"periods": periods, "lines": lines}


def _slim_info(raw: dict) -> dict:
    keys = [
        "shortName", "longName", "sector", "industry", "longBusinessSummary", "fullTimeEmployees",
        "city", "state", "country", "website", "companyOfficers", "trailingPE", "forwardPE", "pegRatio",
        "enterpriseToRevenue", "enterpriseToEbitda", "priceToBook", "marketCap", "enterpriseValue",
        "dividendYield", "beta", "targetMeanPrice", "targetHighPrice", "targetLowPrice",
        "recommendationKey", "numberOfAnalystOpinions", "freeCashflow", "returnOnEquity",
        "totalRevenue", "trailingEps", "quoteType", "currency", "exchange",
    ]
    out: dict = {}
    for key in keys:
        value = raw.get(key)
        if key == "companyOfficers" and isinstance(value, list):
            out[key] = [
                {"name": officer.get("name"), "title": officer.get("title")}
                for officer in value[:8]
                if isinstance(officer, dict)
            ]
        elif key == "longBusinessSummary" and isinstance(value, str):
            out[key] = value[:1200]
        elif isinstance(value, str):
            out[key] = value
        else:
            number = num(value)
            out[key] = number if number is not None else value
    return out


def download_fundamentals(symbol: str) -> dict:
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    info = ticker.info or {}
    return {
        "info": _slim_info(info),
        "income": _statement_block(ticker.financials),
        "balance": _statement_block(ticker.balance_sheet),
        "cashflow": _statement_block(ticker.cashflow),
    }


def download_options(symbol: str, spot: float | None) -> dict | None:
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    expiries = list(ticker.options or [])
    if not expiries:
        return None
    chain = ticker.option_chain(expiries[0])
    calls, puts = chain.calls, chain.puts
    if calls is None or puts is None or calls.empty or puts.empty or spot is None:
        return None
    merged = calls.merge(puts, on="strike", suffixes=("_c", "_p"))
    if merged.empty:
        return None
    merged = merged.assign(_dist=(merged["strike"] - spot).abs()).sort_values("_dist")
    row = merged.iloc[0]
    return {
        "expiry": expiries[0],
        "underlying": spot,
        "atmStrike": num(row["strike"]),
        "callLast": num(row.get("lastPrice_c")),
        "putLast": num(row.get("lastPrice_p")),
        "callIV": num(row.get("impliedVolatility_c")),
        "putIV": num(row.get("impliedVolatility_p")),
        "callOI": num(row.get("openInterest_c")),
        "putOI": num(row.get("openInterest_p")),
    }


def silence_yfinance() -> None:
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    logging.getLogger("peewee").setLevel(logging.CRITICAL)
