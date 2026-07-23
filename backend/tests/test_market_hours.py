from datetime import datetime

from app.data import market_hours


def _ist(y, m, d, hh, mm):
    return datetime(y, m, d, hh, mm, tzinfo=market_hours.IST)


def test_weekend_is_never_a_trading_day(monkeypatch):
    monkeypatch.setattr(market_hours, "_cached_holiday_set", lambda: set())
    saturday = _ist(2026, 7, 25, 10, 0)  # 2026-07-25 is a Saturday
    assert market_hours.is_trading_day(saturday) is False
    assert market_hours.within_market_hours(saturday) is False


def test_weekday_within_hours_is_a_trading_session(monkeypatch):
    monkeypatch.setattr(market_hours, "_cached_holiday_set", lambda: set())
    wednesday_noon = _ist(2026, 7, 22, 12, 0)  # a Wednesday
    assert market_hours.is_trading_day(wednesday_noon) is True
    assert market_hours.within_market_hours(wednesday_noon) is True


def test_weekday_outside_clock_window_is_closed(monkeypatch):
    monkeypatch.setattr(market_hours, "_cached_holiday_set", lambda: set())
    wednesday_evening = _ist(2026, 7, 22, 20, 0)
    assert market_hours.within_market_hours(wednesday_evening) is False


def test_holiday_on_a_weekday_closes_the_market(monkeypatch):
    """The core new behaviour: a weekday that the holiday API reports as a
    trading holiday must be treated as closed, even mid-clock-window."""
    holiday_date = "2026-07-22"  # deliberately overlaps the "weekday" test's date
    monkeypatch.setattr(market_hours, "_cached_holiday_set", lambda: {holiday_date})
    holiday_noon = _ist(2026, 7, 22, 12, 0)
    assert market_hours.is_trading_day(holiday_noon) is False
    assert market_hours.within_market_hours(holiday_noon) is False


def test_holiday_fetch_failure_degrades_to_clock_only_check(monkeypatch):
    """If the holiday API is unreachable, _cached_holiday_set returns None
    (see _fetch_holiday_set's contract) -- is_trading_day must fall back to
    weekday-only rather than raising or silently treating every day as a
    holiday."""
    monkeypatch.setattr(market_hours, "_cached_holiday_set", lambda: None)
    wednesday_noon = _ist(2026, 7, 22, 12, 0)
    assert market_hours.is_trading_day(wednesday_noon) is True


def test_fetch_holiday_set_returns_none_on_request_failure(monkeypatch):
    def _boom(*args, **kwargs):
        raise ConnectionError("no network in this sandbox")

    monkeypatch.setattr(market_hours.requests, "get", _boom)
    assert market_hours._fetch_holiday_set() is None
