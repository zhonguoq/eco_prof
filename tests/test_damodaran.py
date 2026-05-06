"""
Phase 5: Damodaran 数据加载测试
ADR-002 决策 3、4、5
"""

import os
import pytest


# ── load_erp ────────────────────────────────────────────────────────────────


def test_load_erp_china(tmp_path):
    """load_erp('CN') 返回中国 ERP float，在合理范围内。"""
    from lab.engine.micro.damodaran import load_erp

    erp = load_erp("CN")
    assert isinstance(erp, float)
    assert 0.03 < erp < 0.15


def test_load_erp_us(tmp_path):
    """load_erp('US') 返回美国 ERP。"""
    from lab.engine.micro.damodaran import load_erp

    erp = load_erp("US")
    assert isinstance(erp, float)
    assert 0.03 < erp < 0.10


def test_load_erp_unknown_country_fallback():
    """未知国家 → 返回全球 ERP 兜底值（约 5%~8%）。"""
    from lab.engine.micro.damodaran import load_erp

    erp = load_erp("XX")
    assert isinstance(erp, float)
    assert 0.03 < erp < 0.15


# ── load_industry_beta ───────────────────────────────────────────────────────


def test_load_industry_beta_china_beverage():
    """CN 市场酒类行业 → 返回含 unlevered_beta 的 dict。"""
    from lab.engine.micro.damodaran import load_industry_beta

    result = load_industry_beta("Beverage (Alcoholic)", "CN")
    assert "unlevered_beta" in result
    assert "levered_beta" in result
    assert "de_ratio" in result
    assert "tax_rate" in result
    assert 0.3 < result["unlevered_beta"] < 2.0


def test_load_industry_beta_us_tech():
    """US 市场科技行业。"""
    from lab.engine.micro.damodaran import load_industry_beta

    result = load_industry_beta("Technology", "US")
    assert result["unlevered_beta"] > 0
    assert result["levered_beta"] > 0


def test_load_industry_beta_alias():
    """行业别名映射：'白酒' → 'Beverage (Alcoholic)'。"""
    from lab.engine.micro.damodaran import load_industry_beta

    result = load_industry_beta("白酒", "CN")
    assert result["unlevered_beta"] > 0


def test_load_industry_beta_unknown_returns_none():
    """未知行业 → 返回 None（调用方负责降级）。"""
    from lab.engine.micro.damodaran import load_industry_beta

    result = load_industry_beta("NonExistentIndustry_XYZ", "CN")
    assert result is None


# ── load_country_tax ─────────────────────────────────────────────────────────


def test_load_country_tax_china():
    """CN 税率 = 25%。"""
    from lab.engine.micro.damodaran import load_country_tax

    tax = load_country_tax("CN")
    assert abs(tax - 0.25) < 1e-6


def test_load_country_tax_us():
    """US 税率 = 21%。"""
    from lab.engine.micro.damodaran import load_country_tax

    tax = load_country_tax("US")
    assert abs(tax - 0.21) < 1e-6


def test_load_country_tax_unknown_fallback():
    """未知国家 → 返回全球平均税率兜底（约 25%）。"""
    from lab.engine.micro.damodaran import load_country_tax

    tax = load_country_tax("XX")
    assert isinstance(tax, float)
    assert 0.10 < tax < 0.40


# ── in-memory cache ──────────────────────────────────────────────────────────


def test_damodaran_load_is_cached():
    """连续两次调用 load_erp 返回同一对象（缓存命中）。"""
    from lab.engine.micro import damodaran as dam_module

    dam_module._CACHE.clear()
    erp1 = dam_module.load_erp("CN")
    # Cache should now be populated
    assert len(dam_module._CACHE) > 0
    erp2 = dam_module.load_erp("CN")
    assert erp1 == erp2
