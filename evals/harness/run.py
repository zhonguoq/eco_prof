"""
harness/run.py — Eval 入口（ADR-003 决策 3、7、9、14）

用法：
  python -m evals.harness.run --scenario evals/smoke/scenarios/hello.md
  python -m evals.harness.run --scenario evals/micro/scenarios/basic_cn.md

流程：
  1. 解析 scenario
  2. offline 模式复制 fixture DB
  3. agent_builder.build(scenario) 生成临时 agent
  4. subprocess 调 opencode run --agent <temp> --format json
  5. 解析事件流 → conversation.md + events.jsonl
  6. judge.score(conversation, rubric) 拿分
  7. 生成 report.md
  8. agent_builder.cleanup
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from . import agent_builder, judge
from .parser import parse_rubric, parse_scenario

_REPO_ROOT = Path(__file__).parent.parent.parent
_RESULTS_DIR = Path(__file__).parent.parent / "results"
_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
_LAB_DB_DIR = _REPO_ROOT / "lab" / "db"


# ── DB 复制（offline 模式）────────────────────────────────────────────────────


def _setup_fixture(fixture_name: str) -> None:
    """将 evals/fixtures/<fixture_name>.db 复制到 lab/db/micro.db。"""
    src = _FIXTURES_DIR / f"{fixture_name}.db"
    dst = _LAB_DB_DIR / "micro.db"
    if not src.exists():
        raise FileNotFoundError(
            f"Fixture not found: {src}\nRun: python -m evals.harness.seed_fixtures"
        )
    _LAB_DB_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(dst))
    print(f"[harness] Fixture copied: {src} → {dst}")


# ── 事件流解析（ADR-003 决策 9）──────────────────────────────────────────────


def _parse_events(raw_output: str) -> tuple[str, List[Dict[str, Any]]]:
    """
    解析 opencode --format json 的事件流。
    返回 (conversation_md, events_list)。
    """
    events: List[Dict[str, Any]] = []
    conv_parts: List[str] = []

    for line in raw_output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        events.append(event)

        event_type = event.get("type", "")
        if event_type == "text":
            content = event.get("content", "")
            if content:
                conv_parts.append(f"**Assistant:** {content}")
        elif event_type == "tool_call":
            name = event.get("name", "tool")
            params = json.dumps(event.get("input", {}), ensure_ascii=False)
            conv_parts.append(f"**Tool ({name}):** `{params[:200]}`")

    conversation_md = "\n\n".join(conv_parts) if conv_parts else raw_output
    return conversation_md, events


# ── 报告生成（ADR-003 决策 14）───────────────────────────────────────────────


def _build_report(
    scenario_id: str,
    conversation_md: str,
    scores: Dict[str, Any],
    rubric_items: list,
) -> str:
    """生成 report.md，含 rubric 打分 + Human review checkbox。"""
    lines = [
        f"# Eval Report: {scenario_id}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Rubric Results",
        "",
    ]

    if scores.get("_skipped"):
        lines.append(f"> Judge skipped: {scores.get('_reason', 'unknown')}")
        lines.append("")
    elif scores.get("_parse_error"):
        lines.append("> Judge response parse error.")
        lines.append("")
    else:
        pass_count = sum(
            1 for item in rubric_items if scores.get(item.id, {}).get("pass")
        )
        total = len(rubric_items)
        lines.append(f"**Score: {pass_count}/{total}**")
        lines.append("")
        for item in rubric_items:
            s = scores.get(item.id, {})
            status = "✅" if s.get("pass") else "❌"
            reason = s.get("reason", "")
            quote = s.get("quote", "")
            lines.append(f"### {status} {item.id}")
            lines.append(f"**Q:** {item.question}")
            if reason:
                lines.append(f"**Reason:** {reason}")
            if quote:
                lines.append(f"**Quote:** _{quote}_")
            lines.append("")

    lines += [
        "## Human Review",
        "",
    ]
    for item in rubric_items:
        lines.append(f"- [ ] Human review: **{item.id}** — {item.question}")
    lines.append("")

    lines += [
        "## Conversation",
        "",
        conversation_md,
    ]
    return "\n".join(lines)


# ── 主流程 ────────────────────────────────────────────────────────────────────


def run(scenario_path: str) -> Path:
    """运行单个 scenario，返回结果目录路径。"""
    scenario = parse_scenario(scenario_path)
    rubric = parse_rubric(str(_REPO_ROOT / scenario.rubric))

    # ── 结果目录 ──
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = _RESULTS_DIR / ts / scenario.scenario_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── offline fixture 复制 ──
    if scenario.mode == "offline" and scenario.fixture:
        _setup_fixture(scenario.fixture)

    # ── 生成临时 agent ──
    agent_name = agent_builder.build(scenario)
    print(f"[harness] Temp agent: {agent_name}")

    # ── 调用 opencode ──
    raw_output = ""
    try:
        cmd = [
            "opencode",
            "run",
            "--agent",
            agent_name,
            "--format",
            "json",
            "--dangerously-skip-permissions",
            scenario.input_text,
        ]
        print(f"[harness] Running: {' '.join(cmd[:5])} ...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
        )
        raw_output = result.stdout + result.stderr
    except FileNotFoundError:
        raw_output = f"[harness] opencode not found; skipping agent execution.\nInput: {scenario.input_text}"

    # ── 解析事件流 ──
    conversation_md, events = _parse_events(raw_output)
    if not conversation_md.strip():
        conversation_md = f"[No parseable events]\n\nRaw output:\n{raw_output[:2000]}"

    # ── 保存产出物 ──
    (out_dir / "conversation.md").write_text(conversation_md, encoding="utf-8")
    (out_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events),
        encoding="utf-8",
    )

    # ── judge 打分 ──
    scores = judge.score(conversation_md, rubric)
    (out_dir / "scores.json").write_text(
        json.dumps(scores, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # ── report.md ──
    report_md = _build_report(
        scenario.scenario_id, conversation_md, scores, rubric.items
    )
    (out_dir / "report.md").write_text(report_md, encoding="utf-8")

    print(f"[harness] Results saved: {out_dir}")

    # ── 清理临时 agent ──
    agent_builder.cleanup(scenario.scenario_id)

    return out_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Run agent eval scenario")
    parser.add_argument("--scenario", required=True, help="Path to scenario .md file")
    args = parser.parse_args()
    run(args.scenario)
    return 0


if __name__ == "__main__":
    sys.exit(main())
