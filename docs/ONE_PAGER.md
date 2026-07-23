# F&O Derivatives Analytics Platform — One-Pager

**Repo:** github.com/varyaaggarwal/fno-derivatives-analytics-platform
**Live app:** fnoderivativesanalyticsplatform.vercel.app
**API:** fando-derivatives-analytics-platform.onrender.com/api/health

## What this is

A full-stack platform that pulls option-chain data (NSE/Upstox), prices
options and Greeks with Black-Scholes, solves implied volatility in
reverse, renders the volatility surface, decomposes position P&L by Greek,
explains the option chain in plain language, and runs a live signal engine
plus historical backtester for a SuperTrend-based options-selling strategy
("DOS") on Bank Nifty weekly-expiry options.

## Tech stack

| Layer | Technology | Role |
|---|---|---|
| Frontend | Next.js 14 (React 18) + TypeScript, Tailwind, Recharts, Plotly.js | Option chain UI, charts, 3D vol surface, DOS panel |
| Backend | FastAPI (Python), Uvicorn | REST API, Greeks engine, IV solver, P&L decomposer |
| Live data | Upstox API v2 (REST) + Market Data Feed V3 (WebSocket, protobuf), NSE scrape fallback, yfinance | Option chain, spot price, real-time ticks |
| Database | Supabase (PostgreSQL) | Chain snapshot cache, trade log |
| Math | NumPy, pandas, SciPy (Brent's method) | BSM pricing, IV solving, Greeks, SuperTrend |
| Deploy | Vercel (frontend), Render (backend) | Hosting |
| Testing | pytest | 30 tests across 6 files |

## What's implemented

| Feature | Where |
|---|---|
| Live option chain: OI, LTP, IV per strike | `/api/chain`, `upstox_chain.py` |
| Greeks (Delta/Gamma/Theta/Vega) via Black-Scholes | `black_scholes.py` |
| IV solver (reverse Black-Scholes, Brent's method) | `iv_solver.py` |
| Volatility surface (3D, strike × expiry) | `/api/vol-surface`, `VolSurface3D.tsx` |
| Interactive P&L decomposer by Greek | `pnl_decomposer.py`, `/pnl` |
| Plain-language cards (PCR, max pain, IV spike) | `interpretation.py` |
| Live SuperTrend signal + strike selector (DOS) | `dos_strategy.py`, `/api/dos/live-signal` |
| Stop-loss monitor (initial + trailing) | `/api/dos/sl-status` |
| Historical backtest + equity curve | `backtester.py`, `/api/dos/backtest` |
| Trade log persisted to a database | `supabase_client.py` |
| Deployed, working full stack | Vercel + Render |

## A few things beyond the basics

- **Real-time WebSocket feed** — a protobuf-decoded live tick feed from Upstox as an opt-in, push-based alternative to REST polling, with graceful handling of an expired/invalid token (backs off cleanly instead of retrying forever).
- **Data provenance** — every chain response carries a structured object describing exactly which data source served it, when it was captured, and how stale it is — not just a flat mock/live flag.
- **Holiday-aware market hours** — the background poller checks NSE's actual trading-holiday calendar, not just weekday + clock time.
- **Infrastructure as code** and a small frontend keep-alive hook to avoid free-tier cold starts during a live demo.
- 30 automated tests covering pricing correctness, IV round-trips, edge cases, and failure handling.

## Design decisions & known limitations

- The DOS strategy's Wed/Thu weekly-expiry cadence was implemented exactly as specified, but no longer reflects live NSE mechanics as of mid-2026 — Bank Nifty weekly options were discontinued in late 2024, leaving only a monthly expiry. Flagged here rather than hidden.
- Implied volatility is solved independently (Brent's method against the observed price) rather than trusted from whatever the feed reports.
- The historical backtest runs on statistically realistic mock intraday candles, since free NSE data has no intraday history for the instrument — swappable for a paid vendor feed without touching the strategy logic itself.
- Backtest option premiums are priced at a flat assumed IV (14%), stated explicitly.
- Stated assumptions: same-day expiry for both weekly sessions, standard Bank Nifty lot size, a 6.5% risk-free rate.

## Validation performed

- Put-call parity holds to within 1e-8.
- Matches a known textbook Black-Scholes example (S=42, K=40, r=10%, σ=20%, T=0.5y → C≈4.76).
- The IV solver round-trips: price → solved IV recovers the input volatility to 1e-4.
- Deep in/out-of-the-money delta sanity checks (→1 / →0).
- Full automated test suite: 30/30 passing.
