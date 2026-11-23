"""Capture a public-data snapshot used as the offline fixture bundle.

Run from the backend directory:
  .venv/bin/python scripts/snapshot_fixtures.py
"""

from __future__ import annotations

import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "app" / "fixtures" / "snapshot.json"
UA = "APEX Terminal research@apex-terminal.local"
SEC_UA = UA

SYMBOLS = [
    "SPY", "QQQ", "NVDA", "AAPL", "MSFT", "0700.HK", "9988.HK", "^HSI", "GC=F", "^TNX",
    "^GSPC", "^IXIC", "^DJI", "^N225", "^FTSE", "^GDAXI", "DX-Y.NYB", "CL=F", "BTC-USD",
    "GOOGL", "AMZN", "META", "AMD", "AVGO", "TSM", "ORCL", "CRM", "BABA", "USDHKD=X",
]
FUNDAMENTAL_SYMBOLS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "0700.HK", "9988.HK", "AMD", "AVGO"]
INTRADAY_SYMBOLS = ["AAPL", "MSFT", "NVDA", "SPY", "QQQ", "^GSPC"]
FRED_SERIES = ["DGS3MO", "DGS2", "DGS5", "DGS10", "DGS30", "T10Y2Y", "FEDFUNDS", "CPIAUCSL", "UNRATE", "PAYEMS"]
INFO_KEYS = [
    "shortName", "longName", "sector", "industry", "longBusinessSummary", "fullTimeEmployees",
    "city", "state", "country", "website", "companyOfficers", "trailingPE", "forwardPE", "pegRatio",
    "enterpriseToRevenue", "enterpriseToEbitda", "priceToBook", "marketCap", "enterpriseValue",
    "dividendYield", "beta", "targetMeanPrice", "targetHighPrice", "targetLowPrice",
    "recommendationKey", "numberOfAnalystOpinions", "freeCashflow", "returnOnEquity",
    "totalRevenue", "trailingEps", "forwardEps", "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
    "averageVolume", "quoteType", "currency", "exchange", "sharesOutstanding",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def fnum(value):
    try:
        if value is None:
            return None
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return None
        return number
    except (TypeError, ValueError):
        return None


def frame_for(df, symbol: str):
    import pandas as pd

    if df is None or getattr(df, "empty", True):
        return None
    if isinstance(df.columns, pd.MultiIndex):
        levels0 = set(map(str, df.columns.get_level_values(0)))
        levels1 = set(map(str, df.columns.get_level_values(1)))
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


def bars_from(df, intraday: bool) -> list[dict]:
    import pandas as pd

    rows = []
    if df is None:
        return rows
    for idx, row in df.iterrows():
        close = fnum(row.get("Close"))
        if close is None:
            continue
        ts = pd.Timestamp(idx)
        if intraday:
            if ts.tzinfo is None:
                ts = ts.tz_localize("UTC")
            stamp = int(ts.tz_convert("UTC").timestamp())
        else:
            stamp = ts.strftime("%Y-%m-%d")
        rows.append(
            {
                "time": stamp,
                "open": fnum(row.get("Open")) or close,
                "high": fnum(row.get("High")) or close,
                "low": fnum(row.get("Low")) or close,
                "close": close,
                "volume": fnum(row.get("Volume")) or 0.0,
            }
        )
    return rows


def quote_from_bars(symbol: str, daily: list[dict], info: dict | None) -> dict | None:
    if len(daily) < 2 and not info:
        return None
    last = daily[-1] if daily else None
    prev = daily[-2] if len(daily) > 1 else None
    window = daily[-252:] if daily else []
    vol_window = [b["volume"] for b in daily[-30:] if b.get("volume")]
    price = fnum((info or {}).get("lastPrice")) or (last["close"] if last else None)
    previous = fnum((info or {}).get("previousClose")) or (prev["close"] if prev else None)
    if price is None:
        return None
    change = price - previous if previous is not None else None
    change_pct = (change / previous * 100) if change is not None and previous else None
    highs = [b["high"] for b in window] or [price]
    lows = [b["low"] for b in window] or [price]
    return {
        "symbol": symbol,
        "price": price,
        "previousClose": previous,
        "open": fnum((info or {}).get("open")) or (last["open"] if last else None),
        "high": fnum((info or {}).get("dayHigh")) or (last["high"] if last else None),
        "low": fnum((info or {}).get("dayLow")) or (last["low"] if last else None),
        "volume": fnum((info or {}).get("lastVolume")) or (last["volume"] if last else None),
        "avgVolume30d": (sum(vol_window) / len(vol_window)) if vol_window else fnum((info or {}).get("averageVolume")),
        "week52High": fnum((info or {}).get("yearHigh")) or max(highs),
        "week52Low": fnum((info or {}).get("yearLow")) or min(lows),
        "marketCap": fnum((info or {}).get("marketCap")),
        "currency": (info or {}).get("currency"),
        "exchange": (info or {}).get("exchange"),
        "sparkline": [b["close"] for b in daily[-32:]],
        "change": change,
        "changePct": change_pct,
    }


def slim_info(raw: dict) -> dict:
    out = {}
    for key in INFO_KEYS:
        value = raw.get(key)
        if key == "companyOfficers" and isinstance(value, list):
            out[key] = [
                {"name": officer.get("name"), "title": officer.get("title")}
                for officer in value[:8]
                if isinstance(officer, dict)
            ]
        elif key == "longBusinessSummary" and isinstance(value, str):
            out[key] = value[:1200]
        else:
            number = fnum(value)
            out[key] = number if number is not None else value
    return out


def statement_block(df) -> dict | None:
    import pandas as pd

    if df is None or getattr(df, "empty", True):
        return None
    columns = list(df.columns)
    # yfinance returns newest first; store chronological.
    columns = list(reversed(columns))
    periods = [str(pd.Timestamp(col).date()) for col in columns]
    lines: dict[str, list] = {}
    for name, row in df.iterrows():
        values = []
        series = list(reversed(list(row.tolist())))
        for value in series:
            values.append(None if pd.isna(value) else float(value))
        lines[str(name)] = values
    return {"periods": periods, "lines": lines}


def fetch_history(symbols: list[str]) -> dict[str, list[dict]]:
    import yfinance as yf

    daily: dict[str, list[dict]] = {}
    for chunk_start in range(0, len(symbols), 8):
        chunk = symbols[chunk_start : chunk_start + 8]
        print(f"daily {chunk}", flush=True)
        try:
            df = yf.download(
                " ".join(chunk),
                period="5y",
                interval="1d",
                group_by="ticker",
                auto_adjust=False,
                progress=False,
                threads=False,
                timeout=20,
            )
        except Exception as exc:
            print(f"  batch failed: {exc}", flush=True)
            df = None
        for symbol in chunk:
            frame = frame_for(df, symbol)
            rows = bars_from(frame, intraday=False)
            if len(rows) < 30:
                try:
                    single = yf.Ticker(symbol).history(period="5y", interval="1d", auto_adjust=False, timeout=20)
                    rows = bars_from(single, intraday=False)
                except Exception as exc:
                    print(f"  {symbol} history failed: {exc}", flush=True)
            if rows:
                daily[symbol] = rows
                print(f"  {symbol} {len(rows)} bars last {rows[-1]['close']}", flush=True)
    return daily


def fetch_intraday(symbols: list[str]) -> dict[str, list[dict]]:
    import yfinance as yf

    out: dict[str, list[dict]] = {}
    for symbol in symbols:
        print(f"intraday {symbol}", flush=True)
        try:
            frame = yf.Ticker(symbol).history(period="5d", interval="15m", auto_adjust=False, timeout=20)
            rows = bars_from(frame, intraday=True)
            if rows:
                out[symbol] = rows
                print(f"  {len(rows)} bars", flush=True)
        except Exception as exc:
            print(f"  failed: {exc}", flush=True)
    return out


def fetch_fast(symbols: list[str]) -> dict[str, dict]:
    import yfinance as yf

    out = {}
    for symbol in symbols:
        try:
            info = dict(yf.Ticker(symbol).fast_info)
            out[symbol] = {key: (None if fnum(value) is None and not isinstance(value, str) else value) for key, value in info.items()}
            # cast numbers
            clean = {}
            for key, value in info.items():
                if isinstance(value, str):
                    clean[key] = value
                else:
                    clean[key] = fnum(value)
            out[symbol] = clean
        except Exception as exc:
            print(f"fast {symbol} failed: {exc}", flush=True)
    return out


def fetch_fundamentals(symbols: list[str], spots: dict[str, float | None] | None = None) -> tuple[dict, dict, dict]:
    import yfinance as yf

    infos, statements, options = {}, {}, {}
    for symbol in symbols:
        print(f"fundamentals {symbol}", flush=True)
        try:
            ticker = yf.Ticker(symbol)
            raw = ticker.info or {}
            infos[symbol] = slim_info(raw)
            block = {
                "income": statement_block(ticker.financials),
                "balance": statement_block(ticker.balance_sheet),
                "cashflow": statement_block(ticker.cashflow),
            }
            if any(block.values()):
                statements[symbol] = block
                income = block["income"] or {}
                rev = (income.get("lines") or {}).get("Total Revenue")
                print(f"  revenue {rev[-1] if rev else None}", flush=True)
        except Exception as exc:
            print(f"  fundamentals failed: {exc}", flush=True)
        if symbol == "AAPL":
            try:
                ticker = yf.Ticker(symbol)
                expiries = list(ticker.options or [])
                if expiries:
                    chain = ticker.option_chain(expiries[0])
                    price = fnum((infos.get(symbol) or {}).get("targetMeanPrice"))
                    # underlying from calls if needed
                    calls = chain.calls
                    puts = chain.puts
                    spot = (spots or {}).get(symbol)
                    if calls is not None and not calls.empty and puts is not None and not puts.empty:
                        merged = calls.merge(puts, on="strike", suffixes=("_c", "_p"))
                        if spot:
                            merged = merged.assign(_dist=(merged["strike"] - spot).abs()).sort_values("_dist")
                            row = merged.iloc[0]
                        else:
                            merged["_gap"] = (merged["lastPrice_c"] - merged["lastPrice_p"]).abs()
                            row = merged.sort_values("_gap").iloc[0]
                        options[symbol] = {
                            "expiry": expiries[0],
                            "underlying": spot,
                            "atmStrike": fnum(row["strike"]),
                            "callLast": fnum(row.get("lastPrice_c")),
                            "putLast": fnum(row.get("lastPrice_p")),
                            "callIV": fnum(row.get("impliedVolatility_c")),
                            "putIV": fnum(row.get("impliedVolatility_p")),
                            "callOI": fnum(row.get("openInterest_c")),
                            "putOI": fnum(row.get("openInterest_p")),
                        }
                        print(f"  options {options[symbol]['expiry']} {options[symbol]['atmStrike']}", flush=True)
            except Exception as exc:
                print(f"  options failed: {exc}", flush=True)
        time.sleep(0.2)
    return infos, statements, options


def fetch_fred() -> dict[str, list[list]]:
    out: dict[str, list[list]] = {}
    with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": UA}) as client:
        for series in FRED_SERIES:
            url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
            try:
                response = client.get(url)
                response.raise_for_status()
                rows = []
                for line in response.text.splitlines()[1:]:
                    parts = line.split(",")
                    if len(parts) < 2:
                        continue
                    raw = parts[1].strip()
                    if not raw or raw == ".":
                        continue
                    try:
                        rows.append([parts[0], float(raw)])
                    except ValueError:
                        continue
                if rows:
                    out[series] = rows[-800:]
                    print(f"fred {series} {out[series][-1]}", flush=True)
            except Exception as exc:
                print(f"fred {series} failed: {exc}", flush=True)
    return out


def fetch_news() -> list[dict]:
    import feedparser

    feeds = [
        ("REUTERS", "https://news.google.com/rss/search?q=site:reuters.com+when:3d+(markets+OR+stocks+OR+Fed)&hl=en-US&gl=US&ceid=US:en"),
        ("BLOOMBERG", "https://news.google.com/rss/search?q=site:bloomberg.com+when:3d+(markets+OR+stocks)&hl=en-US&gl=US&ceid=US:en"),
        ("WSJ", "https://news.google.com/rss/search?q=site:wsj.com+when:3d+(markets+OR+stocks+OR+Fed)&hl=en-US&gl=US&ceid=US:en"),
        ("YAHOO", "https://finance.yahoo.com/news/rssindex"),
    ]
    items = []
    with httpx.Client(timeout=12, follow_redirects=True, headers={"User-Agent": UA}) as client:
        for source, url in feeds:
            try:
                response = client.get(url)
                response.raise_for_status()
                parsed = feedparser.parse(response.content)
                count = 0
                for entry in parsed.entries[:12]:
                    title = getattr(entry, "title", "") or ""
                    if not title:
                        continue
                    published = None
                    if getattr(entry, "published_parsed", None):
                        published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
                    elif getattr(entry, "updated_parsed", None):
                        published = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc).isoformat()
                    summary = getattr(entry, "summary", "") or ""
                    items.append(
                        {
                            "headline": title,
                            "source": source,
                            "url": getattr(entry, "link", "") or "",
                            "publishedAt": published or now(),
                            "summary": summary[:700],
                        }
                    )
                    count += 1
                print(f"news {source} {count}", flush=True)
            except Exception as exc:
                print(f"news {source} failed: {exc}", flush=True)
    return items


