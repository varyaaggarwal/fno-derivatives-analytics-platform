# F&O Derivatives Analytics Platform

A full-stack app for analyzing NSE index options: live option chains with
Greeks, implied volatility solved in reverse from real prices, a 3D
volatility surface, a P&L attribution tool, plain-language market
interpretation, and a live signal engine + backtester for a
SuperTrend-based options-selling strategy on Bank Nifty.

**Live app:** https://fnoderivativesanalyticsplatform.vercel.app
**API:** https://fando-derivatives-analytics-platform.onrender.com/api/health

---

## Features

- **Option chain** — real-time OI, LTP, and IV per strike, sourced from Upstox (with an NSE-scrape fallback), enriched with Delta/Gamma/Theta/Vega computed in-house
- **Implied volatility, solved not trusted** — every price gets re-run through a Black-Scholes inversion (Brent's method) rather than relying on whatever IV the feed reports
- **Volatility surface** — interactive 3D IV surface across strikes and expiries
- **P&L Decomposer** — attributes a position's P&L to Delta, Gamma, Theta, and Vega, with live sliders for index move, IV change, and time elapsed
- **Plain-language interpretation** — auto-generated cards explaining PCR, max pain, and IV spikes in normal language
- **DOS strategy engine** — a live SuperTrend-based signal, automatic strike selection, stop-loss monitoring (initial + trailing), and a historical backtester with an equity curve
- **Optional real-time feed** — a WebSocket-based live tick feed (Upstox Market Data Feed V3) as a push-based alternative to REST polling, off by default
- **Data provenance** — every response says exactly which data source served it and how fresh it is, instead of a flat "is this live" flag

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (React), TypeScript, Tailwind CSS, Recharts, Plotly.js |
| Backend | FastAPI (Python) |
| Live data | Upstox REST + WebSocket feed, NSE scrape fallback, yfinance |
| Database | Supabase (PostgreSQL) |
| Math | NumPy, pandas, SciPy |
| Deployment | Vercel (frontend), Render (backend) |
| Tests | pytest — 30 tests |

## Getting started

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python -m pytest tests/ -v          # run the test suite
python -m uvicorn main:app --reload --port 8000
```

**Frontend** (separate terminal):
```bash
cd frontend
npm install
cp .env.local.example .env.local    # set NEXT_PUBLIC_API_BASE=http://localhost:8000
npm run dev
```

Open http://localhost:3000 — five pages: Overview, Option Chain, Vol Surface,
P&L Decomposer, and DOS Strategy, all backed by the FastAPI endpoints below.
By default the backend serves realistic mock data; set `LIVE_NSE=true` and
`UPSTOX_ACCESS_TOKEN` to pull real market data.

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Liveness + current config |
| `GET /api/chain` | Option chain with Greeks |
| `GET /api/vol-surface` | IV surface across strikes and expiries |
| `GET /api/interpretation` | Plain-language market read (PCR, max pain, IV spike) |
| `GET /api/pnl-decompose` | P&L attribution by Greek for a given scenario |
| `GET /api/dos/live-signal` | Current SuperTrend signal + recommended strike |
| `GET /api/dos/sl-status` | Stop-loss status for an open position |
| `GET /api/dos/backtest` | Historical backtest, trade log + stats |
| `GET /api/dos/history` | Previously saved backtest trades |
| `GET /api/live-spot` | Push-updated spot price (when the WebSocket feed is enabled) |

## Project layout

```
backend/app/core/       Black-Scholes pricer, IV solver, P&L decomposer,
                        SuperTrend indicator, DOS strategy logic, backtester
backend/app/data/       Option chain sources (Upstox, NSE, mock), the
                        real-time WebSocket feed, market-hours/holiday
                        checks, and data-provenance helpers
backend/tests/          30 tests covering pricing correctness, IV
                        round-trips, and edge cases
frontend/app/           Next.js pages: Overview, Chain, Surface, P&L, DOS
excel_report/           Generates a supplementary Excel report
docs/                   Project write-up
render.yaml             Backend deployment config
```

## Notes on the data

- Option chain data comes from Upstox when a token is configured; NSE's own
  API blocks most cloud-hosted IPs, so it's kept as a local-only fallback.
- The historical backtest runs on statistically realistic mock intraday
  data, since free intraday options data isn't available for this
  instrument — the strategy logic itself is unchanged and ready to run
  against a real feed.
- The strategy's Wednesday/Thursday expiry cadence reflects an older
  Bank Nifty options schedule; NSE has since moved to a monthly expiry.
  The strategy logic and backtester still work exactly as designed, just
  worth knowing if you're comparing against current markets.

## Validation

- Put-call parity holds to 1e-8
- Matches a known textbook Black-Scholes reference value
- IV solver round-trips price → IV → price to 1e-4
- Full test suite passing (30/30)

## Design

Dark, trading-terminal-inspired UI — deliberately not another generic
AI-generated dashboard look. Space Grotesk for headings, monospace for every
number so strikes and Greeks line up like a real terminal.

---

📄 A one-page write-up covering the design decisions and known limitations in more depth: [`docs/ONE_PAGER.md`](docs/ONE_PAGER.md)
