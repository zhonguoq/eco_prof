"""Integration tests for yfinance API contract.

Calls the REAL yfinance API (no mocks) to verify:
1. yfinance.Ticker API shape has not changed
2. Fields we rely on exist and have correct types in each market
3. fetch_securities end-to-end for US / HK / A-share

Marked pytest.mark.slow — excluded from fast CI, run explicitly:
    pytest tests/test_yf_fetcher_integration.py -v -m slow
"""

import pytest

pytestmark = pytest.mark.slow

# ─── 被测股票（选流动性好、不易退市的标的）────────────────────────────────
US_CODE = "AAPL"
HK_CODE = "0700.HK"
A_SH_CODE = "600519.SH"  # 上交所内部格式；yf_fetcher 应自动转换成 600519.SS
A_SZ_CODE = "000725.SZ"  # 深交所内部格式；yfinance 直接接受 .SZ 后缀
A_CODE = A_SH_CODE  # 保持旧引用不变


# ─── 辅助 ─────────────────────────────────────────────────────────────────


def _get_info(yf_code: str) -> dict:
    import yfinance as yf

    return yf.Ticker(yf_code).info


# ─── yfinance Ticker API 形状检查 ─────────────────────────────────────────


def test_yfinance_ticker_has_info_attribute():
    """yfinance.Ticker(code).info 返回非空 dict。"""
    import yfinance as yf

    ticker = yf.Ticker(US_CODE)
    assert hasattr(ticker, "info")
    assert isinstance(ticker.info, dict)
    assert len(ticker.info) > 10, "info dict 意外为空，API 可能已变更"


# ─── US 市场字段契约 ───────────────────────────────────────────────────────


def test_us_stock_required_fields_present():
    """AAPL.info 包含 fetch_securities 依赖的全部字段。"""
    info = _get_info(US_CODE)
    required = [
        "shortName",
        "industry",
        "sharesOutstanding",
        "currency",
        "currentPrice",
    ]
    for field in required:
        assert field in info, f"缺少字段 {field!r}，API 可能已改名"
        assert info[field] is not None, f"字段 {field!r} 为 None"


def test_us_stock_field_types():
    """AAPL 各字段类型符合代码预期。"""
    info = _get_info(US_CODE)
    assert isinstance(info["shortName"], str)
    assert isinstance(info["industry"], str)
    assert isinstance(info["sharesOutstanding"], (int, float))
    assert isinstance(info["currency"], str)
    assert isinstance(info["currentPrice"], (int, float))
    assert info["sharesOutstanding"] > 0
    assert info["currentPrice"] > 0


def test_us_stock_currency_is_usd():
    info = _get_info(US_CODE)
    assert info["currency"] == "USD"


# ─── HK 市场字段契约 ───────────────────────────────────────────────────────


def test_hk_stock_required_fields_present():
    """0700.HK.info 包含必要字段。"""
    info = _get_info(HK_CODE)
    for field in ["shortName", "sharesOutstanding", "currency", "currentPrice"]:
        assert field in info, f"HK 股缺少字段 {field!r}"
        assert info[field] is not None, f"HK 股 {field!r} 为 None"


def test_hk_stock_currency_is_hkd():
    info = _get_info(HK_CODE)
    assert info["currency"] == "HKD"


# ─── A 股代码转换 + 字段契约 ─────────────────────────────────────────────


def test_a_share_internal_code_sh_not_recognized_by_raw_yfinance():
    """600519.SH 直接传 yfinance 时 shortName 为 None —— 验证转换必要性。"""
    info = _get_info("600519.SH")  # 故意传错格式
    # yfinance 用 .SS 表示上交所；.SH 不被识别
    assert info.get("shortName") is None, (
        ".SH 格式居然被 yfinance 识别了，请更新 _to_yf_code() 的转换逻辑"
    )


def test_a_share_ss_format_works():
    """600519.SS（正确格式）能取到数据。"""
    info = _get_info("600519.SS")
    assert info.get("shortName") is not None
    assert info.get("currency") == "CNY"
    assert info.get("currentPrice", 0) > 0


def test_to_yf_code_converts_sh_to_ss():
    """_to_yf_code 把内部 .SH 转为 yfinance .SS。"""
    from lab.engine.micro.yf_fetcher import _to_yf_code

    assert _to_yf_code("600519.SH") == "600519.SS"
    assert _to_yf_code("000725.SZ") == "000725.SZ"  # SZ 不变
    assert _to_yf_code("0700.HK") == "0700.HK"
    assert _to_yf_code("AAPL") == "AAPL"


# ─── fetch_securities 端到端（真实网络） ─────────────────────────────────


def test_fetch_securities_us_end_to_end():
    """fetch_securities('AAPL') 返回完整 dict，market='US'。"""
    from lab.engine.micro.yf_fetcher import fetch_securities

    result = fetch_securities(US_CODE)

    assert result["market"] == "US"
    assert isinstance(result["name"], str) and result["name"]
    assert isinstance(result["shares_outstanding"], (int, float))
    assert result["shares_outstanding"] > 0
    assert result["currency"] == "USD"
    assert result["current_price"] > 0


def test_fetch_securities_hk_end_to_end():
    """fetch_securities('0700.HK') 返回完整 dict，market='HK'。"""
    from lab.engine.micro.yf_fetcher import fetch_securities

    result = fetch_securities(HK_CODE)

    assert result["market"] == "HK"
    assert result["currency"] == "HKD"
    assert result["current_price"] > 0
    assert result["shares_outstanding"] > 0


def test_fetch_securities_a_share_sh_end_to_end():
    """fetch_securities('600519.SH') 经 .SH→.SS 转换后能正确返回数据。"""
    from lab.engine.micro.yf_fetcher import fetch_securities

    result = fetch_securities(A_SH_CODE)

    assert result["market"] == "A"
    assert result["currency"] == "CNY"
    assert result["current_price"] > 0
    assert result["shares_outstanding"] > 0
    assert result["name"], "name 不应为空"


def test_fetch_securities_a_share_sz_end_to_end():
    """fetch_securities('000725.SZ') — 深交所 .SZ 后缀 yfinance 直接识别，无需转换。"""
    from lab.engine.micro.yf_fetcher import fetch_securities

    result = fetch_securities(A_SZ_CODE)

    assert result["market"] == "A"
    assert result["currency"] == "CNY"
    assert result["current_price"] > 0
    assert result["shares_outstanding"] > 0
    assert result["name"], "name 不应为空"


def test_to_yf_code_sz_unchanged():
    """_to_yf_code 对 .SZ 后缀不做任何转换。"""
    from lab.engine.micro.yf_fetcher import _to_yf_code

    assert _to_yf_code("000725.SZ") == "000725.SZ"
