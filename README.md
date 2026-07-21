# F&O Derivatives Analytics Platform

AlgoLabs Assignment 2. Full-stack: FastAPI backend wrapping the pricing/DOS
engine, Next.js frontend consuming it. Live NSE integration and deployment
are the remaining steps — see "Manual steps to go live" below.

## Run it locally

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python -m pytest tests/ -v          # validate the pricing/IV engine first
python -m uvicorn main:app --reload --port 8000
```

**Frontend** (separate terminal):
```bash
cd frontend
npm install
cp .env.local.example .env.local    # NEXT_PUBLIC_API_BASE=http://localhost:8000
npm run dev
```
Open http://localhost:3000 — Overview, Option Chain, Vol Surface, P&L
Decomposer, and DOS Strategy pages, all backed by the live FastAPI endpoints
(currently serving mock NSE-shaped data, see below).

## What's here

```
backend/app/core/
  black_scholes.py    Vectorized BSM pricer + Greeks (Delta, Gamma, Theta, Vega, Rho)
  iv_solver.py         Reverse-BSM IV solver via scipy.optimize.brentq
  pnl_decomposer.py    Taylor-expansion P&L attribution (Delta/Gamma/Theta/Vega + residual)
  interpretation.py    PCR / Max Pain / IV-spike plain-language cards
  supertrend.py         SuperTrend(period, multiplier) indicator
  dos_strategy.py       DOS signal, strike selection, SL rules (per assignment spec)
  backtester.py         Runs DOS across historical sessions, produces trade log + stats

backend/app/data/
  mock_option_chain.py  NSE-shaped mock option chain + multi-expiry vol surface
  mock_bnf_candles.py   Mock 5-min BNF futures candles (see "Data notes" below)
  live_nse_chain.py     Direct NSE scrape (curl_cffi) -- fallback backend, blocked on most cloud IPs
  upstox_chain.py       Upstox API v2 option chain fetcher -- PREFERRED live backend on a deployed server
  data_source.py         Router: picks upstox_chain.py if UPSTOX_ACCESS_TOKEN is set, else live_nse_chain.py

backend/tests/
  test_black_scholes.py  Put-call parity, known BSM value, IV round-trip, Greek sanity checks
  test_upstox_chain.py   Upstox normalizer (mocked response, no live call) + data_source routing logic

excel_report/
  generate_excel_report.py  Builds FnO_Analytics_Report.xlsx (chain+Greeks, vol smile/surface,
                             interpretation cards, P&L decomposition, DOS backtest + equity curve)

backend/main.py
  FastAPI app: /api/chain, /api/vol-surface, /api/interpretation,
  /api/pnl-decompose, /api/dos/backtest, /api/dos/live-signal.
  LIVE_NSE=true env var switches from mock to app/data/data_source.py, which
  fetches from Upstox if UPSTOX_ACCESS_TOKEN is set (the deployed-backend
  path -- doesn't get IP-blocked like NSE does) or falls back to
  live_nse_chain.py's direct NSE scrape otherwise.

frontend/
  Next.js 14 + Tailwind + Recharts. Dark trading-terminal design (see
  "Design system" below). Pages: Overview (/), Option Chain (/chain),
  Vol Surface (/surface), P&L Decomposer (/pnl), DOS Strategy (/dos).
```

## Run it

```bash
cd backend
pip install -r requirements.txt
python -m pytest tests/ -v          # validate the pricing/IV engine
cd ../excel_report
python generate_excel_report.py     # regenerate the Excel report
```

## Data notes (read before the viva)

- **Option chain**: mocked with NSE-matching field names (`strikePrice`,
  `openInterest`, `lastPrice`, `impliedVolatility` conceptually — flattened
  here to `strike`, `open_interest`, `last_price`, `implied_volatility`).
  Live data comes from Upstox's API v2 (`app/data/upstox_chain.py`) when
  `UPSTOX_ACCESS_TOKEN` is set — NSE's own API blocks/rate-limits most
  cloud-provider IPs (including Render's), so Upstox is the backend that
  actually works once deployed; `live_nse_chain.py` stays in the codebase as
  a fallback for local/non-cloud runs. Both normalize to the exact same flat
  schema, so nothing in `app/core/` changes either way.
- **DOS backtest**: NSE's live option-chain API is a snapshot only, and the
  Bhav Copy is end-of-day only — neither has 5-min intraday history for BNF
  futures. The backtester runs against **statistically realistic mock 5-min
  candles** (correct trading hours, correct intraday vol) so the SuperTrend/
  DOS logic is fully built and testable now. For a real backtest, source
  5-min BNF futures history from a vendor (Kite Connect historical API,
  Global Datafeeds) and feed it into `run_backtest()` unchanged.
- **Backtest option pricing**: since no historical options premium feed
  exists either, the sold CE/PE premium is priced via the same BSM engine at
  a flat assumed IV (14%) — stated explicitly rather than hidden. Swap
  `ASSUMED_IV` in `backtester.py` for a live IV lookup once you have one.
- **Assumptions to state in the one-pager**: same-day (0DTE) expiry for both
  Wed and Thu sessions, BNF lot size 15, risk-free rate 6.5%.

## Validation performed

- Put-call parity identity holds to 1e-8.
- Matches Hull's textbook BSM example (S=42, K=40, r=10%, σ=20%, T=0.5y → C≈4.76).
- IV solver round-trips: price → solve IV → recovers input σ to 1e-4.
- Deep ITM/OTM delta sanity (→1 / →0).
- Excel workbook has zero formula/calculation errors (verified via LibreOffice recalc).

## Design system (frontend)

Dark trading-terminal aesthetic, deliberately not the generic "AI cream" or
"acid-green" look: bg `#0B0F14`, cards `#12171F`, borders `#1F2733`, text
`#E6EDF3`, bullish/call `#34D399`, bearish/put `#F87171`, one interactive
accent `#6366F1` kept separate from the sentiment colors. Space Grotesk for
headers, Inter for body, JetBrains Mono for every number (strikes/Greeks
align like a real terminal). Signature element: the ATM Greek gauges on the
Overview page, styled after the FnO deck's own "Risk Dashboard" gauge icons.

## Manual steps to go live (not done yet)

1. **Live option chain data**: generate an access token at
   https://upstox.com/developer/apps, set `UPSTOX_ACCESS_TOKEN` and
   `LIVE_NSE=true` as env vars on your deployed backend (Render). That's the
   whole switch -- `app/data/data_source.py` picks Upstox automatically over
   the NSE fallback whenever the token is present. **Upstox tokens expire
   daily (~3:30 AM IST)** -- regenerate and re-set it each trading morning,
   or the app quietly falls back to `live_nse_chain.py` (and then mock, if
   that's blocked too) until you do.
2. **Supabase**: create a project, run `supabase/schema.sql`, fill in `.env`
   from `.env.example`. Nothing currently writes to it yet -- next step is
   wiring `main.py` to cache chain snapshots and persist DOS trades there.
3. **Deploy frontend**: push to GitHub (already done), import into Vercel,
   set `NEXT_PUBLIC_API_BASE` to your deployed backend URL.
4. **Deploy backend**: Render or Railway, set `LIVE_NSE`, `UPSTOX_ACCESS_TOKEN`,
   and Supabase env vars there.
5. **DOS backtest historical data**: still mock (see data notes above) --
   needs a paid intraday vendor or forward data collection.
6. **One-pager report**: not written yet.

## Next phase

Supabase persistence wiring (cache writes + DOS trade log inserts), live NSE
verification, deployment, and the one-pager report.
