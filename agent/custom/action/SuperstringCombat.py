"""MuMu 超弦空间战斗执行器。

战斗动作放在 agent/custom/profiles/superstring 下的 roles 和 teams 中，任务选项只负责选择档案。
每次节点重入只执行一个动作并重新检查战斗 HUD，避免结算画面继续点击技能。
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from maa.custom_action import CustomAction


CONFIG_ROOT = Path(__file__).resolve().parents[1] / "profiles" / "superstring"
DEFAULT_TOUCH_ACTIONS = {
    "attack": [1173, 615],
    "weapon": [1045, 512],
    "ultimate": [1184, 466],
    "dodge": [1028, 649],
    # 超弦空间这里是队友切换按钮，不能沿用乐土的“助战”命名。
    "switch_1": [1208, 147],
    "switch_2": [1203, 285],
    "star_ring": [914, 565],
    "jump": [1069, 373],
}


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"配置必须是对象：{path.name}")
    return value


class SuperstringCombat(CustomAction):
    def __init__(self):
        super().__init__()
        self.states = {}

    def _load_role(self, role, variant):
        role_candidates = (
            CONFIG_ROOT / "roles" / f"{variant}.json",
            CONFIG_ROOT / "roles" / f"{role}_{variant}.json",
        )
        role_path = next((path for path in role_candidates if path.is_file()), None)
        role_config = _read_json(role_path) if role_path else None
        if role_config is None:
            for path in sorted((CONFIG_ROOT / "roles").glob("*.json")):
                try:
                    candidate = _read_json(path)
                except (OSError, ValueError, json.JSONDecodeError):
                    continue
                if candidate.get("character") == role and candidate.get("variant") == variant:
                    role_config = candidate
                    break
        if role_config is None:
            raise FileNotFoundError(f"未找到角色档案：{role}/{variant}")
        if role_config.get("character") != role:
            raise ValueError(f"角色档案与选择不一致：{role}")
        return role_config

    def _load(self, params):
        role = str(params.get("role", "窈窕谍影"))
        variant = str(params.get("variant", "standard"))
        team = str(params.get("team", "default"))
        team_path = CONFIG_ROOT / "teams" / f"{team}.json"
        role_config = self._load_role(role, variant)
        team_config = _read_json(team_path)
        return role_config, team_config

    @staticmethod
    def _fighting(context, image):
        for node in ("战斗逻辑-战斗中", "角色战斗-生命HUD"):
            try:
                result = context.run_recognition(node, image)
            except Exception:
                continue
            if result and result.hit:
                return True
        return False

    @staticmethod
    def _actions(role_config, team_config):
        actions = []
        for action in team_config.get("opening", []):
            actions.append({"action": action, "interval_ms": 180})
        actions.extend(team_config.get("cycle", []))
        if not actions:
            actions = [{"action": action, "interval_ms": 180} for action in role_config.get("cycle", [])]
        return [item if isinstance(item, dict) else {"action": item, "interval_ms": 180} for item in actions]

    @staticmethod
    def _click(context, point):
        try:
            result = context.tasker.controller.post_click(int(point[0]), int(point[1])).wait()
            return bool(result and result.succeeded)
        except Exception as exc:
            print(f"SuperstringCombat 点击失败：{type(exc).__name__}: {exc}", flush=True)
            return False

    def _run_rotation(self, context, state, role_config, team_config, params, now):
        """按队伍 rotation 分阶段执行，只有配置明确要求时才切换角色。"""
        rotation = team_config.get("rotation")
        if not isinstance(rotation, list) or not rotation:
            return None
        phase_index = int(state.get("phase", 0)) % len(rotation)
        phase = rotation[phase_index]
        if not isinstance(phase, dict):
            raise ValueError(f"队伍 rotation 第 {phase_index + 1} 项必须是对象")

        phase_started = state.get("phase_started")
        if phase_started is None:
            switch_action = phase.get("switch")
            if switch_action:
                point = DEFAULT_TOUCH_ACTIONS.get(str(switch_action))
                if not point or not self._click(context, point):
                    return False
                state["last"][str(switch_action)] = now
            state["phase_started"] = now
            state["index"] = 0
            state["last"] = {}
            return True

        duration = float(phase.get("duration_s", 0))
        if duration > 0 and now - float(phase_started) >= duration:
            state["phase"] = (phase_index + 1) % len(rotation)
            state.pop("phase_started", None)
            state["index"] = 0
            state["last"] = {}
            return True

        phase_role = str(phase.get("role", params.get("role", "窈窕谍影")))
        phase_variant = str(phase.get("variant", params.get("variant", "standard")))
        phase_config = self._load_role(phase_role, phase_variant)
        actions = phase.get("cycle") or phase_config.get("cycle", [])
        actions = [item if isinstance(item, dict) else {"action": item, "interval_ms": 180} for item in actions]
        if not actions:
            raise ValueError(f"角色阶段没有可执行动作：{phase_role}/{phase_variant}")
        for _ in range(len(actions)):
            item = actions[state["index"] % len(actions)]
            state["index"] = (state["index"] + 1) % len(actions)
            action = str(item.get("action", "attack"))
            interval = float(item.get("interval_ms", 180)) / 1000.0
            if now - state["last"].get(action, -1000.0) < interval:
                continue
            point = phase_config.get("touch_actions", {}).get(action) or DEFAULT_TOUCH_ACTIONS.get(action)
            if not point or len(point) != 2:
                raise ValueError(f"角色阶段缺少触摸坐标：{phase_role}/{action}")
            if not self._click(context, point):
                return False
            state["last"][action] = now
            return True
        return True

    def run(self, context, argv):
        raw = getattr(argv, "custom_action_param", None)
        if isinstance(raw, str):
            try:
                params = json.loads(raw or "{}")
            except json.JSONDecodeError:
                params = {}
        else:
            params = raw if isinstance(raw, dict) else {}

        try:
            role_config, team_config = self._load(params)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"SuperstringCombat 配置错误：{exc}", flush=True)
            return False

        task_id = getattr(getattr(argv, "task_detail", None), "task_id", "superstring")
        state = self.states.setdefault(task_id, {"index": 0, "last": {}})
        image = context.tasker.controller.post_screencap().wait().get()
        if image is None:
            return False
        if not self._fighting(context, image):
            return True

        actions = self._actions(role_config, team_config)
        if not actions:
            print("SuperstringCombat 没有可执行的动作", flush=True)
            return False

        now = time.monotonic()
        if team_config.get("rotation"):
            try:
                rotated = self._run_rotation(context, state, role_config, team_config, params, now)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                print(f"SuperstringCombat 队伍轮转配置错误：{exc}", flush=True)
                return False
            if rotated is not None:
                return rotated

        for _ in range(len(actions)):
            item = actions[state["index"] % len(actions)]
            state["index"] = (state["index"] + 1) % len(actions)
            action = str(item.get("action", "attack"))
            interval = float(item.get("interval_ms", 180)) / 1000.0
            if now - state["last"].get(action, -1000.0) < interval:
                continue
            point = role_config.get("touch_actions", {}).get(action) or DEFAULT_TOUCH_ACTIONS.get(action)
            if not point or len(point) != 2:
                print(f"SuperstringCombat 缺少触摸坐标：{action}", flush=True)
                return False
            if context.tasker.stopping:
                return False
            if not self._click(context, point):
                return False
            state["last"][action] = now
            return True
        return True
