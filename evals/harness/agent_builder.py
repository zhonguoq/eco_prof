"""
harness/agent_builder.py — 动态生成 opencode agent 文件（ADR-003 决策 10）

流程：
  1. 读 persona 文件（src/eco-prof.md）
  2. 读 skills 列表的每个 SKILL.md
  3. 拼接 opencode agent 格式（frontmatter + 正文）
  4. 写入 .opencode/agent/eval-<scenario_id>.md
  5. 返回临时 agent 名字供 run.py 调用

cleanup(scenario_id) 删除临时文件。
"""

from __future__ import annotations

import os
from pathlib import Path

from .parser import Scenario

_REPO_ROOT = Path(__file__).parent.parent.parent
_AGENT_DIR = _REPO_ROOT / ".opencode" / "agent"


def build(scenario: Scenario) -> str:
    """生成临时 agent 文件，返回 agent 名字（不含 .md 后缀）。"""
    agent_name = f"eval-{scenario.scenario_id}"
    agent_path = _AGENT_DIR / f"{agent_name}.md"
    _AGENT_DIR.mkdir(parents=True, exist_ok=True)

    parts: list[str] = []

    # ── 读 persona ──
    persona_path = _REPO_ROOT / scenario.persona
    if persona_path.exists():
        persona_text = persona_path.read_text(encoding="utf-8").strip()
        parts.append(persona_text)
    else:
        parts.append(f"# Persona: {scenario.persona}\n(file not found)")

    # ── 读 skills ──
    for skill_rel in scenario.skills:
        skill_path = _REPO_ROOT / skill_rel
        if skill_path.exists():
            skill_text = skill_path.read_text(encoding="utf-8").strip()
            parts.append(f"\n\n---\n\n{skill_text}")
        else:
            parts.append(f"\n\n# Skill: {skill_rel}\n(file not found)")

    agent_content = "\n\n".join(parts)
    agent_path.write_text(agent_content, encoding="utf-8")
    return agent_name


def cleanup(scenario_id: str) -> None:
    """删除临时 agent 文件。"""
    agent_path = _AGENT_DIR / f"eval-{scenario_id}.md"
    if agent_path.exists():
        agent_path.unlink()
