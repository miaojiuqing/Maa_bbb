"""从 characters 目录加载乐土角色和流派配置。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CHARACTER_DIR = PROJECT_ROOT / "characters"


def _load_profiles() -> tuple[dict[str, Any], dict[str, list[int]]]:
    profiles: dict[str, Any] = {}
    touch_actions: dict[str, list[int]] = {}

    for path in sorted(CHARACTER_DIR.glob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"角色配置跳过 {path.name}: {exc}", flush=True)
            continue

        character = document.get("character")
        variant = document.get("variant")
        profile = document.get("profile")
        if not isinstance(character, str) or not isinstance(variant, str) or not isinstance(profile, dict):
            print(f"角色配置跳过 {path.name}: 缺少 character、variant 或 profile", flush=True)
            continue

        profiles.setdefault(character, {"variants": {}})["variants"][variant] = profile
        actions = document.get("touch_actions", {})
        if isinstance(actions, dict):
            touch_actions.update(actions)

    return profiles, touch_actions


CHARACTER_PROFILES, MUMU_TOUCH_ACTIONS = _load_profiles()
