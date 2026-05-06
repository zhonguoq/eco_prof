"""
harness/judge.py — LLM judge（ADR-003 决策 12、13）

One-shot prompt：把完整 rubric + 完整对话送给 judge，
要求返回 JSON：{<rubric_id>: {"pass": bool, "reason": str, "quote": str}}

若 judge 漏答某条 rubric item，per-item 补评。
使用 openai SDK（openai-compatible endpoint）调 DeepSeek。
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from .config import judge_config
from .parser import Rubric


def _build_prompt(conversation: str, rubric: Rubric) -> str:
    rubric_lines = "\n".join(
        f"- id: {item.id}\n  question: {item.question}" for item in rubric.items
    )
    return f"""你是一个严格的 agent 行为评审员。
请根据以下 rubric 评审 agent 对话，逐条判断每个 rubric item 是否通过。

## Rubric
{rubric_lines}

## 对话内容
{conversation}

## 输出要求
请返回严格的 JSON，格式如下（不要输出任何其他内容）：
{{
  "<rubric_item_id>": {{
    "pass": true 或 false,
    "reason": "简短中文理由",
    "quote": "对话中的相关原文片段（≤100字）"
  }}
}}

每条 rubric item 都必须有对应的答案。"""


def _parse_json_response(text: str) -> Dict[str, Any]:
    """从 LLM 回复中提取 JSON 对象。"""
    # 去掉 markdown code fence
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    return json.loads(text)


def score(conversation: str, rubric: Rubric) -> Dict[str, Any]:
    """
    调用 judge LLM 对对话打分。

    返回：{rubric_item_id: {"pass": bool, "reason": str, "quote": str}}
    若 DEEPSEEK_API_KEY 未设置，返回 {"_skipped": True}。
    """
    cfg = judge_config()
    api_key = cfg.get("api_key", "")
    if not api_key:
        return {"_skipped": True, "_reason": "DEEPSEEK_API_KEY not set"}

    try:
        from openai import OpenAI
    except ImportError:
        return {"_skipped": True, "_reason": "openai package not installed"}

    client = OpenAI(
        api_key=api_key,
        base_url=cfg.get("base_url", "https://api.deepseek.com/v1"),
        timeout=cfg.get("timeout_seconds", 60),
    )

    prompt = _build_prompt(conversation, rubric)
    response = client.chat.completions.create(
        model=cfg.get("model", "deepseek-chat"),
        messages=[{"role": "user", "content": prompt}],
        temperature=cfg.get("temperature", 0.0),
    )
    raw = response.choices[0].message.content or ""

    try:
        scores = _parse_json_response(raw)
    except json.JSONDecodeError:
        scores = {"_parse_error": True, "_raw": raw}
        return scores

    # ── schema 校验：补评漏答的 item ──
    missing = [item for item in rubric.items if item.id not in scores]
    if missing:
        scores = _fill_missing(client, cfg, conversation, missing, scores)

    return scores


def _fill_missing(
    client: Any,
    cfg: Dict[str, Any],
    conversation: str,
    missing: List[Any],
    existing: Dict[str, Any],
) -> Dict[str, Any]:
    """对漏答的 rubric item 逐条补评。"""
    for item in missing:
        prompt = f"""请评审以下对话，判断单条 rubric item 是否通过：

- id: {item.id}
  question: {item.question}

## 对话内容
{conversation}

## 输出要求
返回严格 JSON（不含其他内容）：
{{"{item.id}": {{"pass": true/false, "reason": "中文理由", "quote": "原文片段"}}}}"""

        resp = client.chat.completions.create(
            model=cfg.get("model", "deepseek-chat"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        raw = resp.choices[0].message.content or ""
        try:
            part = _parse_json_response(raw)
            existing.update(part)
        except json.JSONDecodeError:
            existing[item.id] = {"pass": False, "reason": "补评解析失败", "quote": ""}
    return existing
