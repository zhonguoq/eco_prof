"""
Scenario 参数构建与存储
ADR-002 决策 2、11、12、13：
- 三套硬编码场景模板（base/bull/bear）
- resolve：字符串引用 → 数字
- save_scenarios / update_scenario：DB 操作
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional

from lab.engine.micro.growth import cagr as calc_cagr
from lab.engine.micro.wacc import capm as calc_capm

# ── 国家长期 GDP 增速（ADR-002 决策 6） ──────────────────────────────────

LONG_TERM_GDP = {
    "CN": 0.045,
    "HK": 0.040,
    "US": 0.040,
}

_DEFAULT_ERP = 0.06  # 市场风险溢价（Equity Risk Premium）


# ── 场景模板（符号定义） ──────────────────────────────────────────────────

# 每个模板的字段可以是 float（直接用）或 str（需 resolve）
# 实际 resolve 由 build_all_scenarios 统一完成
_SCENARIO_TEMPLATES = {
    "base": {
        "g1_ref": "分析师共识_中",
        "N": 5,
        "gt_ref": "min(Rf,GDP)",
        "r_ref": "CAPM",
        "base_fcf_method": "mean3",
    },
    "bull": {
        "g1_ref": "分析师共识_高",
        "N": 7,
        "gt_ref": "min(Rf,GDP)",
        "r_ref": "CAPM",
        "base_fcf_method": "mean3",
    },
    "bear": {
        "g1_ref": "分析师共识_低",
        "N": 5,
        "gt_ref": "min(Rf,GDP)-0.005",
        "r_ref": "CAPM+0.01",
        "base_fcf_method": "mean3",
    },
}


# ── 单场景 resolve（内部辅助） ────────────────────────────────────────────


def resolve_scenario(
    scenario_key: str,
    fcf_list: list,
    rf: float,
    beta: float,
    country: str = "CN",
    analyst: Optional[dict] = None,
    erp: float = _DEFAULT_ERP,
) -> dict:
    """
    把一个场景的符号引用解析为数字，返回 {g1, N, gt, r, base_fcf_method}。
    scenario_key: 'base' | 'bull' | 'bear' | 'g1_cagr_ref'（测试用）
    """
    # 支持测试直接传非标准 key
    if scenario_key == "g1_cagr_ref":
        cagr_val = calc_cagr(fcf_list) or 0.0
        return {"g1": cagr_val}

    tmpl = _SCENARIO_TEMPLATES[scenario_key]

    # ── gt ──
    base_gt = min(rf, LONG_TERM_GDP.get(country, 0.04))
    gt_ref = tmpl["gt_ref"]
    if gt_ref == "min(Rf,GDP)":
        gt = base_gt
    elif gt_ref == "min(Rf,GDP)-0.005":
        gt = base_gt - 0.005
    else:
        gt = base_gt

    # ── r (discount rate) ──
    capm_rate = calc_capm(rf=rf, beta=beta, erp=erp)
    r_ref = tmpl["r_ref"]
    if r_ref == "CAPM":
        r = capm_rate
    elif r_ref == "CAPM+0.01":
        r = capm_rate + 0.01
    else:
        r = capm_rate

    # ── g1 ──
    cagr_val = calc_cagr(fcf_list) or 0.0
    g1_ref = tmpl["g1_ref"]

    if analyst is not None:
        if g1_ref == "分析师共识_高":
            g1 = analyst.get("high", cagr_val + 0.03)
        elif g1_ref == "分析师共识_中":
            g1 = analyst.get("mid", cagr_val)
        elif g1_ref == "分析师共识_低":
            g1 = analyst.get("low", cagr_val - 0.03)
        else:
            g1 = cagr_val
    else:
        # 降级：CAGR ± 3%
        if g1_ref == "分析师共识_高":
            g1 = cagr_val + 0.03
        elif g1_ref == "分析师共识_中":
            g1 = cagr_val
        elif g1_ref == "分析师共识_低":
            g1 = cagr_val - 0.03
        else:
            g1 = cagr_val

    return {
        "g1": g1,
        "N": tmpl["N"],
        "gt": gt,
        "r": r,
        "base_fcf_method": tmpl["base_fcf_method"],
    }


# ── 三场景一次性构建 ──────────────────────────────────────────────────────


def build_all_scenarios(
    fcf_list: list,
    rf: float,
    beta: float,
    country: str = "CN",
    analyst: Optional[dict] = None,
    erp: float = _DEFAULT_ERP,
) -> dict:
    """返回 {'base': {...}, 'bull': {...}, 'bear': {...}}。"""
    return {
        name: resolve_scenario(
            name,
            fcf_list=fcf_list,
            rf=rf,
            beta=beta,
            country=country,
            analyst=analyst,
            erp=erp,
        )
        for name in ("base", "bull", "bear")
    }


# ── DB 操作 ───────────────────────────────────────────────────────────────


def save_scenarios(conn, code: str, scenarios: dict) -> None:
    """把三场景参数写入 scenarios 表（upsert）。"""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for name, params in scenarios.items():
        conn.execute(
            """INSERT OR REPLACE INTO scenarios
               (code, scenario_name, g1, N, gt, r, wacc_l2_sanity, base_fcf_method, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                code,
                name,
                params["g1"],
                params["N"],
                params["gt"],
                params["r"],
                params.get("wacc_l2_sanity"),
                params.get("base_fcf_method", "mean3"),
                now,
            ),
        )
    conn.commit()


def update_scenario(conn, code: str, scenario_name: str, **kwargs) -> None:
    """只更新指定字段（g1/N/gt/r/base_fcf_method）。"""
    allowed = {"g1", "N", "gt", "r", "base_fcf_method"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    updates["updated_at"] = now
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [code, scenario_name]
    conn.execute(
        f"UPDATE scenarios SET {set_clause} WHERE code=? AND scenario_name=?",
        values,
    )
    conn.commit()
