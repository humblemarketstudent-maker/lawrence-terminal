"""APEX Terminal HTTP API."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app.bars import RANGES
from app.services.terminal import get_terminal
from app.symbols import normalize_symbol

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

log = logging.getLogger("apex")


def _frontend_dist() -> Path | None:
    """Locate a Vite production build if this process should serve the desk UI."""
    candidates: list[Path] = []
    env = os.getenv("FRONTEND_DIST")
    if env:
        candidates.append(Path(env))
    here = Path(__file__).resolve()
    # Repo layout: <root>/backend/app/main.py -> <root>/frontend/dist
    if len(here.parents) >= 3:
        candidates.append(here.parents[2] / "frontend" / "dist")
    # Flattened image layout: /app/app/main.py -> /app/frontend/dist
    if len(here.parents) >= 2:
        candidates.append(here.parents[1] / "frontend" / "dist")
        candidates.append(here.parents[1] / "static")
    seen: set[Path] = set()
    for path in candidates:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if (resolved / "index.html").is_file():
            return resolved
    return None


FRONTEND_DIST = _frontend_dist()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    terminal = get_terminal()
    import asyncio

    task = asyncio.create_task(terminal.warm_loop())
    try:
        yield
    finally:
        terminal._stop.set()
        task.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await task


app = FastAPI(title="APEX Terminal", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RefreshBody(BaseModel):
    symbols: list[str] = Field(default_factory=list)
    scope: str = "all"
    range: str = "1Y"


class BriefBody(BaseModel):
    symbols: list[str] = Field(default_factory=list)


def _range(value: str) -> str:
    key = (value or "1Y").upper()
    if key not in RANGES:
        raise HTTPException(status_code=400, detail=f"range must be one of {', '.join(RANGES)}")
    return key


@app.exception_handler(Exception)
async def unhandled(_request, exc: Exception):
    if isinstance(exc, HTTPException):
        raise exc
    log.exception("unhandled error")
    return JSONResponse(status_code=500, content={"error": "internal", "detail": "The terminal hit an unexpected error. Cached data is unchanged."})


@app.get("/")
def root():
    if FRONTEND_DIST:
        return FileResponse(FRONTEND_DIST / "index.html")
    return {"service": "apex-terminal", "docs": "/docs", "health": "/api/health"}


@app.get("/api/health")
def health():
    terminal = get_terminal()
    return {"ok": True, "service": "apex-terminal", **terminal.provider_status()}


@app.get("/api/bootstrap")
async def bootstrap(symbol: str = "AAPL", range_key: str = Query("1Y", alias="range")):
    return get_terminal().bootstrap(symbol, _range(range_key))


@app.get("/api/symbol/{symbol}")
async def symbol_bundle(symbol: str, range_key: str = Query("1Y", alias="range"), force: bool = False):
    terminal = get_terminal()
    key = normalize_symbol(symbol) or "AAPL"
    selected = _range(range_key)
    if force:
        await terminal.refresh_symbol(key, selected)
    return terminal.bundle(key, selected)


@app.get("/api/quotes")
def quotes(symbols: str = "AAPL"):
    parsed = [part.strip() for part in symbols.split(",") if part.strip()]
    return get_terminal().quote_section(parsed or ["AAPL"])


@app.get("/api/history/{symbol}")
async def history(symbol: str, range_key: str = Query("1Y", alias="range")):
    terminal = get_terminal()
    key = normalize_symbol(symbol)
    if not key:
        raise HTTPException(status_code=400, detail="symbol is required")
    selected = _range(range_key)
    terminal.hot.add(key)
    terminal._kick(f"h:{key}:{selected}", lambda: terminal.refresh_history(key, selected))
    return terminal.history_section(key, selected)


@app.get("/api/news")
async def news(symbol: str | None = None):
    terminal = get_terminal()
    key = normalize_symbol(symbol) if symbol else None
    terminal._kick("news" if not key else f"news:{key}", lambda: terminal.refresh_news(key))
    return terminal.news_section(key)


@app.get("/api/dashboard")
async def dashboard():
    terminal = get_terminal()
    if not terminal._macro_done:
        terminal._kick("macro", terminal.refresh_macro)
    return terminal.dashboard_section()


@app.get("/api/wei")
async def wei():
    terminal = get_terminal()
    terminal._kick("macro", terminal.refresh_macro)
    return terminal.wei_section()


@app.get("/api/eco")
async def eco():
    terminal = get_terminal()
    terminal._kick("macro", terminal.refresh_macro)
    return terminal.eco_section()


@app.get("/api/filings/{symbol}")
async def filings(symbol: str):
    terminal = get_terminal()
    key = normalize_symbol(symbol)
    if not key:
        raise HTTPException(status_code=400, detail="symbol is required")
    terminal._kick(f"f:{key}", lambda: terminal.refresh_filings(key))
    return terminal.filings_section(key)


@app.get("/api/search")
def search(q: str = ""):
    return {"results": get_terminal().search(q)}


@app.post("/api/refresh")
async def refresh(body: RefreshBody):
    scope = body.scope if body.scope in {"all", "quotes", "news", "macro", "fundamentals"} else "all"
    return await get_terminal().force_refresh(body.symbols, scope, _range(body.range))


@app.post("/api/brief")
def brief(body: BriefBody):
    return get_terminal().brief(body.symbols)


if FRONTEND_DIST:

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        root = FRONTEND_DIST.resolve()
        target = (root / full_path).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            raise HTTPException(status_code=404, detail="Not found")
        if full_path and target.is_file():
            return FileResponse(target)
        return FileResponse(root / "index.html")
