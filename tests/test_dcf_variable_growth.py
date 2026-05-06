"""
Phase 1: DCF 内核升级测试
ADR-002 决策 1、2、14
- growth_rates: List[float] 驱动逐年增长
- _normalize_base 四种方法
- 负 FCF 拒绝
"""

import pytest
from lab.engine.micro.dcf import dcf_value, _normalize_base, sensitivity_matrix


# ── _normalize_base ────────────────────────────────────────────────────────


def test_normalize_base_mean3():
    # last 3 of [100, 200, 120, 80, 130] = [120, 80, 130] → mean = 110.0
    assert _normalize_base([100, 200, 120, 80, 130], "mean3") == pytest.approx(110.0)


def test_normalize_base_latest():
    assert _normalize_base([100, 200, 120, 80, 130], "latest") == 130


def test_normalize_base_mean5():
    # all 5: (100+200+120+80+130)/5 = 126
    assert _normalize_base([100, 200, 120, 80, 130], "mean5") == pytest.approx(126.0)


def test_normalize_base_median5():
    # sorted last 5: [80, 100, 120, 130, 200] → median = 120
    assert _normalize_base([100, 200, 120, 80, 130], "median5") == pytest.approx(120.0)


def test_normalize_base_short_list_mean3():
    # only 2 elements, mean3 falls back to all available
    assert _normalize_base([50, 70], "mean3") == pytest.approx(60.0)


# ── dcf_value with growth_rates list ─────────────────────────────────────


def test_dcf_constant_rates_matches_legacy():
    """[0.10]*5 with base_fcf_method='latest' must equal old growth_rate=0.10 result."""
    fcf_list = [100, 110, 120, 130, 140]
    # Call using backward-compat kwargs (old interface)
    result_legacy = dcf_value(
        fcf_list,
        growth_rate=0.10,
        growth_years=5,
        terminal_growth=0.03,
        discount_rate=0.08,
        base_fcf_method="latest",
    )
    # Call using new growth_rates list
    result_new = dcf_value(
        fcf_list,
        growth_rates=[0.10] * 5,
        terminal_growth=0.03,
        discount_rate=0.08,
        base_fcf_method="latest",
    )
    assert result_new == pytest.approx(result_legacy, rel=1e-4)


def test_dcf_declining_growth_rates():
    """Declining rates [0.15,0.12,0.10,0.08,0.05] produce value < constant 0.15."""
    fcf_list = [100, 110, 120, 130, 140]
    result_declining = dcf_value(
        fcf_list,
        growth_rates=[0.15, 0.12, 0.10, 0.08, 0.05],
        terminal_growth=0.03,
        discount_rate=0.08,
        base_fcf_method="latest",
    )
    result_high = dcf_value(
        fcf_list,
        growth_rates=[0.15] * 5,
        terminal_growth=0.03,
        discount_rate=0.08,
        base_fcf_method="latest",
    )
    assert result_declining < result_high


def test_dcf_variable_rates_manual():
    """2-year DCF with known rates, verify PV arithmetic."""
    # base=100 (latest), g=[0.10, 0.20], r=0.10, gt=0.03
    # year1 FCF = 100*1.10 = 110; PV1 = 110/1.10 = 100.0
    # year2 FCF = 110*1.20 = 132; PV2 = 132/1.10^2 = 109.0909...
    # terminal = 132*1.03 / (0.10-0.03) = 135.96/0.07 = 1942.286; PV_t = 1942.286/1.21 = 1605.195
    # total ~ 1814.29
    result = dcf_value(
        [100],
        growth_rates=[0.10, 0.20],
        terminal_growth=0.03,
        discount_rate=0.10,
        base_fcf_method="latest",
    )
    assert result == pytest.approx(1814.29, rel=1e-3)


def test_dcf_negative_base_fcf_raises():
    """Normalized FCF ≤ 0 must raise ValueError."""
    with pytest.raises(ValueError, match="DCF 不适用"):
        dcf_value(
            [-100, -200, -150],
            growth_rates=[0.10] * 3,
            terminal_growth=0.03,
            discount_rate=0.08,
        )


def test_dcf_negative_latest_fcf_raises():
    """Latest-method picks a negative value → should raise."""
    with pytest.raises(ValueError, match="DCF 不适用"):
        dcf_value(
            [200, 300, -50],
            growth_rates=[0.10] * 3,
            terminal_growth=0.03,
            discount_rate=0.08,
            base_fcf_method="latest",
        )


def test_dcf_discount_le_terminal_raises():
    """discount_rate ≤ terminal_growth must still raise ValueError."""
    with pytest.raises(ValueError, match="must be >"):
        dcf_value(
            [100, 200],
            growth_rates=[0.10] * 3,
            terminal_growth=0.05,
            discount_rate=0.04,
        )


# ── sensitivity_matrix backward compat ───────────────────────────────────


def test_sensitivity_matrix_still_works():
    """sensitivity_matrix must still return a nested dict of floats."""
    fcf_list = [100, 110, 120]
    matrix = sensitivity_matrix(fcf_list)
    assert isinstance(matrix, dict)
    for row in matrix.values():
        for val in row.values():
            assert isinstance(val, (int, float))
