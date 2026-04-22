from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "openrouter": {
        "model": "anthropic/claude-haiku-4.5",
        "base_url": "https://openrouter.ai/api/v1",
    },
    "trigger": {
        "double_c_window_ms": 400,
    },
    "popup": {
        "default_width": 320,
        "cursor_offset_x": 16,
        "cursor_offset_y": 16,
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def config_path() -> Path:
    return Path(__file__).resolve().parent.parent / "config.json"


def load_config() -> dict[str, Any]:
    path = config_path()
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                user_cfg = json.load(f)
            return _deep_merge(DEFAULT_CONFIG, user_cfg)
        except (OSError, json.JSONDecodeError):
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict[str, Any]) -> None:
    path = config_path()
    with path.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def debug_enabled() -> bool:
    return os.environ.get("TRANSLATO_DEBUG") == "1"
