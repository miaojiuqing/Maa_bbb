"""短周期角色执行器。每次输入前重新检查战斗 HUD，支持随时停止。"""
import json
import time
import re

from maa.custom_action import CustomAction
from ...utils.CharacterProfiles import CHARACTER_PROFILES, MUMU_TOUCH_ACTIONS


class CharacterCombat(CustomAction):
    def __init__(self):
        super().__init__()
        self.support_at = {}
        self.signet_check_at = {}
        self.ultimate_at = {}
        self.star_ring_at = {}
        self.dodge_at = {}
        self.target_lock_at = {}
        self.movement_at = {}
        self.movement_index = {}
        self.branch_at = {}

    def run(self, context, argv):
        try:
            return self._run(context, argv)
        except Exception as exc:
            # 异常不得越过 ctypes 回调边界，否则框架可能继续高速重试。
            print(f"CharacterCombat stopped: {type(exc).__name__}: {exc}", flush=True)
            return False

    def _run(self, context, argv):
        raw_params = getattr(argv, "custom_action_param", None)
        if isinstance(raw_params, str):
            try:
                params = json.loads(raw_params or "{}")
            except json.JSONDecodeError:
                params = {}
        else:
            params = raw_params or {}
        if not isinstance(params, dict):
            params = {}
        role = params.get("character")
        variant = params.get("variant")
        profile = CHARACTER_PROFILES.get(role, {}).get("variants", {}).get(variant)
        if not profile or params.get("confirmed_signet") != profile["requires_signet"]:
            print("CharacterCombat: 角色/变体/核心刻印未确认，停止输入", flush=True)
            return False
        key = (argv.task_detail.task_id, role, variant)
        actions = list(profile["cycle"])
        now = time.monotonic()
        if profile.get("ultimate") and now - self.ultimate_at.get(key, -1000) >= profile.get("ultimate_interval_s", 15):
            actions.insert(0, "ultimate")
        if profile.get("star_ring") and now - self.star_ring_at.get(key, -1000) >= profile.get("star_ring_interval_s", 18):
            actions.insert(0, "star_ring")
        if profile.get("dodge") and now - self.dodge_at.get(key, -1000) >= profile.get("dodge_interval_s", 2.2):
            actions.insert(0, "dodge")
        if profile.get("target_lock") and now - self.target_lock_at.get(key, -1000) >= profile.get("target_lock_interval_s", 3.0):
            actions.insert(0, "target_lock")
        if profile.get("movement") and now - self.movement_at.get(key, -1000) >= profile.get("movement_interval_s", 1.8):
            # 可选的定时移动；华裳配置不启用，不能替代场景中的接敌判断。
            actions.insert(0, "movement")
        if profile.get("branch") and now - self.branch_at.get(key, -1000) >= profile.get("branch_interval_s", 6.0):
            # 出招表中的“攻击（长按）”是分支·无声的利刃；它不能用一次
            # Click 代替，否则只会继续普通攻击而丢失高倍率分支。
            actions.insert(0, "branch")
        if profile.get("elysian_support") and time.monotonic()-self.signet_check_at.get(key,-1000)>=3:
            actions.insert(0,"elysian_support")
        if time.monotonic() - self.support_at.get(key, -1000) >= profile["support_interval_s"]:
            actions = list(profile["opening"]) + actions
        for action in actions:
            if context.tasker.stopping:
                return False
            image = context.tasker.controller.post_screencap().wait().get()
            active = context.run_recognition("战斗逻辑-战斗中", image)
            if not active or not active.hit:
                return True
            hud = context.run_recognition("角色战斗-生命HUD", image)
            if not hud or not hud.hit:
                return True
            disabled = context.run_recognition("角色战斗-战后禁用", image)
            if disabled and disabled.hit:
                print("CharacterCombat: post-battle HUD, no input", flush=True)
                return False
            if action == "elysian_support":
                self.signet_check_at[key]=time.monotonic()
                charge=context.run_recognition("角色战斗-英桀助战充能",image)
                values=re.findall(r"(\d{2,4})[/7](\d{2,4})", "".join(r.text for r in charge.all_results)) if charge and charge.hit else []
                if not any(a==b and int(a)>0 for a,b in values):continue
            if action == "movement":
                if not self._move_short(context, key, profile):
                    return False
                self.movement_at[key] = time.monotonic()
                print(f"CharacterCombat: {role}/{variant} movement", flush=True)
                deadline = time.monotonic() + profile["interval_ms"] / 1000
                while time.monotonic() < deadline:
                    if context.tasker.stopping:
                        return False
                    time.sleep(0.02)
                continue
            if action == "branch":
                if not self._hold_attack(context, profile):
                    return False
                self.branch_at[key] = time.monotonic()
                print(f"CharacterCombat: {role}/{variant} branch", flush=True)
                deadline = time.monotonic() + profile["interval_ms"] / 1000
                while time.monotonic() < deadline:
                    if context.tasker.stopping:
                        return False
                    time.sleep(0.02)
                continue
            # 战后仍有生命条，但武器位已变成刷新门按钮，必须单独拒绝。
            result = context.run_action("角色战斗-触摸", pipeline_override={
                "角色战斗-触摸": {"action": {"type": "Click", "param": {
                    "target": [*MUMU_TOUCH_ACTIONS[action], 1, 1]
                }}}
            })
            if not result or not result.success:
                return False
            print(f"CharacterCombat: {role}/{variant} {action}", flush=True)
            if action == "support_2":
                self.support_at[key] = time.monotonic()
            elif action == "ultimate":
                self.ultimate_at[key] = time.monotonic()
            elif action == "star_ring":
                self.star_ring_at[key] = time.monotonic()
            elif action == "dodge":
                self.dodge_at[key] = time.monotonic()
            elif action == "target_lock":
                self.target_lock_at[key] = time.monotonic()
            deadline = time.monotonic() + profile["interval_ms"] / 1000
            while time.monotonic() < deadline:
                if context.tasker.stopping:
                    return False
                time.sleep(0.02)
        return True

    def _move_short(self, context, key, profile):
        """相对当前视角短走；不代表已锁定敌人。"""
        controller = context.tasker.controller
        vectors = profile.get("movement_vectors") or ((0, -62), (38, -50), (-38, -50), (0, -62))
        index = self.movement_index.get(key, 0)
        dx, dy = vectors[index % len(vectors)]
        self.movement_index[key] = index + 1
        try:
            if not controller.post_touch_down(153, 571).wait().succeeded:
                return False
            if not controller.post_touch_move(153 + int(dx), 571 + int(dy)).wait().succeeded:
                controller.post_touch_up().wait()
                return False
            time.sleep(float(profile.get("movement_hold_ms", 260)) / 1000.0)
            return controller.post_touch_up().wait().succeeded
        except Exception as exc:
            print(f"CharacterCombat movement stopped: {type(exc).__name__}: {exc}", flush=True)
            try:
                controller.post_touch_up().wait()
            except Exception:
                pass
            return False

    def _hold_attack(self, context, profile):
        controller = context.tasker.controller
        x, y = MUMU_TOUCH_ACTIONS["attack"]
        try:
            if not controller.post_touch_down(x, y).wait().succeeded:
                return False
            time.sleep(float(profile.get("branch_hold_ms", 520)) / 1000.0)
            return controller.post_touch_up().wait().succeeded
        except Exception as exc:
            print(f"CharacterCombat branch stopped: {type(exc).__name__}: {exc}", flush=True)
            try:
                controller.post_touch_up().wait()
            except Exception:
                pass
            return False
