"""Turn provider payloads into tear-sheet, statement, and peer models."""

from __future__ import annotations

from app.schemas import (
    AnalystView,
    CompanyEvent,
    CompanyProfile,
    Executive,
    LineItem,
    Multiple,
    OptionSnapshot,
    PeerRow,
    Quote,
    Statements,
)
from app.services.company import Turnover, dollar_volume
from app.symbols import bloomberg_label, classify, currency_for, name_for
from app.util import clean_person, num

INCOME_SPEC = [
    ("revenue", "Revenue", ["Total Revenue"], "millions", True, 0),
    ("cogs", "Cost of revenue", ["Cost Of Revenue", "Reconciled Cost Of Revenue"], "millions", False, 1),
    ("grossProfit", "Gross profit", ["Gross Profit"], "millions", True, 0),
    ("rd", "Research & development", ["Research And Development"], "millions", False, 1),
    ("sga", "SG&A", ["Selling General And Administration"], "millions", False, 1),
    ("opex", "Operating expenses", ["Operating Expense"], "millions", False, 1),
    ("operatingIncome", "Operating income", ["Operating Income"], "millions", True, 0),
    ("pretax", "Pretax income", ["Pretax Income"], "millions", False, 0),
    ("tax", "Tax provision", ["Tax Provision"], "millions", False, 1),
    ("netIncome", "Net income", ["Net Income"], "millions", True, 0),
    ("eps", "Diluted EPS", ["Diluted EPS"], "perShare", True, 0),
    ("shares", "Diluted shares (m)", ["Diluted Average Shares"], "shares", False, 0),
    ("ebitda", "EBITDA", ["EBITDA", "Normalized EBITDA"], "millions", False, 0),
]

BALANCE_SPEC = [
    ("cash", "Cash & equivalents", ["Cash And Cash Equivalents"], "millions", False, 1),
    ("receivables", "Receivables", ["Accounts Receivable", "Receivables"], "millions", False, 1),
    ("inventory", "Inventory", ["Inventory"], "millions", False, 1),
    ("currentAssets", "Current assets", ["Current Assets"], "millions", True, 0),
    ("totalAssets", "Total assets", ["Total Assets"], "millions", True, 0),
    ("currentDebt", "Current debt", ["Current Debt"], "millions", False, 1),
    ("currentLiab", "Current liabilities", ["Current Liabilities"], "millions", True, 0),
    ("longDebt", "Long-term debt", ["Long Term Debt"], "millions", False, 1),
    ("totalDebt", "Total debt", ["Total Debt"], "millions", True, 0),
    ("netDebt", "Net debt", ["Net Debt"], "millions", True, 0),
    ("equity", "Stockholders' equity", ["Stockholders Equity", "Common Stock Equity"], "millions", True, 0),
]

CASH_SPEC = [
    ("ocf", "Operating cash flow", ["Operating Cash Flow"], "millions", True, 0),
    ("capex", "Capital expenditure", ["Capital Expenditure"], "millions", False, 1),
    ("fcf", "Free cash flow", ["Free Cash Flow"], "millions", True, 0),
    ("investing", "Investing cash flow", ["Investing Cash Flow"], "millions", False, 0),
    ("financing", "Financing cash flow", ["Financing Cash Flow"], "millions", False, 0),
    ("buybacks", "Share repurchases", ["Repurchase Of Capital Stock"], "millions", False, 1),
    ("dividends", "Dividends paid", ["Common Stock Dividend Paid", "Cash Dividends Paid"], "millions", False, 1),
]


def _block_lines(block: dict | None) -> tuple[list[str], dict[str, list]]:
    if not block:
        return [], {}
    return list(block.get("periods") or []), dict(block.get("lines") or {})


def _pick(lines: dict[str, list], names: list[str]) -> list | None:
    for name in names:
        series = lines.get(name)
        if series and any(value is not None for value in series):
            return series
    return None


def _at(series: list | None, index: int) -> float | None:
    if series is None or index >= len(series):
        return None
    return num(series[index])


def _scale_money(value: float | None) -> float | None:
    if value is None:
        return None
    return value / 1_000_000.0


def _scale_shares(value: float | None) -> float | None:
    if value is None:
        return None
    if abs(value) > 1_000_000:
        return value / 1_000_000.0
    return value


def _present(series: list) -> list[float | None]:
    return [num(value) for value in series]


