from app.core.pnl_decomposer import decompose_pnl


def _position(strike=24350, qty=-50):
    return {"K": strike, "r": 0.065, "option_type": "call", "quantity": qty}


def test_zero_move_zero_iv_change_zero_days_gives_near_zero_pnl():
    """No spot move, no IV change, no time passing -> price shouldn't move,
    so actual_pnl and every Greek contribution should be ~0."""
    position = _position()
    snap = {"S": 24350.0, "T": 6 / 365.0, "sigma": 0.135}
    result = decompose_pnl(position, snap, dict(snap))
    assert abs(result["actual_pnl"]) < 1e-6
    assert abs(result["delta_pnl"]) < 1e-6
    assert abs(result["vega_pnl"]) < 1e-6


def test_more_days_elapsed_means_more_theta_decay():
    """Holding spot and IV fixed, more elapsed days should mean a larger
    (more negative, for a long call) theta contribution in magnitude --
    this is the behaviour the frontend's new 'Time' slider relies on."""
    position = _position(qty=1)  # long, so theta_pnl is negative for a call
    snap_t0 = {"S": 24350.0, "T": 6 / 365.0, "sigma": 0.135}

    one_day = decompose_pnl(position, snap_t0, {"S": 24350.0, "T": 5 / 365.0, "sigma": 0.135})
    three_days = decompose_pnl(position, snap_t0, {"S": 24350.0, "T": 3 / 365.0, "sigma": 0.135})

    assert abs(three_days["theta_pnl"]) > abs(one_day["theta_pnl"])


def test_time_to_expiry_clamp_prevents_zero_or_negative_T():
    """main.py clamps T1 to a 1-day floor before calling decompose_pnl so a
    large days_elapsed value (e.g. more days than expiry_days itself) can
    never reach T=0 or negative -- reproduce that clamp here and confirm it
    still produces a finite, sane result rather than a math-domain error."""
    T0 = 6 / 365.0
    days_elapsed = 30  # far more than the 6 days to expiry
    T1 = max(T0 - days_elapsed / 365.0, 1 / 365.0)
    assert T1 == 1 / 365.0  # floor was applied, not a negative T

    position = _position()
    result = decompose_pnl(position, {"S": 24350.0, "T": T0, "sigma": 0.135},
                            {"S": 24350.0, "T": T1, "sigma": 0.135})
    assert all(isinstance(v, (int, float)) for k, v in result.items() if k != "primary_driver")


def test_primary_driver_matches_largest_magnitude_contribution():
    position = _position()
    snap_t0 = {"S": 24350.0, "T": 6 / 365.0, "sigma": 0.135}
    # Large IV jump, tiny spot move -> Vega should dominate.
    snap_t1 = {"S": 24350.0 * 1.0001, "T": 6 / 365.0, "sigma": 0.135 + 0.10}
    result = decompose_pnl(position, snap_t0, snap_t1)
    assert result["primary_driver"] == "Vega"
