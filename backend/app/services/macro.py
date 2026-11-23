"""FRED public CSV (or the keyed API) and the world-monitor / calendar boards."""

from __future__ import annotations

import csv
import io
import logging
from datetime import date, timedelta

import httpx

from app.schemas import EcoBoard, EcoEvent, EcoSeries, MacroPoint, Quote, WeiBoard, YieldPoint
from app.util import iso, utcnow

log = logging.getLogger(__name__)

CURVE = [
    ("DGS3MO", "US 3M", 0.25),
    ("DGS2", "US 2Y", 2.0),
    ("DGS5", "US 5Y", 5.0),
    ("DGS10", "US 10Y", 10.0),
    ("DGS30", "US 30Y", 30.0),
]
FRED_SERIES = [series for series, _, _ in CURVE] + ["T10Y2Y", "FEDFUNDS", "CPIAUCSL", "UNRATE", "PAYEMS"]
UA = "APEX Terminal research@apex-terminal.local"


def _rows(raw: list | None) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    for item in raw or []:
        if not item or len(item) < 2 or item[1] is None:
            continue
        try:
            rows.append((str(item[0]), float(item[1])))
        except (TypeError, ValueError):
            continue
    return rows


def _last_pair(rows: list[tuple[str, float]]) -> tuple[float | None, float | None]:
    if not rows:
        return None, None
    if len(rows) == 1:
        return rows[-1][1], None
    return rows[-1][1], rows[-2][1]


def _spark(rows: list[tuple[str, float]], count: int = 48) -> list[float]:
    return [value for _, value in rows[-count:]]


def _bp(last: float | None, prev: float | None) -> float | None:
    if last is None or prev is None:
        return None
    return (last - prev) * 100.0


async def fetch_fred(api_key: str | None) -> dict[str, list[list]]:
    out: dict[str, list[list]] = {}
    async with httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=4.0), follow_redirects=True, headers={"User-Agent": UA}) as client:
        for series in FRED_SERIES:
            try:
                if api_key:
                    url = "https://api.stlouisfed.org/fred/series/observations"
                    response = await client.get(
                        url,
                        params={"series_id": series, "api_key": api_key, "file_type": "json", "sort_order": "asc"},
                    )
                    response.raise_for_status()
                    rows = []
                    for obs in response.json().get("observations", []):
                        raw = obs.get("value")
                        if raw in (None, "."):
                            continue
                        rows.append([obs.get("date"), float(raw)])
                else:
                    response = await client.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}")
                    response.raise_for_status()
                    rows = []
                    reader = csv.DictReader(io.StringIO(response.text))
                    for record in reader:
                        date_key = record.get("observation_date") or record.get("DATE")
                        value = None
                        for key, raw in record.items():
                            if key and key.lower() not in {"observation_date", "date"} and raw and raw != ".":
                                value = float(raw)
                        if date_key and value is not None:
                            rows.append([date_key, value])
                if rows:
                    out[series] = rows[-800:]
            except Exception as exc:
                log.warning("fred %s failed: %s", series, exc)
    return out


def build_wei(quotes: dict[str, Quote], fred: dict[str, list], sample_macro: bool) -> WeiBoard:
    points: list[MacroPoint] = []
    for quote in quotes.values():
        if quote.symbol == "^TNX":
            continue
        points.append(
            MacroPoint(
                id=quote.symbol,
                symbol=quote.symbol,
                name=quote.name,
                group=_group(quote.assetClass),
                value=quote.price,
                change=quote.change,
                changePct=quote.changePct,
                unit="%" if quote.assetClass == "rate" else "px",
                spark=quote.sparkline[-32:],
                sample=quote.sample,
            )
        )
    curve: list[YieldPoint] = []
    for series, name, years in CURVE:
        rows = _rows(fred.get(series))
        last, prev = _last_pair(rows)
        points.append(
            MacroPoint(
                id=series,
                name=name,
                group="rate",
                value=last,
                changeBp=_bp(last, prev),
                unit="%",
                spark=_spark(rows, 64),
                sample=sample_macro,
            )
        )
        curve.append(YieldPoint(tenor=name, years=years, value=last))
    spread_rows = _rows(fred.get("T10Y2Y"))
    spread, spread_prev = _last_pair(spread_rows)
    return WeiBoard(points=points, curve=curve, spread2s10s=spread, spreadChangeBp=_bp(spread, spread_prev))