def fetch_filings(tickers: list[str]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    headers = {"User-Agent": SEC_UA, "Accept": "application/json"}
    with httpx.Client(timeout=20, follow_redirects=True, headers=headers) as client:
        try:
            listing = client.get("https://www.sec.gov/files/company_tickers.json")
            listing.raise_for_status()
            companies = listing.json()
        except Exception as exc:
            print(f"sec tickers failed: {exc}", flush=True)
            return out
        cik_by_ticker = {}
        for row in companies.values():
            if isinstance(row, dict) and row.get("ticker"):
                cik_by_ticker[str(row["ticker"]).upper()] = str(row["cik_str"]).zfill(10)
        for ticker in tickers:
            cik = cik_by_ticker.get(ticker.upper())
            if not cik:
                print(f"sec no cik {ticker}", flush=True)
                continue
            time.sleep(0.25)
            try:
                response = client.get(f"https://data.sec.gov/submissions/CIK{cik}.json")
                response.raise_for_status()
                recent = response.json().get("filings", {}).get("recent", {})
                forms = recent.get("form", [])
                dates = recent.get("filingDate", [])
                accessions = recent.get("accessionNumber", [])
                docs = recent.get("primaryDocument", [])
                descriptions = recent.get("primaryDocDescription", [])
                filings = []
                cik_int = str(int(cik))
                for form, filed, accession, doc, desc in zip(forms, dates, accessions, docs, descriptions):
                    if form not in {"10-K", "10-Q", "8-K", "4"}:
                        continue
                    acc_nodash = accession.replace("-", "")
                    url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/{doc}"
                    filings.append(
                        {
                            "form": form,
                            "filed": filed,
                            "description": desc or form,
                            "accession": accession,
                            "url": url,
                        }
                    )
                    if len(filings) >= 12:
                        break
                if filings:
                    out[ticker] = filings
                    print(f"sec {ticker} {len(filings)}", flush=True)
            except Exception as exc:
                print(f"sec {ticker} failed: {exc}", flush=True)
    return out


def main() -> int:
    started = time.time()
    print("collecting daily history", flush=True)
    daily = fetch_history(SYMBOLS)
    intraday = fetch_intraday(INTRADAY_SYMBOLS)
    fast = fetch_fast(SYMBOLS)
    spots = {symbol: fnum((fast.get(symbol) or {}).get("lastPrice")) for symbol in FUNDAMENTAL_SYMBOLS}
    infos, statements, options = fetch_fundamentals(FUNDAMENTAL_SYMBOLS, spots)
    quotes = {}
    for symbol in SYMBOLS:
        quote = quote_from_bars(symbol, daily.get(symbol, []), fast.get(symbol))
        if quote:
            info = infos.get(symbol) or {}
            if not quote.get("marketCap"):
                quote["marketCap"] = fnum(info.get("marketCap"))
            if not quote.get("currency"):
                quote["currency"] = info.get("currency")
            quotes[symbol] = quote
    # Fill option underlying with the quote.
    for symbol, snap in options.items():
        quote = quotes.get(symbol)
        if quote:
            snap["underlying"] = quote["price"]
    fred = fetch_fred()
    news = fetch_news()
    filings = fetch_filings(["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META"])
    payload = {
        "asOf": now(),
        "quotes": quotes,
        "daily": daily,
        "intraday": intraday,
        "info": infos,
        "statements": statements,
        "options": options,
        "news": news,
        "filings": filings,
        "macro": fred,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, separators=(",", ":")))
    size = OUT.stat().st_size
    print(
        f"wrote {OUT} bytes={size} quotes={len(quotes)} daily={len(daily)} news={len(news)} fred={len(fred)} filings={len(filings)} in {time.time()-started:.1f}s",
        flush=True,
    )
    return 0 if quotes else 1


if __name__ == "__main__":
    sys.exit(main())
