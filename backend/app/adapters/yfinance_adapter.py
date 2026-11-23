"""Zero-key market data via yfinance. Unofficial and delayed; failures fall back upstream."""

from __future__ import annotations

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pandas as pd

from app.bars import RANGE_TO_YF, last_session, scale_bar, scale_value
from app.schemas import Quote
from app.services.company import price_currency
from app.services.yahoo_public import fill_missing, parse_quote_page, parse_timeseries_latest, peer_info_from_quote, quote_from_chart
from app.symbols import bloomberg_label, classify, currency_for, exchange_for, name_for
from app.util import iso, num

_FUTURE_MONTH = re.compile(r"^[A-Z0-9]{1,8}-[FGHJKMNQUVXZ]\d{2}\.[A-Z]{1,4}$")
_FX_CACHE: dict[str, tuple[float, dict | None]] = {}
_FX_TTL = 600.0

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


def is_future_symbol(symbol: str) -> bool:
    return symbol.endswith("=F") or bool(_FUTURE_MONTH.match(symbol))


def future_quote_from_info(symbol: str, raw: dict | None) -> Quote | None:
    """Last vs Yahoo previous close. Reject a print whose own change disagrees.

    Futures change on this desk is price minus `regularMarketPreviousClose`.
    Yahoo's `regularMarketChange` has to match that difference. A contract
    whose fields disagree, or that is not quoteType FUTURE, is dropped.
    """
    raw = raw or {}
    if str(raw.get("quoteType") or "").upper() != "FUTURE":
        return None
    price = num(raw.get("regularMarketPrice"))
    previous = num(raw.get("regularMarketPreviousClose"))
    if previous is None:
        previous = num(raw.get("previousClose"))
    if price is None or price <= 0 or previous is None or previous <= 0:
        return None
    traded = num(raw.get("regularMarketTime"))
    if traded is not None:
        age_days = (datetime.now(timezone.utc).timestamp() - traded) / 86400.0
        if age_days > 5:
            log.info("futures %s rejected: last trade %.1f days ago", symbol, age_days)
            return None
    change = price - previous
    reported = num(raw.get("regularMarketChange"))
    tolerance = max(0.05, abs(previous) * 1e-4)
    if reported is not None and abs(reported - change) > tolerance:
        log.info("futures %s rejected: price %s prev %s yahoo change %s", symbol, price, previous, reported)
        return None
    name = raw.get("shortName") or raw.get("longName") or symbol
    currency = raw.get("currency") if isinstance(raw.get("currency"), str) else currency_for(symbol)
    exchange = raw.get("exchange") if isinstance(raw.get("exchange"), str) else exchange_for(symbol)
    volume = num(raw.get("regularMarketVolume"))
    return Quote(
        symbol=symbol,
        name=str(name),
        label=bloomberg_label(symbol),
        assetClass="future",
        currency=currency or "USD",
        exchange=exchange or "",
        price=price,
        change=change,
        changePct=change / previous * 100.0,
        previousClose=previous,
        volume=volume if volume and volume > 0 else None,
        status="ok",
        sample=False,
        asOf=iso(),
    )


def _chart_result(symbol: str) -> dict | None:
    """v8 chart. This endpoint quotes without the crumb quoteSummary requires."""
    try:
        from curl_cffi import requests

        response = requests.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/" + requests.utils.quote(symbol, safe=""),
            params={"range": "10d", "interval": "1d", "includePrePost": "false"},
            impersonate="chrome",
            timeout=15,
        )
        payload = response.json()
    except Exception as exc:
        log.info("chart %s: %s", symbol, exc)
        return None
    result = ((payload.get("chart") or {}).get("result") or [None])[0]
    return result if isinstance(result, dict) else None