def _group(asset: str) -> str:
    if asset in {"equity", "index", "etf"}:
        return "equity"
    if asset in {"fx", "commodity", "crypto", "rate"}:
        return asset
    return "equity"


def _cpi_yoy(rows: list[tuple[str, float]]) -> tuple[float | None, float | None]:
    if len(rows) < 14:
        return None, None
    latest = rows[-1][1] / rows[-13][1] - 1
    prior = rows[-2][1] / rows[-14][1] - 1
    return latest * 100.0, prior * 100.0


def _cpi_spark(rows: list[tuple[str, float]]) -> list[float]:
    values = []
    for index in range(13, len(rows)):
        base = rows[index - 12][1]
        if base:
            values.append((rows[index][1] / base - 1) * 100.0)
    return values[-36:]


def _nfp(rows: list[tuple[str, float]]) -> tuple[float | None, float | None]:
    if len(rows) < 3:
        return None, None
    return rows[-1][1] - rows[-2][1], rows[-2][1] - rows[-3][1]


def _business_day(day: date) -> date:
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day


def _first_weekday(year: int, month: int, weekday: int) -> date:
    day = date(year, month, 1)
    while day.weekday() != weekday:
        day += timedelta(days=1)
    return day


def _shift_month(day: date, months: int) -> date:
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def _sample_consensus(actual: float | None, digits: int = 1) -> float | None:
    if actual is None:
        return None
    # A stable, obviously synthetic survey print sitting a tenth away from the actual.
    bumped = actual + (0.1 if actual >= 0 else -0.1)
    return round(bumped, digits)


