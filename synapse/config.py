from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "active_provider": "openrouter",
    "custom_prompt": "",
    "preferred_dst_lang": "en",
    "ui_lang": "en",
    "openrouter": {
        "model": "anthropic/claude-haiku-4.5",
        "base_url": "https://openrouter.ai/api/v1",
    },
    "anthropic": {
        "model": "claude-haiku-4-5",
    },
    "trigger": {
        "double_c_window_ms": 400,
    },
    "popup": {
        "default_width": 480,
        "default_height": 280,
        "cursor_offset_x": 16,
        "cursor_offset_y": 16,
        "close_on_copy": False,
    },
    "editor": {
        "width": 900,
        "height": 520,
        "debounce_ms": 500,
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
    if getattr(sys, "frozen", False):
        # In a PyInstaller build, store config.json next to Synapse.exe rather
        # than inside _MEIPASS (that folder is recreated on every launch).
        return Path(sys.executable).resolve().parent / "config.json"
    return Path(__file__).resolve().parent.parent / "config.json"


def load_config() -> dict[str, Any]:
    path = config_path()
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                user_cfg = json.load(f)
            return _deep_merge(DEFAULT_CONFIG, user_cfg)
        except json.JSONDecodeError:
            # Broken JSON — save it as .bak so the next save does not
            # silently overwrite the user's settings.
            try:
                backup = path.with_suffix(path.suffix + ".bak")
                path.replace(backup)
            except OSError:
                pass
        except OSError:
            pass
    return copy.deepcopy(DEFAULT_CONFIG)


def save_config(cfg: dict[str, Any]) -> None:
    # Atomic write: write to a temp file in the same folder, then os.replace.
    # A crash mid-write will not truncate config.json.
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def debug_enabled() -> bool:
    return os.environ.get("SYNAPSE_DEBUG") == "1"
