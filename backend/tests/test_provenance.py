from datetime import datetime, timedelta

from app.data.provenance import IST, STALE_AFTER_SECONDS, build_source_meta


def test_mock_source_has_a_readable_description_and_is_not_degraded():
    meta = build_source_meta("mock")
    assert meta["rung"] == "mock"
    assert "mock" in meta["description"].lower()
    assert meta["degraded"] is False
    assert meta["live_fetch_error"] is None


def test_live_fetch_error_marks_response_degraded_even_if_rung_is_live():
    """A fallback path can report data_source='live-upstox' having actually
    served real data, but still pass along a live_fetch_error from a
    *different* attempt -- degraded should reflect that honestly."""
    meta = build_source_meta("live-upstox", live_fetch_error="timeout on retry 1")
    assert meta["degraded"] is True
    assert meta["live_fetch_error"] == "timeout on retry 1"


def test_fresh_capture_is_not_stale():
    meta = build_source_meta("live-nse", captured_at=datetime.now(IST))
    assert meta["stale"] is False
    assert meta["age_seconds"] < 5


def test_old_capture_is_stale():
    old = datetime.now(IST) - timedelta(seconds=STALE_AFTER_SECONDS + 30)
    meta = build_source_meta("live-nse", captured_at=old)
    assert meta["stale"] is True
    assert meta["age_seconds"] >= STALE_AFTER_SECONDS


def test_unrecognized_source_string_does_not_crash():
    meta = build_source_meta("something-new")
    assert "Unrecognized source" in meta["description"]