def build_eco(fred: dict[str, list], sample_macro: bool) -> EcoBoard:
    today = utcnow().date()
    cpi_rows = _rows(fred.get("CPIAUCSL"))
    un_rows = _rows(fred.get("UNRATE"))
    pay_rows = _rows(fred.get("PAYEMS"))
    ff_rows = _rows(fred.get("FEDFUNDS"))
    spread_rows = _rows(fred.get("T10Y2Y"))
    cpi, cpi_prior = _cpi_yoy(cpi_rows)
    unemp, unemp_prior = _last_pair(un_rows)
    nfp, nfp_prior = _nfp(pay_rows)
    funds, funds_prior = _last_pair(ff_rows)

    events: list[EcoEvent] = []

    def add(event_id: str, when: date, clock: str, region: str, title: str, category: str, importance: str, actual, prior, unit: str, digits: int, actual_sample: bool):
        consensus = _sample_consensus(actual if actual is not None else prior, digits)
        events.append(
            EcoEvent(
                id=event_id,
                date=when.isoformat(),
                time=clock,
                region=region,
                event=title,
                category=category,  # type: ignore[arg-type]
                importance=importance,  # type: ignore[arg-type]
                consensus=consensus,
                actual=actual,
                prior=prior,
                unit=unit,
                consensusSample=consensus is not None,
                actualSample=actual_sample and actual is not None,
            )
        )

    # Most recent standard release dates, walking back until they are in the past.
    nfp_date = _first_weekday(today.year, today.month, 4)
    if nfp_date > today:
        previous = _shift_month(today, -1)
        nfp_date = _first_weekday(previous.year, previous.month, 4)
    cpi_date = _business_day(date(today.year, today.month, 12))
    if cpi_date > today:
        previous = _shift_month(today, -1)
        cpi_date = _business_day(date(previous.year, previous.month, 12))
    un_date = _first_weekday(today.year, today.month, 4)
    if un_date > today:
        previous = _shift_month(today, -1)
        un_date = _first_weekday(previous.year, previous.month, 4)
    fomc = _third_wednesday(today)
    if fomc > today:
        fomc = _third_wednesday(_shift_month(today, -1))

    add("cpi-last", cpi_date, "08:30", "US", "CPI YoY", "CPI", "high", cpi, cpi_prior, "%", 1, sample_macro)
    add("nfp-last", nfp_date, "08:30", "US", "Nonfarm payrolls", "LABOR", "high", nfp, nfp_prior, "k", 0, sample_macro)
    add("un-last", un_date, "08:30", "US", "Unemployment rate", "LABOR", "high", unemp, unemp_prior, "%", 1, sample_macro)
    add("ff-last", fomc, "14:00", "US", "Fed funds rate", "RATES", "high", funds, funds_prior, "%", 2, sample_macro)

    next_month = _shift_month(today, 1)
    add("cpi-next", _business_day(date(next_month.year, next_month.month, 12)), "08:30", "US", "CPI YoY", "CPI", "high", None, cpi, "%", 1, False)
    add("nfp-next", _first_weekday(next_month.year, next_month.month, 4), "08:30", "US", "Nonfarm payrolls", "LABOR", "high", None, nfp, "k", 0, False)
    add("fomc-next", _third_wednesday(next_month if _third_wednesday(today) <= today else today), "14:00", "US", "FOMC rate decision", "RATES", "high", None, funds, "%", 2, False)
    pmi_day = _business_day(date(next_month.year, next_month.month, 1))
    add("pmi-next", pmi_day, "10:00", "US", "ISM manufacturing PMI", "PMI", "medium", None, None, "idx", 1, False)
    # Give the PMI row a sample consensus even without an actual, near a neutral 50 handle.
    events[-1].consensus = 50.2
    events[-1].consensusSample = True
    ecb = _business_day(date(next_month.year, next_month.month, 18))
    add("ecb-next", ecb, "08:15", "EA", "ECB rate decision", "RATES", "high", None, None, "%", 2, False)
    events[-1].consensus = 2.15
    events[-1].consensusSample = True

    events.sort(key=lambda item: (item.date, item.time))
    series = [
        EcoSeries(id="cpi", name="CPI YoY", value=cpi, unit="%", change=(cpi - cpi_prior) if cpi is not None and cpi_prior is not None else None, spark=_cpi_spark(cpi_rows)),
        EcoSeries(id="unrate", name="Unemployment", value=unemp, unit="%", change=(unemp - unemp_prior) if unemp is not None and unemp_prior is not None else None, spark=_spark(un_rows, 36)),
        EcoSeries(id="nfp", name="Payrolls change", value=nfp, unit="k", change=(nfp - nfp_prior) if nfp is not None and nfp_prior is not None else None, spark=[pay_rows[i][1] - pay_rows[i - 1][1] for i in range(max(1, len(pay_rows) - 24), len(pay_rows))]),
        EcoSeries(id="ff", name="Fed funds", value=funds, unit="%", change=(funds - funds_prior) if funds is not None and funds_prior is not None else None, spark=_spark(ff_rows, 36)),
        EcoSeries(id="spread", name="2s10s", value=_last_pair(spread_rows)[0], unit="%", change=None, spark=_spark(spread_rows, 64)),
    ]
    note = (
        "CPI, unemployment, nonfarm payrolls, fed funds, and Treasury yields use FRED public series when the feed responds. "
        "Consensus prints are desk samples for layout and surprise math — not a licensed economist survey — and are flagged in the table. "
        "Release dates follow the regular statistical calendar and can shift by a session."
    )
    return EcoBoard(events=events, series=series, note=note)


def _third_wednesday(day: date) -> date:
    first = date(day.year, day.month, 1)
    # weekday(): Monday=0 ... Wednesday=2
    offset = (2 - first.weekday()) % 7
    return first + timedelta(days=offset + 14)
