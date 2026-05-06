import os

SKILL_PATH = "src/skills/micro/SKILL.md"


def test_skill_file_exists():
    assert os.path.isfile(SKILL_PATH)


def test_skill_references_fetch_financials():
    with open(SKILL_PATH) as f:
        content = f.read()
    assert "fetch_financials.py" in content


def test_skill_references_estimate_params():
    with open(SKILL_PATH) as f:
        content = f.read()
    assert "estimate_params.py" in content


def test_skill_references_websearch():
    with open(SKILL_PATH) as f:
        content = f.read()
    assert "WebSearch" in content


def test_skill_references_build_scenarios():
    """v2: build_scenarios.py 替代旧 dcf.py --growth --discount（ADR-002 决策 #13）。"""
    with open(SKILL_PATH) as f:
        content = f.read()
    assert "build_scenarios" in content


def test_skill_references_l3_wacc():
    """v2: SKILL.md 说明 L3 WACC（ADR-002 决策 #3）。"""
    with open(SKILL_PATH) as f:
        content = f.read()
    assert "L3" in content


def test_skill_references_damodaran():
    """v2: SKILL.md 说明 Damodaran 作为 β/ERP 来源（ADR-002 决策 #4）。"""
    with open(SKILL_PATH) as f:
        content = f.read()
    assert "Damodaran" in content


def test_skill_no_deprecated_growth_discount_flags():
    """v2: 旧的 dcf.py --growth --discount 命令已删除（ADR-002 决策 #13）。"""
    with open(SKILL_PATH) as f:
        content = f.read()
    assert "dcf.py --growth" not in content


def test_skill_requires_user_confirmation():
    with open(SKILL_PATH) as f:
        content = f.read()
    assert "确认" in content
