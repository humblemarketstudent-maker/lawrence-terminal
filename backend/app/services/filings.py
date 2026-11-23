"""SEC EDGAR submissions. Requires a descriptive User-Agent per the SEC fair-access policy."""

from __future__ import annotations

import logging
import time

import httpx

from app.book import FORM_TITLES
from app.schemas import Filing

log = logging.getLogger(__name__)

_TICKERS: dict[str, str] | None = None
_TICKERS_AT = 0.0


async def _ticker_map(client: httpx.AsyncClient) -> dict[str, str]:
    global _TICKERS, _TICKERS_AT
    if _TICKERS and time.time() - _TICKERS_AT < 24 * 3600:
        return _TICKERS
    response = await client.get("https://www.sec.gov/files/company_tickers.json")
    response.raise_for_status()
    mapping: dict[str, str] = {}
    for row in response.json().values():
        if isinstance(row, dict) and row.get("ticker"):
            mapping[str(row["ticker"]).upper()] = str(row["cik_str"]).zfill(10)
    _TICKERS = mapping
    _TICKERS_AT = time.time()
    return mapping


def _us_ticker(symbol: str) -> str | None:
    if not symbol or symbol.startswith("^") or any(ch in symbol for ch in ".="):
        return None
    return symbol.replace(".", "-")


async def fetch_filings(symbol: str, user_agent: str) -> list[Filing]:
    ticker = _us_ticker(symbol)
    if not ticker:
        return []
    headers = {"User-Agent": user_agent, "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=4.0), follow_redirects=True, headers=headers) as client:
        mapping = await _ticker_map(client)
        cik = mapping.get(ticker.upper())
        if not cik:
            return []
        response = await client.get(f"https://data.sec.gov/submissions/CIK{cik}.json")
        response.raise_for_status()
        recent = response.json().get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    docs = recent.get("primaryDocument", [])
    descriptions = recent.get("primaryDocDescription", [])
    cik_int = str(int(cik))
    filings: list[Filing] = []
    for form, filed, accession, doc, desc in zip(forms, dates, accessions, docs, descriptions):
        if form not in {"10-K", "10-Q", "8-K", "4"}:
            continue
        description = str(desc or "").strip()
        if description.upper() in {form.upper(), f"FORM {form}".upper(), ""}:
            description = FORM_TITLES.get(form, form)
        acc = str(accession)
        url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc.replace('-', '')}/{doc}"
        filings.append(
            Filing(
                symbol=symbol,
                form=form,
                filed=str(filed),
                description=description,
                accession=acc,
                url=url,
                sample=False,
            )
        )
        if len(filings) >= 12:
            break
    return filings