def _download_future_quotes(symbols: list[str]) -> list[Quote]:
    import yfinance as yf

    def one(symbol: str) -> Quote | None:
        quote = quote_from_chart(symbol, _chart_result(symbol), futures_only=True)
        if quote is not None:
            return quote
        try:
            raw = yf.Ticker(symbol).info or {}
        except Exception as exc:
            log.info("futures info %s: %s", symbol, exc)
            return None
        return future_quote_from_info(symbol, raw)

    quotes: list[Quote] = []
    with ThreadPoolExecutor(max_workers=4, thread_name_prefix="apex-fut") as pool:
        for quote in pool.map(one, symbols):
            if quote is not None:
                quotes.append(quote)
    return quotes


def download_quotes(symbols: list[str]) -> list[Quote]:
    import yfinance as yf

    if not symbols:
        return []
    futures = [symbol for symbol in symbols if is_future_symbol(symbol)]
    cash = [symbol for symbol in symbols if symbol not in set(futures)]
    quotes: list[Quote] = []
    chunk_size = 40
    for i in range(0, len(cash), chunk_size):
        chunk = cash[i : i + chunk_size]
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
            if quote is None or quote.previousClose is None:
                chart = quote_from_chart(symbol, _chart_result(symbol))
                if quote is None:
                    quote = chart
                elif chart is not None and chart.previousClose:
                    quote = quote.model_copy(update={
                        "previousClose": chart.previousClose,
                        "change": chart.change,
                        "changePct": chart.changePct,
                    })
            if quote:
                quotes.append(quote)
    if futures:
        quotes.extend(_download_future_quotes(futures))
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
        "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "regularMarketPrice", "regularMarketChange",
        "regularMarketChangePercent", "regularMarketPreviousClose", "regularMarketVolume",
        "revenueGrowth",
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
            out[key] = value[:1400]
        elif isinstance(value, str):
            out[key] = value
        else:
            number = num(value)
            out[key] = number if number is not None else value
    return out


def _json_date(value: object) -> object:
    if isinstance(value, list):
        return [_json_date(item) for item in value]
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()  # type: ignore[no-any-return]
        except Exception:
            return str(value)
    return value


def _calendar_payload(ticker) -> dict:
    try:
        calendar = ticker.calendar
    except Exception as exc:
        log.info("calendar %s: %s", getattr(ticker, "ticker", ""), exc)
        return {"calendar": {}, "earnings": []}
    flat: dict = {}
    if isinstance(calendar, dict):
        for key, value in calendar.items():
            flat[str(key)] = _json_date(value)
    earnings: list[dict] = []
    try:
        frame = ticker.earnings_dates
    except Exception as exc:
        log.info("earnings dates %s: %s", getattr(ticker, "ticker", ""), exc)
        frame = None
    if frame is not None and not getattr(frame, "empty", True):
        for idx, row in list(frame.head(8).iterrows()):
            stamp = pd.Timestamp(idx)
            earnings.append({"date": str(stamp.date()), "epsEstimate": num(row.get("EPS Estimate"))})
    return {"calendar": flat, "earnings": earnings}


def _recommended_symbols(symbol: str) -> tuple[list[str], str | None]:
    try:
        from curl_cffi import requests

        response = requests.get(
            f"https://query1.finance.yahoo.com/v6/finance/recommendationsbysymbol/{symbol}",
            impersonate="chrome",
            timeout=12,
        )
        payload = response.json()
        result = ((payload.get("finance") or {}).get("result") or [{}])[0]
        found: list[str] = []
        for row in result.get("recommendedSymbols") or []:
            peer = str((row or {}).get("symbol") or "").upper()
            if peer and peer != symbol.upper() and peer not in found:
                found.append(peer)
        return found[:5], None
    except Exception as exc:
        log.info("peers %s: %s", symbol, exc)
        return [], "Yahoo peer feed did not respond."


def _quote_page(symbol: str) -> str:
    try:
        from curl_cffi import requests

        response = requests.get(
            f"https://finance.yahoo.com/quote/{requests.utils.quote(symbol, safe='')}/",
            impersonate="chrome",
            timeout=20,
        )
        if response.status_code != 200:
            log.info("quote page %s: %s", symbol, response.status_code)
            return ""
        return response.text or ""
    except Exception as exc:
        log.info("quote page %s: %s", symbol, exc)
        return ""