def _build_lines(spec, lines: dict[str, list], count: int) -> list[LineItem]:
    items: list[LineItem] = []
    for key, label, aliases, unit, bold, indent in spec:
        raw = _pick(lines, aliases)
        if raw is None:
            continue
        values: list[float | None] = []
        for index in range(count):
            value = _at(raw, index)
            if unit == "millions":
                value = _scale_money(value)
            elif unit == "shares":
                value = _scale_shares(value)
            values.append(value)
        if not any(value is not None for value in values):
            continue
        items.append(LineItem(key=key, label=label, values=values, unit="millions" if unit == "shares" else unit, bold=bold, indent=indent))
    return items


def _aligned(primary_periods: list[str], periods: list[str], series: list | None, index: int) -> float | None:
    if series is None or index >= len(primary_periods):
        return None
    wanted = primary_periods[index]
    if wanted in periods:
        return _at(series, periods.index(wanted))
    return _at(series, index)


def _pct(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator * 100.0


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def statements_from_blocks(
    symbol: str,
    currency: str,
    income_block: dict | None,
    balance_block: dict | None,
    cash_block: dict | None,
    sample: bool,
) -> Statements:
    asset = classify(symbol)
    income_periods, income_lines = _block_lines(income_block)
    balance_periods, balance_lines = _block_lines(balance_block)
    cash_periods, cash_lines = _block_lines(cash_block)
    if asset in {"index", "fx", "commodity", "crypto", "rate"} or (asset == "etf" and not income_periods):
        return Statements(
            symbol=symbol,
            currency=currency,
            periods=[],
            periodEnds=[],
            income=[],
            balance=[],
            cashflow=[],
            ratios=[],
            notes=["Operating statements are not published for this instrument."],
            sample=sample,
            applicable=False,
        )
    count = len(income_periods)
    income = _build_lines(INCOME_SPEC, income_lines, count) if count else []
    balance = _build_lines(BALANCE_SPEC, balance_lines, len(balance_periods)) if balance_periods else []
    cashflow = _build_lines(CASH_SPEC, cash_lines, len(cash_periods)) if cash_periods else []
    ratios = _ratios(income_periods, income_lines, balance_periods, balance_lines, cash_periods, cash_lines)
    labels = [f"FY{period[:4]}" for period in income_periods]
    notes = [
        f"Flow and stock lines are in millions of {currency}. EPS is as reported.",
        "ROIC ≈ operating income × (1 − effective tax rate) / (equity + total debt − cash).",
        "Net debt / EBITDA uses total debt − cash when the provider does not publish net debt.",
    ]
    if sample:
        notes.append("FIXTURE figures are a saved public snapshot and refresh when the live provider responds.")
    return Statements(
        symbol=symbol,
        currency=currency,
        periods=labels,
        periodEnds=income_periods,
        income=income,
        balance=balance,
        cashflow=cashflow,
        ratios=ratios,
        notes=notes,
        sample=sample,
        applicable=bool(income or balance or cashflow),
    )


def _ratios(income_periods, income_lines, balance_periods, balance_lines, cash_periods, cash_lines) -> list[LineItem]:
    if not income_periods:
        return []
    count = len(income_periods)

    def series(lines, *names):
        return _pick(lines, list(names))

    rev = series(income_lines, "Total Revenue")
    gross = series(income_lines, "Gross Profit")
    opinc = series(income_lines, "Operating Income")
    pretax = series(income_lines, "Pretax Income")
    tax = series(income_lines, "Tax Provision")
    net = series(income_lines, "Net Income")
    ebitda = series(income_lines, "EBITDA", "Normalized EBITDA")
    equity = series(balance_lines, "Stockholders Equity", "Common Stock Equity")
    debt = series(balance_lines, "Total Debt")
    cash = series(balance_lines, "Cash And Cash Equivalents")
    net_debt = series(balance_lines, "Net Debt")
    current_assets = series(balance_lines, "Current Assets")
    current_liab = series(balance_lines, "Current Liabilities")
    fcf = series(cash_lines, "Free Cash Flow")

    buckets = {
        "grossMargin": [],
        "operatingMargin": [],
        "netMargin": [],
        "fcfMargin": [],
        "roe": [],
        "roic": [],
        "netDebtEbitda": [],
        "currentRatio": [],
    }
    for index in range(count):
        revenue = _at(rev, index)
        gross_profit = _at(gross, index)
        operating = _at(opinc, index)
        pretax_v = _at(pretax, index)
        tax_v = _at(tax, index)
        net_v = _at(net, index)
        ebitda_v = _at(ebitda, index)
        equity_v = _aligned(income_periods, balance_periods, equity, index)
        debt_v = _aligned(income_periods, balance_periods, debt, index)
        cash_v = _aligned(income_periods, balance_periods, cash, index)
        published_net_debt = _aligned(income_periods, balance_periods, net_debt, index)
        assets_v = _aligned(income_periods, balance_periods, current_assets, index)
        liab_v = _aligned(income_periods, balance_periods, current_liab, index)
        fcf_v = _aligned(income_periods, cash_periods, fcf, index)
        tax_rate = _ratio(tax_v, pretax_v)
        nopat = operating * (1 - tax_rate) if operating is not None and tax_rate is not None else None
        invested = None
        if equity_v is not None and debt_v is not None and cash_v is not None:
            invested = equity_v + debt_v - cash_v
        net_debt_v = published_net_debt
        if net_debt_v is None and debt_v is not None and cash_v is not None:
            net_debt_v = debt_v - cash_v
        buckets["grossMargin"].append(_pct(gross_profit, revenue))
        buckets["operatingMargin"].append(_pct(operating, revenue))
        buckets["netMargin"].append(_pct(net_v, revenue))
        buckets["fcfMargin"].append(_pct(fcf_v, revenue))
        buckets["roe"].append(_pct(net_v, equity_v))
        buckets["roic"].append(_pct(nopat, invested))
        buckets["netDebtEbitda"].append(_ratio(net_debt_v, ebitda_v))
        buckets["currentRatio"].append(_ratio(assets_v, liab_v))

    spec = [
        ("grossMargin", "Gross margin", "%", "percent"),
        ("operatingMargin", "Operating margin", "%", "percent"),
        ("netMargin", "Net margin", "%", "percent"),
        ("fcfMargin", "FCF margin", "%", "percent"),
        ("roe", "ROE", "%", "percent"),
        ("roic", "ROIC", "%", "percent"),
        ("netDebtEbitda", "Net debt / EBITDA", "x", "ratio"),
        ("currentRatio", "Current ratio", "x", "ratio"),
    ]
    items: list[LineItem] = []
    for key, label, _suffix, unit in spec:
        values = buckets[key]
        if any(value is not None for value in values):
            items.append(LineItem(key=key, label=label, values=values, unit=unit, bold=key in {"roic", "netDebtEbitda"}))
    return items


def latest_ratio(statements: Statements | None, key: str) -> float | None:
    if not statements:
        return None
    for line in statements.ratios:
        if line.key == key and line.values:
            for value in reversed(line.values):
                if value is not None:
                    return value
    return None


def _clip_text(text: str, limit: int) -> str:
    """Cut on a sentence or word so the description does not end mid-word."""
    text = " ".join(text.split()).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    dot = max(cut.rfind(". "), cut.rfind("."))
    if dot >= int(limit * 0.55):
        return cut[: dot + 1]
    space = cut.rfind(" ")
    body = cut[:space] if space > 40 else cut
    return body.rstrip(" ,;:") + "…"


def revenue_growth(statements: Statements | None) -> float | None:
    if not statements:
        return None
    for line in statements.income:
        if line.key == "revenue" and len(line.values) >= 2:
            latest, prior = line.values[-1], line.values[-2]
            if latest is None or prior in (None, 0):
                return None
            return (latest - prior) / abs(prior) * 100.0
    return None


def _yield_percent(value: object) -> float | None:
    number = num(value)
    if number is None:
        return None
    if abs(number) <= 0.25:
        return number * 100.0
    return number


def _roe_percent(value: object) -> float | None:
    number = num(value)
    if number is None:
        return None
    if abs(number) <= 5:
        return number * 100.0
    return number


def multiples_from(info: dict, statements: Statements | None) -> list[Multiple]:
    free_cash = num(info.get("freeCashflow"))
    market_cap = num(info.get("marketCap"))
    fcf_yield = (free_cash / market_cap * 100.0) if free_cash and market_cap else None
    rows = [
        ("trailingPE", "Trailing P/E", num(info.get("trailingPE")), "x"),
        ("forwardPE", "Forward P/E", num(info.get("forwardPE")), "x"),
        ("peg", "PEG", num(info.get("pegRatio")), "x"),
        ("evSales", "EV/Sales", num(info.get("enterpriseToRevenue")), "x"),
        ("evEbitda", "EV/EBITDA", num(info.get("enterpriseToEbitda")), "x"),
        ("priceBook", "P/B", num(info.get("priceToBook")), "x"),
        ("fcfYield", "FCF yield", fcf_yield, "%"),
        ("roic", "ROIC", latest_ratio(statements, "roic"), "%"),
        ("netDebtEbitda", "Net debt/EBITDA", latest_ratio(statements, "netDebtEbitda"), "x"),
    ]
    return [Multiple(key=key, label=label, value=value, unit=unit) for key, label, value, unit in rows]


def peer_row(symbol: str, info: dict | None, market_cap: float | None, ytd: float | None, statements: Statements | None) -> PeerRow:
    info = info or {}
    cap = market_cap if market_cap is not None else num(info.get("marketCap"))
    return PeerRow(
        symbol=symbol,
        name=name_for(symbol, info.get("shortName") or info.get("longName")),
        label=bloomberg_label(symbol),
        marketCap=cap,
        trailingPE=num(info.get("trailingPE")),
        forwardPE=num(info.get("forwardPE")),
        evEbitda=num(info.get("enterpriseToEbitda")),
        priceBook=num(info.get("priceToBook")),
        revenueGrowth=revenue_growth(statements),
        ytd=ytd,
    )


def profile_from_parts(
    symbol: str,
    info: dict | None,
    *,
    price: float | None,
    peers: list[PeerRow],
    statements: Statements | None,
    options: OptionSnapshot | None,
    sample: bool,
    quote: Quote | None = None,
    fx: dict | None = None,
    events: list[CompanyEvent] | None = None,
    events_status: str | None = None,
    events_reason: str | None = None,
    peers_status: str | None = None,
    peers_reason: str | None = None,
    peers_source: str | None = None,
    public_summary: str | None = None,
    public_source: str | None = None,
) -> CompanyProfile:
    info = info or {}
    quote_type = str(info.get("quoteType") or "")
    asset = "future" if quote_type.upper() == "FUTURE" else classify(symbol, quote_type or None)
    currency = currency_for(symbol, info.get("currency") if isinstance(info.get("currency"), str) else None)
    name = name_for(symbol, info.get("longName") or info.get("shortName"))
    description_source = None
    summary = ""
    if public_summary:
        summary = _clip_text(public_summary, 420)
        description_source = public_source
    if not summary and not sample:
        if asset == "etf":
            summary = f"{name} is an exchange-traded fund. Operating statements are not shown for the wrapper."
        elif asset == "index":
            summary = f"{name} is a published market index tracked on the monitor."
        elif asset == "fx":
            summary = f"{name} is a spot currency or dollar index quote."
        elif asset == "future":
            summary = f"{name} is an exchange-traded futures contract. The level is the futures price."
        elif asset == "commodity":
            summary = f"{name} is a front-month commodity future."
        elif asset == "crypto":
            summary = f"{name} is a crypto-asset quoted in dollars."
        elif asset == "rate":
            summary = "US Treasury yield index. The level is the yield in percent."
        else:
            summary = "A public description was not available."
    elif not summary and sample:
        summary = "A public description loads when the live feed answers."
    summary = _clip_text(summary, 420)
    live_quote = quote is not None and not quote.sample and quote.price is not None
    if live_quote and quote is not None:
        price = quote.price
        change = quote.change
        change_pct = quote.changePct
        volume = quote.volume or num(info.get("regularMarketVolume"))
    else:
        if price is None:
            price = num(info.get("regularMarketPrice"))
        change = num(info.get("regularMarketChange"))
        change_pct = num(info.get("regularMarketChangePercent"))
        volume = num(info.get("regularMarketVolume"))
        if quote is not None and quote.sample:
            # Offline book can fill the tape. It must not invent a session change
            # that fights a live quote the desk is already showing.
            change = None
            change_pct = None
    week_high = num(info.get("fiftyTwoWeekHigh"))
    week_low = num(info.get("fiftyTwoWeekLow"))
    if week_high is None and quote is not None:
        week_high = quote.week52High
    if week_low is None and quote is not None:
        week_low = quote.week52Low
    fx = fx or {}
    if sample:
        turnover = Turnover(None, None, None, None, None, "pending", None)
    else:
        turnover = dollar_volume(
            price,
            volume,
            currency,
            usd_per_major=num(fx.get("usdPerMajor")) if fx else (1.0 if currency == "USD" else None),
            pair=str(fx.get("pair")) if fx.get("pair") else ("USD" if currency == "USD" else None),
        )
    if events_status is None:
        if events:
            events_status = "ok"
            events_reason = None
        elif sample:
            events_status = "pending"
            events_reason = None
        else:
            events_status = "unavailable"
            events_reason = events_reason or "No upcoming date in the Yahoo calendar."
    if peers_status is None:
        if sample:
            peers = []
            peers_status = "pending"
            peers_reason = None
            peers_source = None
        elif peers:
            peers_status = "ok"
            peers_source = peers_source or "Yahoo Finance recommendations"
        else:
            peers_status = "unavailable"
            peers_reason = peers_reason or "No live peer list from Yahoo Finance."
            peers_source = None
    city = info.get("city") or ""
    state = info.get("state") or ""
    country = info.get("country") or ""
    headquarters = ", ".join(part for part in [city, state, country] if isinstance(part, str) and part)
    officers = []
    for officer in info.get("companyOfficers") or []:
        if not isinstance(officer, dict):
            continue
        person = clean_person(str(officer.get("name") or ""))
        title = clean_person(str(officer.get("title") or ""))
        if person and title:
            officers.append(Executive(name=person, title=title))
    recommendation = info.get("recommendationKey")
    if isinstance(recommendation, str):
        recommendation = recommendation.replace("_", " ").upper()
    else:
        recommendation = None
    analyst = None
    if any(num(info.get(key)) is not None for key in ("targetMeanPrice", "targetHighPrice", "targetLowPrice")) or recommendation:
        count = info.get("numberOfAnalystOpinions")
        analyst = AnalystView(
            recommendation=recommendation,
            targetLow=num(info.get("targetLowPrice")),
            targetMean=num(info.get("targetMeanPrice")),
            targetHigh=num(info.get("targetHighPrice")),
            numAnalysts=int(count) if isinstance(count, (int, float)) else None,
        )
    employees = info.get("fullTimeEmployees")
    return CompanyProfile(
        symbol=symbol,
        name=name,
        label=bloomberg_label(symbol),
        assetClass=asset,
        sector=None,
        industry=None,
        summary=summary,
        website=info.get("website") if isinstance(info.get("website"), str) else None,
        employees=int(employees) if isinstance(employees, (int, float)) else None,
        headquarters=headquarters or None,
        currency=currency,
        executives=officers[:6],
        multiples=multiples_from(info, statements),
        analyst=analyst,
        peers=peers,
        options=options,
        price=price,
        change=change,
        changePct=change_pct,
        week52High=week_high,
        week52Low=week_low,
        volume=volume,
        turnoverLocal=turnover.local,
        turnoverCurrency=turnover.local_currency,
        turnoverUsd=turnover.usd,
        fxPair=turnover.pair,
        fxRate=turnover.fx_rate,
        turnoverStatus=turnover.status,  # type: ignore[arg-type]
        turnoverReason=turnover.reason,
        forwardPE=num(info.get("forwardPE")),
        priceToBook=num(info.get("priceToBook")),
        taxonomyLabel=None,
        taxonomySource=None,
        gicsCode=None,
        descriptionSource=description_source,
        events=events or [],
        eventsStatus=events_status,  # type: ignore[arg-type]
        eventsReason=events_reason,
        peersStatus=peers_status,  # type: ignore[arg-type]
        peersReason=peers_reason,
        peersSource=peers_source,
        marketCap=num(info.get("marketCap")),
        enterpriseValue=num(info.get("enterpriseValue")),
        beta=num(info.get("beta")),
        dividendYield=_yield_percent(info.get("dividendYield")),
        eps=num(info.get("trailingEps")),
        revenue=num(info.get("totalRevenue")),
        netIncome=None,
        sample=sample,
    )


def option_from_dict(payload: dict | None, sample: bool) -> OptionSnapshot | None:
    if not payload or not payload.get("expiry"):
        return None

    def maybe_iv(value: object) -> float | None:
        number = num(value)
        if number is None:
            return None
        return number * 100.0 if abs(number) <= 3 else number

    return OptionSnapshot(
        expiry=str(payload["expiry"]),
        underlying=num(payload.get("underlying")),
        atmStrike=num(payload.get("atmStrike")),
        callLast=num(payload.get("callLast")),
        putLast=num(payload.get("putLast")),
        callIV=maybe_iv(payload.get("callIV")),
        putIV=maybe_iv(payload.get("putIV")),
        callOI=num(payload.get("callOI")),
        putOI=num(payload.get("putOI")),
        sample=sample,
    )
