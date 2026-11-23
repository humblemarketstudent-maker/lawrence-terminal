"""Desk behavior that must work with the fixture book and no network."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.cache import TTLCache
from app.sentiment import score_text
from app.services.normalize import statements_from_blocks
from app.symbols import normalize_symbol


def test_normalize_symbol_accepts_bloomberg_codes():
    assert normalize_symbol("aapl us") == "AAPL"
    assert normalize_symbol("700 HK") == "0700.HK"
    assert normalize_symbol("^hsi") == "^HSI"
    assert normalize_symbol("ASML NA") == "ASML.AS"
    assert normalize_symbol("USDHKD=X") == "USDHKD=X"


def test_sentiment_flags_guidance_and_rate_cuts():
    bearish = score_text("Apple cuts guidance amid weak demand")
    assert bearish["sentiment"] == "BEARISH"
    assert "guidance" in bearish["keywords"]
    bullish = score_text("Nvidia beats estimates and raises guidance")
    assert bullish["sentiment"] == "BULLISH"
    assert "guidance" in bullish["keywords"]


def test_cache_serves_stale_values():
    cache = TTLCache()
    cache.set("a", {"n": 1}, ttl=0.01)
    import time

    time.sleep(0.02)
    assert cache.get("a") is None
    stale = cache.get("a", allow_stale=True)
    assert stale is not None
    assert stale.fresh is False
    assert stale.value == {"n": 1}


def test_roic_uses_nopat_over_invested_capital():
    income = {
        "periods": ["2024-09-30", "2025-09-30"],
        "lines": {
            "Total Revenue": [1000, 1100],
            "Gross Profit": [400, 500],
            "Operating Income": [200, 250],
            "Pretax Income": [200, 250],
            "Tax Provision": [40, 50],
            "Net Income": [160, 200],
            "EBITDA": [300, 360],
        },
    }
    balance = {
        "periods": ["2024-09-30", "2025-09-30"],
        "lines": {
            "Stockholders Equity": [500, 550],
            "Total Debt": [200, 180],
            "Cash And Cash Equivalents": [50, 40],
            "Current Assets": [300, 320],
            "Current Liabilities": [150, 160],
        },
    }
    cash = {"periods": ["2024-09-30", "2025-09-30"], "lines": {"Free Cash Flow": [120, 140]}}
    statements = statements_from_blocks("TEST", "USD", income, balance, cash, sample=True)
    roic = next(line for line in statements.ratios if line.key == "roic")
    leverage = next(line for line in statements.ratios if line.key == "netDebtEbitda")
    assert abs(roic.values[-1] - (200 / 690 * 100)) < 0.05
    assert abs(leverage.values[-1] - (140 / 360)) < 0.01
    assert statements.income[0].key == "revenue"


def test_bootstrap_paints_the_desk():
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/api/bootstrap", params={"symbol": "AAPL US", "range": "1Y"})
        assert response.status_code == 200
        body = response.json()
        symbols = [quote["symbol"] for quote in body["quotes"]["data"]]
        for required in ["AAPL", "MSFT", "NVDA", "0700.HK", "9988.HK", "2330.TW", "^HSI", "^N225", "^NSEI", "RELIANCE.NS"]:
            assert required in symbols
        profile = body["bundle"]["profile"]["data"]
        assert profile["symbol"] == "AAPL"
        assert profile["summary"]
        assert profile["multiples"]
        assert profile["executives"]
        revenue = next(line for line in body["bundle"]["statements"]["data"]["income"] if line["key"] == "revenue")
        assert any(value for value in revenue["values"])
        assert body["bundle"]["history"]["data"]["bars"]
        assert body["news"]["data"]
        sources = {item["source"] for item in body["news"]["data"]}
        assert {"REUTERS", "BLOOMBERG", "WSJ", "YAHOO"} <= sources
        assert body["wei"]["data"]["points"]
        assert body["wei"]["data"]["curve"]
        assert body["eco"]["data"]["events"]
        assert body["bundle"]["filings"]["data"]
        apple = next(quote for quote in body["quotes"]["data"] if quote["symbol"] == "AAPL")
        last = body["bundle"]["history"]["data"]["bars"][-1]["close"]
        assert abs(apple["price"] - last) < 0.05

        chart = client.get("/api/history/AAPL", params={"range": "1D"})
        assert chart.status_code == 200
        assert len(chart.json()["data"]["bars"]) >= 4

        brief = client.post("/api/brief", json={"symbols": ["AAPL", "NVDA", "SPY"]})
        assert brief.status_code == 200
        text = brief.json()["markdown"]
        assert "MORNING BRIEF" in text
        assert "RATES" in text
        assert "TOP HEADLINES" in text

        found = client.get("/api/search", params={"q": "tencent"})
        assert any(row["symbol"] == "0700.HK" for row in found.json()["results"])

        wire = client.get("/api/news", params={"symbol": "AAPL"})
        assert wire.status_code == 200
        assert wire.json()["data"]
