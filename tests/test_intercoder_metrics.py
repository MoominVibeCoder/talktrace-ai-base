"""Tests for inter-coder agreement metrics."""
import math

import pandas as pd

from talktrace_ai.utils.intercoder_metrics import (
    compute_intercoder_agreement,
    p_value_stars,
)


def _df(codes):
    """Build a coded-impulse frame: one impulse per code, stable text."""
    return pd.DataFrame(
        {"Impuls": [f"Impuls {i}" for i in range(len(codes))], "Shortcode": codes}
    )


# --- p_value_stars ---------------------------------------------------

def test_p_value_stars_thresholds():
    assert p_value_stars(0.0005) == "***"
    assert p_value_stars(0.005) == "**"
    assert p_value_stars(0.03) == "*"
    assert p_value_stars(0.5) in ("", "n.s.", "ns")  # not significant


# --- compute_intercoder_agreement ------------------------------------

def test_perfect_agreement():
    df = _df(["A", "B", "A", "C"])
    r = compute_intercoder_agreement(df, df.copy())
    assert r["n_pairs"] == 4
    assert r["n_both"] == 4
    assert r["n_only_a"] == 0 and r["n_only_b"] == 0
    assert r["percent_agreement"] == 1.0
    assert math.isclose(r["kappa"], 1.0, abs_tol=1e-9)


def test_total_disagreement_low_percent():
    a = _df(["A", "A", "A", "A"])
    b = _df(["B", "B", "B", "B"])
    r = compute_intercoder_agreement(a, b)
    assert r["percent_agreement"] == 0.0


def test_unmatched_impulses_counted():
    a = pd.DataFrame({"Impuls": ["x", "y"], "Shortcode": ["A", "B"]})
    b = pd.DataFrame({"Impuls": ["x", "z"], "Shortcode": ["A", "C"]})
    r = compute_intercoder_agreement(a, b)
    assert r["n_both"] == 1       # only "x" in both
    assert r["n_only_a"] == 1     # "y"
    assert r["n_only_b"] == 1     # "z"
    assert r["n_pairs"] == 3


def test_partial_agreement_between_zero_and_one():
    a = _df(["A", "B", "A", "B"])
    b = _df(["A", "B", "B", "A"])
    r = compute_intercoder_agreement(a, b)
    assert 0.0 < r["percent_agreement"] < 1.0