def _timeseries_measures(symbol: str) -> dict:
    """Forward P/E and P/B from the same fundamentals series the statements use."""
    try:
        from curl_cffi import requests

        now = int(time.time())
        types = ",".join(["trailingForwardPeRatio", "trailingPbRatio", "trailingPeRatio"])
        response = requests.get(
            "https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/"
            + requests.utils.quote(symbol, safe=""),
            params={"symbol": symbol, "type": types, "period1": "1483228800", "period2": str(now)},
            impersonate="chrome",
            timeout=15,
        )
        if response.status_code != 200:
            return {}
        return parse_timeseries_latest(response.json())
    except Exception as exc:
        log.info("timeseries %s: %s", symbol, exc)
        return {}


def _enrich_info(symbol: str, info: dict) -> dict:
    """Fill profile fields quoteSummary omitted. Existing values are kept."""
    needed = ("longBusinessSummary", "sector", "industry", "forwardPE", "priceToBook")
    if all(info.get(key) not in (None, "", []) for key in needed):
        return info
    info = fill_missing(info, parse_quote_page(_quote_page(symbol)))
    if info.get("forwardPE") in (None, "") or info.get("priceToBook") in (None, ""):
        info = fill_missing(info, _timeseries_measures(symbol))
    return info


def _peer_infos(symbols: list[str]) -> list[dict]:
    def one(peer: str) -> dict | None:
        quote = quote_from_chart(peer, _chart_result(peer), futures_only=False)
        if quote is None or quote.price is None:
            return None
        return peer_info_from_quote(quote, _timeseries_measures(peer))

    if not symbols:
        return []
    with ThreadPoolExecutor(max_workers=4, thread_name_prefix="apex-peer") as pool:
        return [row for row in pool.map(one, symbols) if row]


def _fx_payload(currency: str | None) -> dict | None:
    """USD value of one major unit of `currency`, from a live Yahoo FX pair."""
    major, _divisor = price_currency(currency)
    if major == "USD":
        return {"pair": "USD", "usdPerMajor": 1.0, "major": "USD"}
    now = time.monotonic()
    cached = _FX_CACHE.get(major)
    if cached and now - cached[0] < _FX_TTL:
        return cached[1]
    import yfinance as yf

    chosen: dict | None = None
    for pair, invert in ((f"{major}USD=X", False), (f"USD{major}=X", True)):
        try:
            raw = yf.Ticker(pair).info or {}
        except Exception as exc:
            log.info("fx %s: %s", pair, exc)
            continue
        price = num(raw.get("regularMarketPrice"))
        if price is None or price <= 0:
            continue
        label = f"{raw.get('shortName') or ''} {raw.get('longName') or ''}".upper()
        quote_type = str(raw.get("quoteType") or "").upper()
        if quote_type not in {"CURRENCY", ""} and major not in label and "USD" not in label:
            continue
        if quote_type != "CURRENCY" and major not in label:
            continue
        usd = (1.0 / price) if invert else price
        if not 1e-8 < usd < 1000:
            continue
        chosen = {"pair": pair, "usdPerMajor": usd, "major": major}
        break
    _FX_CACHE[major] = (now, chosen)
    return chosen


def download_fundamentals(symbol: str) -> dict:
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    try:
        raw_info = ticker.info or {}
    except Exception as exc:
        log.info("info %s: %s", symbol, exc)
        raw_info = {}
    info = _enrich_info(symbol, _slim_info(raw_info))
    peers, peers_error = _recommended_symbols(symbol)
    return {
        "info": info,
        "income": _statement_block(ticker.financials),
        "balance": _statement_block(ticker.balance_sheet),
        "cashflow": _statement_block(ticker.cashflow),
        "events": _calendar_payload(ticker),
        "peers": _peer_infos(peers),
        "peerSymbols": peers,
        "peersError": peers_error,
        "fx": _fx_payload(info.get("currency") if isinstance(info.get("currency"), str) else None),
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
