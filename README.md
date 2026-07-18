# F&O Derivatives Analytics Platform — Engine + Backtest (Phase 1)

AlgoLabs Assignment 2. This pass builds and validates the **math/DOS engine
and Excel deliverable** (per plan) — the FastAPI/React UI layer comes next.

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

backend/tests/
  test_black_scholes.py Put-call parity, known BSM value, IV round-trip, Greek sanity checks

excel_report/
  generate_excel_report.py  Builds FnO_Analytics_Report.xlsx (chain+Greeks, vol smile/surface,
                             interpretation cards, P&L decomposition, DOS backtest + equity curve)
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
  Swapping in a live NSE session fetch only requires replacing
  `generate_chain()`'s return value — nothing downstream changes.
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

## Next phase (not built yet)

FastAPI endpoints wrapping these modules, Supabase schema + caching layer for
live NSE snapshots, Next.js frontend (option chain table, 3D vol surface,
P&L chart, DOS live panel), deployment.
