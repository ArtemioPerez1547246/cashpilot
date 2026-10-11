"""Bad inputs are rejected with a clear error, never turned into a confident wrong number."""
import pytest

from app.engine import scenarios as S


def test_garbage_date_is_rejected():
    with pytest.raises(ValueError):
        S.forecast("normal", extra_changes=[{"op": "set_date", "txn": "T15", "date": "not-a-date"}])


def test_huge_shift_is_rejected():
    with pytest.raises(ValueError):
        S.forecast("normal", extra_changes=[{"op": "shift", "txn": "T15", "days": 10**9}])


def test_stacked_credit_draws_are_rejected():
    with pytest.raises(ValueError):
        S.forecast("disruption", ["L05A", "L05B", "L05C"])


def test_valid_inputs_still_match_golden():
    assert S.forecast("disruption", ["L01"]).min_balance == 300
    assert S.forecast("disruption", ["L01", "L05B"]).min_balance == 2300
