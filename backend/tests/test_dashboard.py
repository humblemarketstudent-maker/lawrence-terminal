"""Market dashboard: real symbols, no fabricated prints, full equity book."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.adapters.yfinance_adapter import apply_previous_close, future_quote_from_info, is_future_symbol
from app.dashboard import G10, STRIP, TWO_YEAR_SERIES, alias_map, build_dashboard, market_symbols, rank_movers
from app.schemas import Quote
from app.symbols import ASIA_INDEX_SYMBOLS, DEFAULT_WATCHLIST, equity_universe


def _quote(symbol: str, price: float, change_pct: float, volume: float, *, sample: bool = False, asset: str = "equity") -> Quote:
    change = price * change_pct / 100.0
    return Quote(
        symbol=symbol,
        name=symbol,
        label=f"{symbol} US",
        assetClass=asset,
        currency="USD",
        exchange="X",
        price=price,
        change=change,
        changePct=change_pct,
        previousClose=price - change,
        volume=volume,
        status="ok",
        sample=sample,
        asOf="2026-11-20T21:00:00+00:00",
    )


def test_equity_book_keeps_every_name():
    assert len(DEFAULT_WATCHLIST) == 462
    assert len(set(DEFAULT_WATCHLIST)) == 462
    assert len(ASIA_INDEX_SYMBOLS) == 33
    assert set(ASIA_INDEX_SYMBOLS).isdisjoint(DEFAULT_WATCHLIST)
    equities = equity_universe()
    assert len(equities) == 462
    assert equities == list(DEFAULT_WATCHLIST)
    assert not any(symbol.startswith("^") for symbol in equities)
    root = Path(__file__).resolve().parents[2]
    client = (root / "frontend/src/context/TerminalContext.tsx").read_text()
    for symbol in DEFAULT_WATCHLIST:
        assert f'"{symbol}"' in client
    # Frontend DEFAULT_WATCHLIST ends at HO.PA; index tickers are not seeded there.
    assert '"HO.PA"' in client
    assert re.search(r'DEFAULT_WATCHLIST\s*=\s*\[[^\]]*?\^N225', client, re.S) is None


def test_verified_symbols_and_aliases():
    names = [spec.name for spec in STRIP]
    assert names == [
        "S&P 500",
        "NASDAQ 100",
        "Euro Stoxx 50",
        "DAX",
        "FTSE 100",
        "CSI 300",
        "KOSPI",
        "Nikkei 225",
        "TOPIX",
        "S&P/ASX 200",
        "CSI 500",
        "CSI 1000",
        "TWSE",
        "Singapore STI",
        "Nifty 50",
        "KLCI",
        "SET50",
        "USD/JPY",
        "AUD/USD",
        "US 2-Year Yield",
        "US 10-Year Yield",
    ]
    symbols = market_symbols()
    assert symbols[:6] == ["^GSPC", "^NDX", "^STOXX50E", "^GDAXI", "^FTSE", "000300.SS"]
    for futures in ("ES=F", "NQ=F", "NIY=F", "TPY=F", "2YY=F", "SGP-X26.SI"):
        assert futures not in symbols
    assert "^KS11" in symbols
    assert "^N225" in symbols
    assert "^AXJO" in symbols
    assert "000905.SS" in symbols
    assert "000852.SS" in symbols
    assert "^TWII" in symbols
    assert "^STI" in symbols
    assert "^NSEI" in symbols
    assert "^KLSE" in symbols
    assert "^SET50.BK" in symbols
    assert "DGS2" not in symbols
    assert "^TNX" in symbols
    assert symbols.count("USDJPY=X") == 1
    assert [spec.symbol for spec in G10] == [
        "EURUSD=X",
        "GBPUSD=X",
        "USDJPY=X",
        "USDCHF=X",
        "USDCAD=X",
        "AUDUSD=X",
        "NZDUSD=X",
        "USDSEK=X",
        "USDNOK=X",
    ]
    aliases = alias_map()
    assert aliases["eurostoxx"] == "Euro Stoxx 50"
    assert aliases["ftse"] == "FTSE 100"
    assert aliases["asx200"] == "S&P/ASX 200"
    assert aliases["usdjpy"] == "USD/JPY"
    assert aliases["audusd"] == "AUD/USD"
    assert TWO_YEAR_SERIES == "DGS2"
    topix = next(spec for spec in STRIP if spec.name == "TOPIX")
    assert topix.symbol is None


def test_two_year_uses_fred_dgs2_not_the_bill_or_the_ten_year():
    fred = {
        "DGS3MO": [["2026-11-18", 4.15], ["2026-11-19", 4.12]],
        "DGS10": [["2026-11-18", 5.07], ["2026-11-19", 5.04]],
        "DGS2": [["2026-11-18", 4.80], ["2026-11-19", 4.76]],
    }
    section = build_dashboard({}, fred=fred, attempted=set(), macro_done=True, live=True)
    row = next(item for item in section.data.strip if item.name == "US 2-Year Yield")
    ten = next(item for item in section.data.strip if item.name == "US 10-Year Yield")
    assert row.status == "ok"
    assert row.price == 4.76
    assert row.previousClose == 4.80
    assert abs((row.change or 0) - (-0.04)) < 1e-9
    assert row.session == "2026-11-19"
    assert row.provider == "fred"
    assert row.symbol == "DGS2"
    assert ten.price is None
    assert ten.status == "pending"
    topix = next(item for item in section.data.strip if item.name == "TOPIX")
    assert topix.status == "unavailable"
    assert topix.price is None


def test_sample_and_partial_books_do_not_publish_numbers():
    sample = _quote("^GSPC", 9999, 1.5, 10, sample=True, asset="index")
    section = build_dashboard({"^GSPC": sample}, fred=None, attempted={"^GSPC"}, macro_done=False, live=True)
    spx = next(item for item in section.data.strip if item.name == "S&P 500")
    assert spx.price is None
    assert spx.status == "unavailable"
    universe = ["AAA", "BBB", "CCC"]
    quotes = [
        _quote("AAA", 10, 5, 100),
        _quote("BBB", 10, -8, 50),
        _quote("^N225", 50000, 9, 1_000_000_000, asset="index"),
        _quote("CCC", 10, 1, 0),
    ]
    waiting = rank_movers(quotes, universe=universe, ready=False, attempted=1)
    assert waiting.active == []
    assert waiting.rise == []
    assert waiting.quoted == 3
    ready = rank_movers(quotes, universe=universe, ready=True, attempted=3)
    assert [row.symbol for row in ready.active] == ["AAA", "BBB"]
    assert [row.symbol for row in ready.rise] == ["AAA", "CCC", "BBB"]
    assert [row.symbol for row in ready.drop] == ["BBB", "CCC", "AAA"]
    assert "^N225" not in {row.symbol for row in ready.active + ready.rise + ready.drop}


def test_apply_previous_close_requires_a_real_prior():
    base = _quote("000300.SS", 3930.08, 0, 1)
    base = base.model_copy(update={"previousClose": None, "change": None, "changePct": None})
    filled = apply_previous_close(base, 3952.14)
    assert filled.previousClose == 3952.14
    assert filled.price == 3930.08
    assert filled.change is not None and filled.change < 0
    assert abs((filled.changePct or 0) - ((3930.08 - 3952.14) / 3952.14 * 100)) < 1e-9
    kept = apply_previous_close(filled, 1)
    assert kept.previousClose == 3952.14
    blank = apply_previous_close(base, None)
    assert blank.change is None
    assert apply_previous_close(base, 0).change is None


def test_dashboard_route_has_no_placeholder_prices_when_live_is_off():
    from app.main import app

    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["ok"] is True
        body = client.get("/api/dashboard")
        assert body.status_code == 200
        payload = body.json()
        assert [row["name"] for row in payload["data"]["strip"]] == [spec.name for spec in STRIP]
        assert payload["data"]["movers"]["universe"] == 462
        assert payload["data"]["movers"]["activity"] == "volume"
        assert payload["data"]["movers"]["active"] == []
        assert len(payload["data"]["fx"]) == 9
        for row in payload["data"]["strip"] + payload["data"]["fx"]:
            assert row["price"] is None
            assert row["change"] is None
            assert row["status"] == "unavailable"
        topix = next(row for row in payload["data"]["strip"] if row["name"] == "TOPIX")
        assert "Yahoo" in (topix["reason"] or "")
        sti = next(row for row in payload["data"]["strip"] if row["name"] == "Singapore STI")
        assert sti["symbol"] == "^STI"
        assert sti["price"] is None


def test_futures_change_must_match_the_published_previous_close():
    es = future_quote_from_info("ES=F", {
        "quoteType": "FUTURE",
        "shortName": "E-Mini S&P 500 Dec 26",
        "regularMarketPrice": 7085.5,
        "regularMarketPreviousClose": 6935.0,
        "regularMarketChange": 150.5,
        "currency": "USD",
        "exchange": "CME",
        "regularMarketVolume": 149759,
    })
    assert es is not None
    assert es.price == 7085.5
    assert es.previousClose == 6935.0
    assert abs((es.change or 0) - 150.5) < 1e-9
    rejected = future_quote_from_info("TPY=F", {
        "quoteType": "FUTURE",
        "regularMarketPrice": 3672.0,
        "regularMarketPreviousClose": 3672.0,
        "regularMarketChange": -148.5,
        "currency": "JPY",
    })
    assert rejected is None
    assert future_quote_from_info("ES=F", {"quoteType": "INDEX", "regularMarketPrice": 1, "previousClose": 1}) is None
    stale = future_quote_from_info("SGP-H27.SI", {
        "quoteType": "FUTURE",
        "regularMarketPrice": 472.0,
        "regularMarketPreviousClose": 445.8,
        "regularMarketChange": 26.2,
        "regularMarketTime": 1_700_000_000,
        "currency": "SGD",
    })
    assert stale is None
    assert is_future_symbol("ES=F")
    assert is_future_symbol("SGP-X26.SI")
    assert not is_future_symbol("ENR.F")
    assert not is_future_symbol("NOVO-B.CO")


def test_cash_index_row_uses_the_index_symbol():
    quote = _quote("^GSPC", 6910.39, -3.7, 0, asset="index")
    section = build_dashboard({"^GSPC": quote}, fred=None, attempted=set(market_symbols()), macro_done=True, live=True)
    row = next(item for item in section.data.strip if item.name == "S&P 500")
    assert row.status == "ok"
    assert row.symbol == "^GSPC"
    assert row.price == 6910.39
    assert "ES=F" not in {item.symbol for item in section.data.strip}
