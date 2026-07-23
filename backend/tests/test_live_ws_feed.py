"""
Tests for live_ws_feed.py's auth-failure parking. These exercise
run_forever()'s control flow only (via monkeypatched _run_once) -- they do
not open a real socket or call Upstox, consistent with this module's own
documented caveat that it hasn't been exercised against a live connection
in this environment.
"""
import asyncio

import pytest

from app.data import live_ws_feed


class _StopLoop(BaseException):
    """Raised from a monkeypatched asyncio.sleep (or _run_once) to break
    run_forever()'s `while True` after we've observed what we need, since
    it never returns on its own. Subclasses BaseException, not Exception,
    so it isn't swallowed by run_forever's `except Exception` handlers."""


def _run_until_stopped(coro):
    try:
        asyncio.run(coro)
    except _StopLoop:
        pass


def test_auth_error_sets_auth_failed_and_uses_the_long_retry_interval(monkeypatch):
    live_ws_feed._status.update(connected=False, last_error=None,
                                 auth_failed=False, auth_failed_since=None)

    async def _fake_run_once(symbols):
        raise live_ws_feed.AuthError("401 token rejected")

    sleep_calls = []

    async def _fake_sleep(seconds):
        sleep_calls.append(seconds)
        raise _StopLoop()

    monkeypatch.setattr(live_ws_feed, "_run_once", _fake_run_once)
    monkeypatch.setattr(live_ws_feed.asyncio, "sleep", _fake_sleep)

    _run_until_stopped(live_ws_feed.run_forever(symbols=("NIFTY",)))

    assert live_ws_feed._status["auth_failed"] is True
    assert live_ws_feed._status["auth_failed_since"] is not None
    assert sleep_calls == [live_ws_feed.AUTH_FAILED_RETRY_SECONDS]


def test_non_auth_error_does_not_set_auth_failed_and_backs_off_normally(monkeypatch):
    live_ws_feed._status.update(connected=False, last_error=None,
                                 auth_failed=False, auth_failed_since=None)

    async def _fake_run_once(symbols):
        raise ConnectionError("network blip")

    sleep_calls = []

    async def _fake_sleep(seconds):
        sleep_calls.append(seconds)
        raise _StopLoop()

    monkeypatch.setattr(live_ws_feed, "_run_once", _fake_run_once)
    monkeypatch.setattr(live_ws_feed.asyncio, "sleep", _fake_sleep)

    _run_until_stopped(live_ws_feed.run_forever(symbols=("NIFTY",)))

    assert live_ws_feed._status["auth_failed"] is False
    assert sleep_calls == [live_ws_feed.RECONNECT_BACKOFF_START]


def test_recovering_after_auth_failure_clears_the_parked_state(monkeypatch):
    """Once a connection succeeds (_run_once returns cleanly), auth_failed
    must reset even if it was previously True -- fixing the token on Render
    should recover without a restart."""
    live_ws_feed._status.update(connected=False, last_error="stale",
                                 auth_failed=True, auth_failed_since=123.0)

    calls = {"n": 0}

    async def _fake_run_once(symbols):
        calls["n"] += 1
        if calls["n"] == 1:
            return  # clean "disconnect" -- simulates a successful reconnect
        raise _StopLoop()

    monkeypatch.setattr(live_ws_feed, "_run_once", _fake_run_once)

    _run_until_stopped(live_ws_feed.run_forever(symbols=("NIFTY",)))

    assert live_ws_feed._status["auth_failed"] is False
    assert live_ws_feed._status["auth_failed_since"] is None


def test_authorize_raises_autherror_on_401(monkeypatch):
    class _FakeResp:
        status_code = 401
        text = "invalid token"

    monkeypatch.setattr(live_ws_feed.requests, "get", lambda *a, **k: _FakeResp())

    with pytest.raises(live_ws_feed.AuthError):
        live_ws_feed._authorize("bad-token")
