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


def test_skill_references_dcf_equity():
    with open(SKILL_PATH) as f:
        content = f.read()
    assert "--equity" in content


def test_skill_requires_user_confirmation():
    with open(SKILL_PATH) as f:
        content = f.read()
    assert "确认" in content or "确认" in content
