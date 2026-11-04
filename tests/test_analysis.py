"""Tests for the calculation functions in analysis.py.

Uses the repo's own filtered dataset (data/bc_canada_enrolment.csv) —
no download, no plotting. Values are the published StatCan figures
quoted in the README.
"""
from pathlib import Path

import pandas as pd
import pytest

from analysis import BREAK_YEAR, compute_series, summarise

DATA = Path(__file__).resolve().parents[1] / "data" / "bc_canada_enrolment.csv"


@pytest.fixture(scope="module")
def series():
    piv = pd.read_csv(DATA, header=[0, 1], index_col=0)
    return piv, compute_series(piv)


def test_series_cover_all_years(series):
    piv, s = series
    assert len(piv) == 33
    assert piv.index[0] == "1992/1993"
    assert piv.index[-1] == "2024/2025"
    assert list(s["bc_total"].index) == list(piv.index)


def test_latest_year_values_match_readme(series):
    _, s = series
    assert s["bc_total"].loc["2024/2025"] == pytest.approx(291930.0)
    assert s["bc_international"].loc["2024/2025"] == pytest.approx(73938.0)
    assert s["bc_domestic"].loc["2024/2025"] == pytest.approx(217839.0)
    assert s["bc_international_share"].loc["2024/2025"] == pytest.approx(25.3, abs=0.05)


def test_international_peak_is_2023_2024(series):
    _, s = series
    assert s["bc_international"].idxmax() == "2023/2024"
    assert s["bc_international"].loc["2023/2024"] == pytest.approx(78885.0)
    assert s["bc_international_share"].loc["2023/2024"] == pytest.approx(26.5, abs=0.05)


def test_2024_25_dip(series):
    _, s = series
    f = summarise(s)
    assert f["bc_international_change_peak_to_last"] == pytest.approx(-6.3, abs=0.05)
    assert f["ca_international_change_peak_to_last"] == pytest.approx(-6.9, abs=0.05)


def test_executive_summary_window(series):
    """The exec chart covers 2000/01 onward: 25 academic years."""
    piv, s = series
    window = s["bc_international"][piv.index >= BREAK_YEAR]
    assert len(window) == 25
    assert window.index[0] == "2000/2001"
    assert window.index[-1] == "2024/2025"
