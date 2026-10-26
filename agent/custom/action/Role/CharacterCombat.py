"""短周期角色执行器。每次输入前重新检查战斗 HUD，支持随时停止。"""
import json
import time
import re

from maa.custom_action import CustomAction
from ...utils import DesktopInput
from ...utils.CharacterProfiles import CHARACTER_PROFILES, MUMU_TOUCH_ACTIONS

# 安卓端（模拟器）只能走触摸坐标；桌面端资源包会提供 角色战斗-按键-<动作> 节点改用键码。
TOUCH_NODE = "角色战斗-触摸"
# 长按使用独立触摸点：周期性点按走 contact=0，其 touch_up 会把同一 touch 的按住一起抬起。
HOLD_CONTACT = 1
# 按住期间定期刷新一次（松开→立即重按）：修复误判战斗后"幽灵按住"导致下一层不普攻。
HOLD_REFRESH_S = 5.0


class CharacterCombat(CustomAction):
    def __init__(self):
        super().__init__()
        self.input_nodes = {}
        self.support_at = {}
        self.signet_check_at = {}
        self.ultimate_at = {}
        self.star_ring_at = {}
        self.dodge_at = {}
        self.target_lock_at = {}
        self.movement_at = {}
        self.movement_index = {}
        self.branch_at = {}
        self.holding = False
        self.hold_key = None
        self.hold_release = True
        self.hold_at = 0.0

    def _drop_hold(self, context):
        """画面已不是战斗：立即松开并清掉记账，避免把"幽灵按住"带进下一层。"""
        if self.hold_key is None:
            return
        self.holding = False
        self.hold_key = None
        self._release_attack(context)

    def run(self, context, argv):
        self.holding = False
        self.hold_release = True
        try:
            return self._run(context, argv)
        except Exception as exc:
            # 异常不得越过 ctypes 回调边界，否则框架可能继续高速重试。
            print(f"CharacterCombat stopped: {type(exc).__name__}: {exc}", flush=True)
            return False
        finally:
            # 只有判定为战斗结束/停止/异常时才松开；动作跑完会保持按住，
            # 由下一次节点重入接着按住并轮转周期动作。
            if self.holding and self.hold_release:
                self.holding = False
                self.hold_key = None
                self._release_attack(context)

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
        if profile.get("branch") and not profile.get("hold_attack") and now - self.branch_at.get(key, -1000) >= profile.get("branch_interval_s", 6.0):
            # 出招表中的“攻击（长按）”是分支·无声的利刃；它不能用一次
            # Click 代替，否则只会继续普通攻击而丢失高倍率分支。
            actions.insert(0, "branch")
        if profile.get("elysian_support") and time.monotonic()-self.signet_check_at.get(key,-1000)>=3:
            actions.insert(0,"elysian_support")
        if time.monotonic() - self.support_at.get(key, -1000) >= profile["support_interval_s"]:
            actions = list(profile["opening"]) + actions
        if profile.get("hold_attack"):
            # 全程按住普攻：按住期间不再点攻击；其他动作走不同按钮，与按住互不冲突。
            actions = [a for a in actions if a != "attack"]
            if self.hold_key is not None and self.hold_key != key:
                # 上一场没松开（异常退出等）先补一次松开，避免按键残留。
                self._release_attack(context)
                self.hold_key = None
            self.holding = True
            self.hold_release = True          # 任何提前返回都松手；正常跑完会改回 False
            if self.hold_key != key:
                if not self._press_attack(context):
                    return False
                self.hold_key = key
                self.hold_at = time.monotonic()
            elif time.monotonic() - self.hold_at >= HOLD_REFRESH_S:
                # 两个节点无 pre/post_delay：松开后立刻重按，空档只有一次 adb 往返（约 10~40ms）。
                self._release_attack(context)
                self.hold_at = time.monotonic()
                if not self._press_attack(context):
                    return False
            if not actions:
                # cycle 为空且没有其它待执行动作：只做一轮 HUD 检查就返回，
                # 由节点重入去执行到期的周期动作；按住状态通过跨调用保持。
                print(f"CharacterCombat: {role}/{variant} hold_attack 持续按住，直到战斗结束", flush=True)
                if context.tasker.stopping:
                    return False
                image = context.tasker.controller.post_screencap().wait().get()
                active = context.run_recognition("战斗逻辑-战斗中", image)
                if not active or not active.hit:
                    self._drop_hold(context)
                    return True
                hud = context.run_recognition("角色战斗-生命HUD", image)
                if not hud or not hud.hit:
                    self._drop_hold(context)
                    return True
                disabled = context.run_recognition("角色战斗-战后禁用", image)
                if disabled and disabled.hit:
                    print("CharacterCombat: post-battle HUD, no input", flush=True)
                    return False
                time.sleep(profile["interval_ms"] / 1000.0)
                self.hold_release = False     # 战斗仍在：保持按住
                return True
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
            node = self._input_node(context, action)
            if node == TOUCH_NODE:
                result = context.run_action(node, pipeline_override={
                    node: {"action": {"type": "Click", "param": {
                        "target": [*MUMU_TOUCH_ACTIONS[action], 1, 1]
                    }}}
                })
            else:
                result = context.run_action(node)
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
        self.hold_release = False  # 动作跑完、战斗仍在：保持按住
        return True

    def _input_node(self, context, action):
        """返回该动作要执行的节点名：桌面端用键码节点，缺失时回退触摸点击。"""
        cached = self.input_nodes.get(action)
        if cached:
            return cached
        candidate = f"角色战斗-按键-{action}"
        try:
            name = candidate if context.get_node_data(candidate) else TOUCH_NODE
        except Exception:
            name = TOUCH_NODE
        self.input_nodes[action] = name
        return name

    def _touch_based(self, context, node):
        """桌面端按键节点没有接触点概念；只有触摸型节点才需要指定 contact。"""
        try:
            data = context.get_node_data(node) or {}
        except Exception:
            return True
        action = data.get("action") if isinstance(data, dict) else None
        action_type = action.get("type") if isinstance(action, dict) else action
        return action_type in (None, "TouchDown", "TouchUp")

    def _press_attack(self, context):
        """按下普攻并保持；触摸型节点用独立 contact，避免被点按的 touch_up 抬起。"""
        override = None
        if self._touch_based(context, "按下攻击_action"):
            override = {"按下攻击_action": {"action": {"param": {"contact": HOLD_CONTACT}}}}
        result = context.run_action("按下攻击_action", pipeline_override=override)
        return bool(result and result.success)

    def _release_attack(self, context):
        try:
            override = None
            if self._touch_based(context, "松开攻击_action"):
                override = {"松开攻击_action": {"action": {"param": {"contact": HOLD_CONTACT}}}}
            context.run_action("松开攻击_action", pipeline_override=override)
        except Exception as exc:
            print(f"CharacterCombat release stopped: {type(exc).__name__}: {exc}", flush=True)

    def _move_short(self, context, key, profile):
        """相对当前视角短走；不代表已锁定敌人。"""
        controller = context.tasker.controller
        vectors = profile.get("movement_vectors") or ((0, -62), (38, -50), (-38, -50), (0, -62))
        index = self.movement_index.get(key, 0)
        dx, dy = vectors[index % len(vectors)]
        self.movement_index[key] = index + 1
        held = DesktopInput.hold(context)  # 桌面端要先按住 Alt 才能拖视角，安卓端恒为 False
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
        finally:
            DesktopInput.release(context, held)

    def _hold_attack(self, context, profile):
        """长按攻击：桌面端用 LongPressKey 节点，安卓端用触摸按下-抬起。"""
        node = self._input_node(context, "branch")
        if node != TOUCH_NODE:
            result = context.run_action(node)
            return bool(result and result.success)
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
