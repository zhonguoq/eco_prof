def test_capm():
    from lab.engine.micro.wacc import capm

    # rf=3%, beta=1.2, ERP=6% → WACC = 3% + 1.2*6% = 10.2%
    w = capm(rf=0.03, beta=1.2, erp=0.06)
    assert w == 0.102

    # rf=2.5%, beta=1.0, ERP=6% → WACC = 8.5%
    w2 = capm(rf=0.025, beta=1.0)
    assert w2 == 0.085


def test_default_industry():
    from lab.engine.micro.wacc import default_industry

    w = default_industry("白酒")
    assert w is not None
    assert 0.08 < w < 0.15

    # Unknown industry → general default
    w2 = default_industry("未知行业")
    assert w2 is not None
