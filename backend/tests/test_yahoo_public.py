"""Chart and quote-page parsers. These are the paths that still work when quoteSummary is empty."""

from __future__ import annotations

from app.services.yahoo_public import parse_quote_page, parse_timeseries_latest, quote_from_chart, session_change


def test_session_change_uses_the_prior_bar_when_it_matches_the_full_day_change():
    previous, change = session_change(7085.75, [7197.25, 6935.0, 7085.75], 150.75)
    assert previous == 6935.0
    assert abs(change - 150.75) < 1e-9


def test_session_change_uses_fullday_change_when_history_has_only_the_live_bar():
    previous, change = session_change(441.25, [441.25], -3.35)
    assert abs(previous - 444.6) < 1e-9
    assert abs(change - (-3.35)) < 1e-9


def test_session_change_leaves_the_change_blank_when_neither_source_exists():
    previous, change = session_change(100.0, [100.0], None)
    assert previous is None
    assert change is None


def test_chart_quote_keeps_the_last_price_without_a_previous_close():
    result = {
        "meta": {
            "instrumentType": "FUTURE",
            "shortName": "E-Mini S&P 500 Dec 26",
            "regularMarketPrice": 7084.0,
            "currency": "USD",
            "exchangeName": "CME",
            "regularMarketVolume": 1000,
            "regularMarketTime": 10**10,
        },
        "indicators": {"quote": [{"close": [7084.0]}]},
    }
    quote = quote_from_chart("ES=F", result, futures_only=True)
    assert quote is not None
    assert quote.price == 7084.0
    assert quote.change is None
    assert quote.previousClose is None
    assert quote_from_chart("ES=F", {"meta": {"instrumentType": "EQUITY", "regularMarketPrice": 1, "regularMarketTime": 10**10}}, futures_only=True) is None


def test_quote_page_reads_the_embedded_fundamentals():
    html = (
        r'\"forwardPE\":{\"raw\":32.400333,\"fmt\":\"32.40\"},'
        r'\"priceToBook\":{\"raw\":44.41333,\"fmt\":\"44.41\"},'
        r'\"sector\":\"Technology\",\"industry\":\"Consumer Electronics\",'
        r'\"longBusinessSummary\":\"Apple Inc. designs smartphones.\"'
    )
    fields = parse_quote_page(html)
    assert fields["forwardPE"] == 32.400333
    assert fields["priceToBook"] == 44.41333
    assert fields["sector"] == "Technology"
    assert fields["industry"] == "Consumer Electronics"
    assert fields["longBusinessSummary"].startswith("Apple Inc.")


def test_timeseries_keeps_the_latest_forward_pe_and_book_value():
    payload = {
        "timeseries": {
            "result": [
                {
                    "trailingForwardPeRatio": [
                        {"asOfDate": "2026-11-18", "reportedValue": {"raw": 30.0}},
                        {"asOfDate": "2026-11-20", "reportedValue": {"raw": 35.8423}},
                    ],
                    "trailingPbRatio": [
                        {"asOfDate": "2026-11-20", "reportedValue": {"raw": 44.41084}},
                    ],
                }
            ]
        }
    }
    assert parse_timeseries_latest(payload) == {"forwardPE": 35.8423, "priceToBook": 44.41084}
