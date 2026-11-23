"""Company view: dollar turnover, calendar, and live peers. No invented GICS codes."""

from __future__ import annotations

from datetime import date

from app.services.company import dollar_volume, live_peer, peer_rows, upcoming_events
from app.services.normalize import profile_from_parts


def test_sample_profile_does_not_publish_a_turnover_or_a_session_change():
    from app.schemas import Quote

    quote = Quote(
        symbol="MSFT",
        name="Microsoft",
        label="MSFT US",
        assetClass="equity",
        currency="USD",
        exchange="NASDAQ",
        price=484.52,
        change=2.8,
        changePct=0.59,
        volume=56_000_000,
        status="ok",
        sample=True,
        asOf="2026-11-23T00:00:00+00:00",
    )
    profile = profile_from_parts(
        "MSFT",
        {},
        price=quote.price,
        quote=quote,
        peers=[],
        statements=None,
        options=None,
        sample=True,
    )
    assert profile.sample is True
    assert profile.changePct is None
    assert profile.turnoverUsd is None
    assert profile.turnoverStatus == "pending"
    long = "Apple Inc. designs devices. " + ("word " * 400)
    clipped = profile_from_parts(
        "AAPL",
        {"longBusinessSummary": long, "currency": "USD", "quoteType": "EQUITY"},
        price=1,
        peers=[],
        statements=None,
        options=None,
        sample=False,
        peers_status="unavailable",
        events=[],
        events_status="unavailable",
    )
    assert clipped.summary.endswith(".") or clipped.summary.endswith("…")
    assert not clipped.summary.endswith(" w")
    assert len(clipped.summary) <= 901


def test_hkd_and_pence_turnover_use_a_real_fx_rate():
    hkd = dollar_volume(336.8, 100, "HKD", usd_per_major=0.1276, pair="HKDUSD=X")
    assert hkd.status == "ok"
    assert hkd.usd is not None
    assert abs(hkd.usd - 336.8 * 100 * 0.1276) < 1e-6
    pence = dollar_volume(1234, 10, "GBp", usd_per_major=1.3112, pair="GBPUSD=X")
    assert pence.status == "ok"
    assert pence.local_currency == "GBP"
    assert pence.usd is not None
    assert abs(pence.usd - (1234 / 100) * 10 * 1.3112) < 1e-6
    missing = dollar_volume(3312, 100, "JPY", usd_per_major=None, pair=None)
    assert missing.status == "unavailable"
    assert missing.usd is None
    assert missing.local is not None
    blank = dollar_volume(None, 100, "USD", usd_per_major=1, pair="USD")
    assert blank.status == "unavailable"
    assert blank.usd is None


def test_upcoming_events_drop_dates_already_past():
    events = upcoming_events(
        {"Ex-Dividend Date": "2026-05-15", "Earnings Date": "2026-11-18", "Dividend Date": "2027-03-30"},
        [{"date": "2026-11-18", "epsEstimate": 7.21}, {"date": "2027-03-17", "epsEstimate": 6.31}],
        date(2026, 11, 23),
    )
    assert [(event.kind, event.date) for event in events] == [("earnings", "2027-03-17"), ("dividend", "2027-03-30")]
    earnings = next(event for event in events if event.kind == "earnings")
    assert earnings.detail == "EPS est 6.31"
    assert upcoming_events({}, [], date(2026, 11, 23)) == []


def test_profile_labels_yahoo_taxonomy_and_does_not_invent_gics():
    profile = profile_from_parts(
        "AAPL",
        {
            "longName": "Apple Inc.",
            "longBusinessSummary": "Apple Inc. designs smartphones.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "currency": "USD",
            "quoteType": "EQUITY",
            "forwardPE": 32.4,
            "priceToBook": 44.4,
            "regularMarketPrice": 342.56,
            "regularMarketVolume": 1000,
            "fiftyTwoWeekHigh": 360.83,
            "fiftyTwoWeekLow": 243.42,
        },
        price=342.56,
        peers=[],
        statements=None,
        options=None,
        sample=False,
        peers_status="unavailable",
        peers_reason="Yahoo did not list peers for this symbol.",
        events=[],
        events_status="unavailable",
        events_reason="No upcoming date in the Yahoo calendar.",
    )
    assert profile.forwardPE == 32.4
    assert profile.priceToBook == 44.4
    assert profile.week52High == 360.83
    assert profile.week52Low == 243.42
    assert profile.taxonomyLabel == "Technology · Consumer Electronics"
    assert "GICS" in profile.taxonomySource
    assert "Yahoo Finance" in profile.taxonomySource
    assert profile.gicsCode is None
    assert profile.descriptionSource == "Yahoo Finance business summary"
    assert "Bloomberg" not in profile.summary
    assert profile.turnoverStatus == "ok"
    assert profile.turnoverUsd == 342.56 * 1000
    assert profile.peers == []
    assert profile.peersStatus == "unavailable"
    assert profile.peersSource is None
    peer = live_peer({"symbol": "MSFT", "regularMarketPrice": 400, "shortName": "Microsoft", "forwardPE": 30, "priceToBook": 10, "regularMarketChangePercent": 1.2, "currency": "USD"})
    assert peer is not None
    assert peer.price == 400
    assert peer.forwardPE == 30
    assert peer.changePct == 1.2
    assert peer_rows([{"symbol": "MSFT"}]) == []
