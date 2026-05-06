def test_cagr_computes_compound_growth():
    from lab.engine.micro.growth import cagr

    # 3 years: 100 → 121 = 10% CAGR
    rate = cagr([100.0, 110.0, 121.0])
    assert abs(rate - 0.10) < 0.001

    # 5 years: 100 → 161.05 = 10% CAGR
    rate2 = cagr([100.0, 110.0, 121.0, 133.1, 146.41])
    assert abs(rate2 - 0.10) < 0.001

    # Single year → None
    assert cagr([100.0]) is None

    # Empty → None
    assert cagr([]) is None


def test_linear_trend_growth():
    from lab.engine.micro.growth import linear_trend

    # Perfect linear: values increase by 10 each year, mean=100 → ~10% growth
    rate = linear_trend([90.0, 100.0, 110.0, 120.0, 130.0])
    assert rate is not None
    assert abs(rate - 0.10) < 0.02  # slope=10, mean=110 → ~9.1%

    # Flat → near zero
    rate2 = linear_trend([100.0, 100.0, 100.0])
    assert rate2 is not None
    assert abs(rate2) < 0.001

    # Single → None
    assert linear_trend([100.0]) is None
