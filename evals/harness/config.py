"""
harness/config.py — 读取 evals/config.yaml（ADR-003 决策 13）
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def load_config() -> Dict[str, Any]:
    """加载 evals/config.yaml，返回配置字典。"""
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def judge_config() -> Dict[str, Any]:
    """返回 judge 配置块，并解析 api_key_env → api_key。"""
    cfg = load_config().get("judge", {})
    api_key_env = cfg.get("api_key_env", "DEEPSEEK_API_KEY")
    cfg["api_key"] = os.environ.get(api_key_env, "")
    return cfg
