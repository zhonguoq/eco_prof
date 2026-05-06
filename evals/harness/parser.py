"""
harness/parser.py — Scenario & Rubric Markdown 解析（ADR-003 决策 5、11）

Scenario 文件格式：
  ---
  scenario_id: micro_basic_cn
  mode: offline           # offline | live
  persona: src/eco-prof.md
  skills:
    - src/skills/micro/SKILL.md
  fixture: micro_seeded   # offline 模式需要
  rubric: evals/micro/rubrics/adr-002.md
  tags: [micro, cn, happy-path]
  ---

  ## Input
  帮我估值 000725.SZ

  ## Notes
  验证 ADR-002 的 16 个决策……

Rubric 文件格式：
  ---
  rubric_id: smoke_hello
  ---
  # Rubric Title
  - id: item_id
    question: 评估问题？
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class Scenario:
    scenario_id: str
    mode: str  # "offline" | "live"
    persona: str  # 相对路径，如 src/eco-prof.md
    skills: List[str]  # skill 文件路径列表
    rubric: str  # rubric 文件路径
    input_text: str  # ## Input 段内容
    fixture: Optional[str] = None  # offline 模式的 fixture 名称
    tags: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class RubricItem:
    id: str
    question: str


@dataclass
class Rubric:
    rubric_id: str
    items: List[RubricItem]


def _split_frontmatter(text: str):
    """将 Markdown 文本拆分为 (frontmatter_dict, body_str)。"""
    text = text.strip()
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm_raw = text[3:end].strip()
    body = text[end + 4 :].strip()
    fm = yaml.safe_load(fm_raw) or {}
    return fm, body


def parse_scenario(path: str | Path) -> Scenario:
    """解析 scenario Markdown 文件，返回 Scenario dataclass。"""
    content = Path(path).read_text(encoding="utf-8")
    fm, body = _split_frontmatter(content)

    # 提取 ## Input 段
    input_match = re.search(r"## Input\s*\n(.*?)(?=\n## |\Z)", body, re.DOTALL)
    input_text = input_match.group(1).strip() if input_match else ""

    # 提取 ## Notes 段
    notes_match = re.search(r"## Notes\s*\n(.*?)(?=\n## |\Z)", body, re.DOTALL)
    notes = notes_match.group(1).strip() if notes_match else ""

    return Scenario(
        scenario_id=fm.get("scenario_id", Path(path).stem),
        mode=fm.get("mode", "offline"),
        persona=fm.get("persona", "src/eco-prof.md"),
        skills=fm.get("skills") or [],
        rubric=fm.get("rubric", ""),
        input_text=input_text,
        fixture=fm.get("fixture"),
        tags=fm.get("tags") or [],
        notes=notes,
    )


def parse_rubric(path: str | Path) -> Rubric:
    """解析 rubric Markdown 文件，返回 Rubric dataclass。"""
    content = Path(path).read_text(encoding="utf-8")
    fm, body = _split_frontmatter(content)

    rubric_id = fm.get("rubric_id", Path(path).stem)

    # 解析列表项：- id: xxx\n  question: ...
    items: List[RubricItem] = []
    item_pattern = re.compile(
        r"-\s+id:\s*(\S+)\s*\n\s+question:\s*(.+?)(?=\n-\s+id:|\Z)",
        re.DOTALL,
    )
    for m in item_pattern.finditer(body):
        item_id = m.group(1).strip()
        question = m.group(2).strip()
        items.append(RubricItem(id=item_id, question=question))

    return Rubric(rubric_id=rubric_id, items=items)
