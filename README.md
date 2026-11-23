# APEX Terminal

A dark, keyboard-driven market workstation. One screen holds a watchlist, a command-selected function, and a multi-source news wire. Quotes, charts, financials, filings, and macro series render from a saved market snapshot immediately, then refresh from public feeds when they respond.

## Run it

Requires Python 3.12 and Node 22.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8741 --reload
```

```bash
cd frontend
npm install
npm run dev
```

Open [http://127.0.0.1:4317](http://127.0.0.1:4317). The Vite server proxies `/api` to the API on port 8741.

`scripts/dev.sh` starts both. Docker Compose builds the same pair:

```bash
docker compose up --build
```

The desk is also at [http://127.0.0.1:4317](http://127.0.0.1:4317). API docs are at [http://127.0.0.1:8741/docs](http://127.0.0.1:8741/docs).

Copy `.env.example` to `.env` only if you want to change the provider or add keys. The default configuration needs none.

## Command bar

Focus it with `/`. Examples:

| Command | Panel |
| --- | --- |
| `AAPL US <DES>` | Tear sheet: business summary, officers, multiples, peers, ATM options |
| `AAPL US <GP>` | Candles or line, volume, SMA 20/50/200, RSI, MACD, VWAP, compare mode |
| `AAPL US <FA>` | Income, balance, cash flow, ratios, YoY toggle, CSV export |
| `AAPL US <N>` | Ticker news across Reuters, Bloomberg, WSJ, and Yahoo Finance |
| `AAPL US <FIL>` | Recent SEC 10-K, 10-Q, 8-K, and Form 4 filings |
| `<WEI>` | S&P 500, Nasdaq, Dow, Hang Seng, Nikkei, FTSE, DAX, Treasuries, DXY, WTI, gold, bitcoin |
| `<ECO>` | CPI, payrolls, unemployment, FOMC / ECB, PMI — consensus, actual, prior |
| `<BRIEF>` | Copy-ready morning note from the current book |

`700 HK` normalizes to `0700.HK`. `ASML NA` normalizes to `ASML.AS`. Indexes and futures keep their Yahoo symbols (`^HSI`, `GC=F`, `USDHKD=X`).

## Keys

| Key | Action |
| --- | --- |
| `/` | Focus the command bar |
| `1`–`4` | Layout: focus, two columns, three columns, 2×2 |
| `R` | Force-refresh quotes, news, macro, and the active symbol |
| `Esc` | Close the reader, brief, or help |
| `?` | Shortcut card |

Clicking a watchlist row or a headline ticker pushes that symbol into every linked panel. The status bar `LINK` toggle stops the push. Layouts are resizable. On a narrow screen the desk collapses to Watch / Desk / Wire.

The default book is `SPY QQQ NVDA AAPL MSFT 0700.HK 9988.HK ^HSI GC=F ^TNX`. Add any of those styles from the watchlist field. The list is stored in the browser.

## Data and adapters

`DATA_PROVIDER` selects the quote source. `yfinance` is the default and also the fallback when a keyed provider misses a symbol or a field. History and statements stay on yfinance. Macro prefers the FRED observations API when `FRED_API_KEY` is set, otherwise the public FRED CSV. News is RSS only (Google News site queries for Reuters, Bloomberg, WSJ, and Yahoo Finance, plus the publisher link). Filings use the SEC submissions API with `SEC_USER_AGENT`.

Nothing in the repo is a secret. Do not commit a filled-in `.env`.

Each payload carries `source` (`live`, `cache`, or `fixture`), `asOf`, and `stale`. If a feed times out, the last cached payload is served and the UI keeps the previous panel instead of going blank. A snapshot checked into `backend/app/fixtures/snapshot.json` is the offline book, so the first paint is populated even before the network returns. Refresh that file with:

```bash
cd backend && .venv/bin/python scripts/snapshot_fixtures.py
```

Sentiment tags are a transparent keyword score on the headline and RSS snippet. They are not a forecast. Consensus figures on the calendar are marked `SMP` unless you attach a licensed survey; actuals for CPI, payrolls, unemployment, fed funds, and the Treasury curve come from FRED when that feed answers. Article text is the RSS snippet plus an outbound link. The app does not scrape paywalled bodies.

Quotes from yfinance are unofficial and often delayed. This is a research terminal, not an execution system.

## Tests

```bash
cd backend && .venv/bin/pytest
cd frontend && npx tsc -b --noEmit
```

## Layout

```
backend/app
  adapters/     yfinance plus optional Finnhub, FMP, Alpha Vantage, Twelve Data
  services/     statements, news, filings, FRED, morning brief
  book.py       snapshot and builtin fallback
  main.py       FastAPI routes
frontend/src
  components/   command bar, watchlist, chart, tear sheet, financials, wire
  context/      linked symbol, polling, shortcuts
```
