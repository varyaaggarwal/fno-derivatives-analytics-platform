-- Run this in Supabase's SQL Editor (Project > SQL Editor > New Query) once
-- you've created a project. This is the caching + persistence layer the
-- assignment spec calls for.

create table if not exists option_chain_snapshots (
    id bigint generated always as identity primary key,
    symbol text not null,                  -- 'NIFTY' or 'BANKNIFTY'
    fetched_at timestamptz not null default now(),
    spot numeric not null,
    expiry_date date not null,
    raw_json jsonb not null                -- full NSE response, cached as-is
);
create index if not exists idx_chain_symbol_time on option_chain_snapshots (symbol, fetched_at desc);

create table if not exists bhav_copy_fo (
    id bigint generated always as identity primary key,
    trade_date date not null,
    symbol text not null,
    instrument text not null,              -- FUTIDX, OPTIDX, etc.
    expiry_date date,
    strike_price numeric,
    option_type text,                      -- CE / PE / null for futures
    open_price numeric, high_price numeric, low_price numeric, close_price numeric,
    settle_price numeric, contracts numeric, open_interest numeric,
    unique (trade_date, symbol, instrument, expiry_date, strike_price, option_type)
);

create table if not exists dos_trade_log (
    id bigint generated always as identity primary key,
    session_date date not null,
    day_type text not null,                -- Wednesday / Thursday
    entry_time timestamptz not null,
    exit_time timestamptz not null,
    option_type text not null,             -- CE / PE
    strike numeric not null,
    fut_at_entry numeric, fut_at_exit numeric, supertrend_at_entry numeric,
    premium_sold numeric, premium_exit numeric,
    exit_reason text not null,             -- initial_sl / trailing_sl / market_close
    pnl_rupees numeric not null,
    -- P&L attribution split by day type (per assignment spec)
    delta_pnl numeric, gamma_pnl numeric, theta_pnl numeric, vega_pnl numeric, residual_pnl numeric,
    created_at timestamptz not null default now()
);
create index if not exists idx_dos_session on dos_trade_log (session_date);

-- Row Level Security: enable + add a permissive policy for the anon key if
-- your frontend reads directly from Supabase (skip this if only your FastAPI
-- backend, using the service_role key, ever talks to these tables).
alter table option_chain_snapshots enable row level security;
alter table bhav_copy_fo enable row level security;
alter table dos_trade_log enable row level security;

create policy "public read" on option_chain_snapshots for select using (true);
create policy "public read" on bhav_copy_fo for select using (true);
create policy "public read" on dos_trade_log for select using (true);
