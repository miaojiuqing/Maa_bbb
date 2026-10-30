"""MuMu 深层序列流程。每次只根据当前画面推进一步，出招仍由角色模块负责。"""
import json
import re
import time
import traceback
import threading
from pathlib import Path
from types import SimpleNamespace
from PIL import Image
from maa.custom_action import CustomAction
from .Role.CharacterCombat import CharacterCombat
from .ElysianPanelAction import ElysianPanelAction
from ..utils.ElysianPolicy import RunState, FAMILY_MARKERS, GATE_NAMES, KNOWN_SIGNETS, normalize, score_signet, choose_gate, choice_rows, gate_order, read_floor, shop_rows, signet_detail_open, signet_disabled
from ..utils.ElysianVision import dormant_anchors, red_portals
from ..utils import DesktopInput
from ..utils.CharacterProfiles import CHARACTER_PROFILES


# 进入第一层后游戏还会播放出生动画并生成初始专属刻印，过早打开暂停菜单
# 会把“尚未选择”误判为“没有必需专属”。
INITIAL_SIGNET_GRACE_S = 8
GATE_CLICK_CHECK_S = 3
GATE_LOAD_WAIT_S = 30
# 点击「前往」后若既没切层也没有加载迹象（常见于擦过传送门：OCR 短暂看到「前往」），
# 先反向走一小步 + 转视角，再重新靠近最近的门；重试有上限，用尽后回到原有超时逻辑。
GATE_ENTER_RETRY_S = 5.0
GATE_ENTER_RECOVERIES = 3
GATE_CLICK_OFFSETS = (80, 0, 110)
# 桌面端「前往」长条更窄且更靠右：偏移与兜底点各用一套，避免第三次点击落到框外。
GATE_CLICK_OFFSETS_PC = (40, 0, 70)
GATE_CLICK_MAX_ATTEMPTS = 6
GATE_AFTER_PAUSE_ATTEMPTS = 3
GATE_PAUSE_WAIT_S = 10
# 商店层：门藏在商店后面时，向前挪动的最大步数（每步都要本帧仍看到商店才继续）
SHOP_PASS_STEPS = 8
# 传送锚点面板（减负/挑战奖励层）：三张卡位置固定，门名是卡片顶部文字（1280×720 逻辑坐标）
GATE_PANEL_BANDS = ((0, 500), (500, 795), (795, 1280))
GATE_PANEL_POINTS = ((352, 350), (647, 350), (943, 350))
GATE_PANEL_WAIT_S = 1.2
# 不同场景背景下「前往」小卡片的 OCR 可能整体读不到；门名已确认时按门前标准位置补点。
GATE_BLIND_READS = 3
GATE_BLIND_PROMPT = (728, 285)
# 1080p 窗口实测「前往」文字中心（换算到 1280×720）：桌面端比模拟器右移约 50、下移约 15。
GATE_BLIND_PROMPT_PC = (778, 300)


def pipeline():
    return {
        "乐土自动-OCR": {"recognition": "OCR", "expected": [".+"], "post_delay": 0},
        "乐土自动-门": {"recognition": "NeuralNetworkDetect", "model": "best.onnx", "expected": list(range(25)), "roi": [0, 0, 1280, 720], "post_delay": 0},
        "乐土自动-刷新门": {"recognition": "TemplateMatch", "template": ["自动战斗识别/窈窕谍影/战后刷新门.png"], "roi": [985,450,125,120], "threshold": .72, "post_delay": 0},
        "乐土自动-执行": {"action": {"type": "Custom", "param": {"custom_action": "ElysianRun"}}, "next": [], "pre_delay": 0, "post_delay": 0},
        "乐土自动-暂停": {"action": {"type": "Custom", "param": {"custom_action": "ElysianPause"}}, "next": [], "pre_delay": 0, "post_delay": 0},
    }


class RunHalt(Exception): pass


class ElysianRun(CustomAction):
    def __init__(self, stop_event, report, preview, root):
        super().__init__()
        self.stop_event, self.report, self.preview = stop_event, report, preview
        self.root = Path(root)
        self.state = RunState()
        self.motion = ElysianPanelAction(stop_event, report, preview)
        self.combat = CharacterCombat()
        self.output = None

    def stopped(self): return self.stop_event.is_set() or self.context.tasker.stopping

    def profile(self):
        """当前角色档案；run() 已校验角色与流派，流程内只负责取用。"""
        return CHARACTER_PROFILES[self.state.role]["variants"][self.state.variant]

    def required_signet(self):
        """本流派的必需专属刻印，替代原先写死的华裳。"""
        return self.profile()["requires_signet"]

    def capture(self):
        image = self.context.tasker.controller.post_screencap().wait().get()
        if image is None: raise RunHalt("MuMu 截图失败，请检查模拟器连接")
        self.frame = image
        self.preview(image)
        return image

    def read(self):
        self.capture()
        result = self.context.run_recognition("乐土自动-OCR", self.frame)
        self.items = [{"text": r.text, "box": list(r.box)} for r in result.all_results] if result and result.hit else []
        self.text = normalize("".join(r["text"] for r in self.items))
        return self.text

    def hit(self, name):
        result = self.context.run_recognition(name, self.frame)
        return result if result and result.hit else None

    def arena(self):
        """战斗中判定：优先看「战斗中」模板，其次血量 HUD，最后排除普攻键禁用态。

        「战斗中」模板在桌面端实测可命中（0.94），命中即可确认还在战斗；
        血量 OCR 在低血量/特效遮挡时会读成没有斜杠的串（如 "1366"），
        不能单独作为必要判据，否则燃血角色会把战斗画面判成非战斗。
        禁用态模板命中 = 战后/脱战；减负层选完刻印后直接出传送门，按导航处理。
        """
        if "抵达层数-减负层" in self.text:
            return False
        # 「战斗中」模板在桌面端同样能命中（实测 0.94），命中即可确认还在战斗，
        # 不必再依赖血量 OCR——血量文本在低血量/特效遮挡时会读成没有斜杠的串。
        if not self.hit("战斗逻辑-战斗中"):
            # 血量要允许个位数：浮生·渡尘之羽靠燃血作战，血量常被压到 1/13658，
            # 旧写法要求两侧至少两位，会把满屏战斗画面判成非战斗而转去找门。
            hud = bool(self.find(r"^\d{1,5}/\d{1,5}$", [296, 620, 165, 42])) or bool(self.hit("角色战斗-生命HUD"))
            if not hud:
                return False
        if self.hit("角色战斗-战后禁用"):
            return False
        return True

    def find(self, pattern, roi=None):
        for item in self.items:
            x, y, w, h = item["box"]
            if roi and not (roi[0] <= x+w/2 <= roi[0]+roi[2] and roi[1] <= y+h/2 <= roi[1]+roi[3]): continue
            if re.search(pattern, normalize(item["text"])): return item
        return None

    def click(self, x, y, delay=.45):
        if self.stopped(): return False
        # 桌面端键鼠方案下游戏不主动唤出光标，PostMessage 形式的点击对 3D 场景 HUD
        # （如左上角暂停键）无效；与 swipe 保持一致，先按住 Alt 再点，安卓端恒为 False。
        held = DesktopInput.hold(self.context)
        try:
            if not self.context.tasker.controller.post_click(int(x), int(y)).wait().succeeded:
                raise RunHalt("触摸点击失败，已停止")
        finally:
            DesktopInput.release(self.context, held)
        self.stop_event.wait(delay)
        return True

    def click_text(self, pattern, roi=None, delay=.45):
        item = self.find(pattern, roi)
        if item:
            x, y, w, h = item["box"]
            return self.click(x+w/2, y+h/2, delay)
        return False

    def swipe(self, x1, y1, x2, y2, ms=250):
        if self.stopped(): return
        held = DesktopInput.hold(self.context)  # 桌面端靠 Alt+拖动转视角，安卓端恒为 False
        try:
            if not self.context.tasker.controller.post_swipe(x1, y1, x2, y2, ms).wait().succeeded:
                raise RunHalt("滑动输入失败")
        finally:
            DesktopInput.release(self.context, held)
        self.stop_event.wait(.3)

    def save(self, picture=False):
        if not self.output: return
        data = self.state.to_dict()
        data["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        (self.output / "state.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        if picture and getattr(self, "frame", None) is not None:
            name = f"{time.time_ns()}-floor{self.state.floor}.png"
            Image.fromarray(self.frame[:, :, ::-1]).save(self.output / name)
            (self.output / name.replace(".png", ".json")).write_text(json.dumps(getattr(self, "items", []), ensure_ascii=False), encoding="utf-8")

    def phase(self, name, detail=""):
        changed = name != self.state.phase
        self.state.phase = name
        msg = f"第 {self.state.floor or '?'} / {self.state.total} 层 · {name}" + (f" · {detail}" if detail else "")
        if msg != getattr(self, "last_message", ""):
            self.report(msg); self.last_message = msg
            with (self.output / "events.log").open("a", encoding="utf-8") as log:
                log.write(time.strftime("%H:%M:%S ") + msg + "\n")
        self.save(changed)

    def detect_gates(self):
        result = self.context.run_recognition("乐土自动-门", self.frame)
        return result.raw_detail.get("all", []) if result else []

    def update_floor(self):
        observed = read_floor(self.items)
        if not observed:
            self.floor_candidate=None
            return
        if observed:
            floor, total = observed
            # 特效遮住十位数字时，17/17 会被读成 7/17；同一局楼层不会倒退。
            if self.state.floor and not self.state.floor <= floor <= self.state.floor+1:
                self.floor_candidate=None
                return
            if 1 <= total <= 22 and 1 <= floor <= total+1:
                if floor == self.state.floor:self.floor_candidate=None
                if floor != self.state.floor:
                    if getattr(self, 'floor_candidate', None) != observed:
                        self.floor_candidate=observed
                        self.floor_candidate_reads=1
                        return
                    self.floor_candidate_reads += 1
                    if self.floor_candidate_reads < 2:return
                if self.final_clear and self.final_gate_clicked and floor>17:self.final_exit=True
                if floor != self.state.floor:
                    self.state.floor, self.state.total = floor, total
                    self.target = None; self.state.target = ""
                    self.nav_steps = self.turns = 0
                    self.nav_recoveries=self.lost_frames=0;self.nav_started=0
                    self.frame_target=None;self.frame_lost=0
                    self.shop_done=False
                    self.shop_steps=0
                    self.battle_finished = False
                    self.active_hud_frames=0
                    self.floor_since = time.monotonic()
                    self.progress_at = time.monotonic()
                    self.gate_pause_used = False
                    self.gate_recovery_phase = None
                    self.enter_attempts = self.enter_failure_reads = 0
                    self.enter_recovery = 0
                    # 每层开场必放一次大招：清掉终结技计时，让本层第一次战斗调用立刻插入 ultimate。
                    self.combat.ultimate_at.clear()
                    self.phase("进入楼层")
                if self.enter_pending is not None and floor != self.enter_pending:
                    self.enter_pending = None
                    self.enter_attempts = self.enter_failure_reads = 0
                    self.phase("进门成功")

    def sync_pause(self):
        if self.final_exit:
            self.phase("结算深层序列", "已按要求进入任选英桀门，现在退出结算")
            if not self.click_text('放弃并结算',[200,570,500,150],.8):
                self.click_text('^战况报告$',[0,170,210,110])
            return
        self.phase("检查本局", "读取角色与已获刻印")
        if not self.state.role_verified:
            role = normalize(self.state.role)
            if self.find(re.escape(role), [230, 70, 1020, 150]):
                self.state.role_verified = True
            elif "状态列表" in self.text and role not in self.text and self.find("状态列表", [220, 0, 900, 90]):
                raise RunHalt(f"状态列表中的角色不是{self.state.role}；请更换为当前适配角色")
            else:
                self.click_text("^状态列表$", [0, 320, 210, 380]); return
        if not self.state.build_verified:
            if self.state.floor==0:
                # 出生动画期间还没弹出初始专属；先恢复，等实际楼层/选刻印出现。
                if not self.click_text('^继续战斗$',[800,570,480,150],.6):self.click_text('^战况报告$',[0,170,210,110])
                return
            if "增益列表" not in self.text:
                self.click_text("^往世乐土$", [0, 90, 210, 120]); return
            plan = self.profile()["signet_plan"]
            required = self.required_signet()
            # 已获刻印按当前角色方案列举，新增角色不需要改脚本；
            # FAMILY_MARKERS 兜住暂停菜单只显示体系标题（没有核心名）的体系。
            for name in dict.fromkeys([required] + list(FAMILY_MARKERS)
                                      + list(plan.get("exclusive", [])) + list(plan.get("cores", []))):
                if name in self.text: self.state.record(name)
            # 接管可能发生在第一层 HUD 出现、初始专属刻印尚未弹出的瞬间。
            # 此时暂停菜单里的增益列表只有追忆之证，不能把“尚未选择”当成
            # “已经选错”。继续战斗后，下一轮 step 会优先处理刻印选择界面。
            known_signet = KNOWN_SIGNETS
            if self.state.floor == 1 and not self.state.acquired and not any(
                    marker in self.text for marker in known_signet):
                self.phase("等待初始刻印", "第一层尚未出现已获刻印，继续战斗等待专属选择")
                # “增益列表”是暂停菜单的子页，先点左上角返回关闭菜单；
                # 只有在“战况报告”页才存在“继续战斗”按钮。
                if self.find("^增益列表$", [220, 0, 260, 90]):
                    self.click_text("返回$", [0, 0, 210, 90], .6)
                elif not self.click_text("^继续战斗$", [800, 570, 480, 150], .6):
                    self.click_text("^战况报告$", [0, 170, 210, 110])
                return
            signature = normalize("".join(i["text"] for i in self.items if i["box"][0] > 220))
            if signature != self.build_signature and self.build_scrolls < 6:
                self.build_signature = signature
                self.swipe(1100, 604, 1100, 290, 300); self.build_scrolls += 1; return
            if self.state.has(required):
                self.state.build_verified = True
                self.phase("本局检查通过", f"{self.state.role} / {required}")
            else:
                raise RunHalt(f'未在已获刻印中确认{required}，不能执行{required}专属循环')
        if self.click_text("^继续战斗$", [800, 570, 480, 150], .6): return
        self.click_text("^战况报告$", [0, 170, 210, 110])

    def select_signet(self):
        self.battle_finished = True
        self.phase("选择刻印")
        rows = choice_rows(self.items)
        if not rows:
            # 一张卡都没识别到：静默返回会让阶段循环原地空转、卡死在刻印页。
            if self.choice_empty >= 3:
                raise RunHalt("刻印选择页识别不到任何卡片，已停止并保存现场")
            self.choice_empty += 1
            self.phase("刻印页无候选", f"识别不到卡片，重置后重试（{self.choice_empty}/3）")
            self.click_text("重置刻印", [600, 630, 420, 90], .8)
            return
        self.choice_empty = 0
        family_match = re.search(r"[「【\[]?(真我|黄金|鏖灭|空梦|螺旋|天慧|浮生|戒律|无限|旭光|繁星|刹那|救世)[」】\]]?的刻印", self.text)
        family = family_match.group(1) if family_match else ""
        signature = "|".join(normalize(r["text"]) for r in rows)
        if signature == self.choice_signature and time.monotonic()-self.choice_at < 2: return
        exclusive = family == "真我" or any("祝福" in r["text"] for r in rows)
        required = self.required_signet()
        if exclusive and not self.state.has(required) and not any(required in r["text"] for r in rows):
            if self.exclusive_refresh >= 8: raise RunHalt(f"初始专属刷新 8 次仍未找到{required}")
            if self.click_text("重置刻印", [600, 630, 420, 90], .8):
                self.exclusive_refresh += 1
                self.phase("初始专属", f"寻找{required}，刷新 {self.exclusive_refresh}/8")
            return
        allowed_rows = [row for row in rows if not signet_disabled(row["text"], self.state, family)]
        if not allowed_rows:
            if self.exclusive_refresh < 8 and self.click_text("重置刻印", [600, 630, 420, 90], .8):
                self.exclusive_refresh += 1
                self.phase("刷新禁用刻印", "当前仅有禁用刻印，尝试重置")
                return
            raise RunHalt("当前奖励只有禁用刻印可选，已停止并保留现场")
        scored = [{**row, "score": score_signet(row["text"], self.state)} for row in allowed_rows]
        chosen = max(scored, key=lambda row: row["score"])
        with (self.output / "decisions.jsonl").open("a", encoding="utf-8") as log:
            log.write(json.dumps({"at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "floor": self.state.floor, "family": family, "candidates": scored,
                "chosen": chosen["text"]}, ensure_ascii=False) + "\n")
        self.phase("选择刻印", normalize(chosen["text"])[:64])
        self.save(True)
        self.click(*chosen["point"], delay=.3)
        self.read()
        if not self.click(1147, 670, .6): return
        self.pending_signet = (chosen["text"], family, signature)
        self.choice_signature, self.choice_at = signature, time.monotonic()
        self.progress_at = time.monotonic()

    def commit_signet(self):
        if not self.pending_signet: return
        text, family, signature = self.pending_signet
        # 选择后必须用最新画面判断是否已离开刻印页：这里若沿用点击前的 items，
        # 会一直认为"页面没变"而永久挂在 pending 上，后续画面切走也没人推进。
        self.read()
        current = "|".join(normalize(r["text"]) for r in choice_rows(self.items))
        if signature == current and "选择刻印" in self.text: return
        self.state.record(text, family)
        if self.required_signet() in text: self.state.build_verified = True
        self.pending_signet = None
        self.phase("已获得刻印", normalize(text)[:48])

    def gate_panel(self):
        """传送锚点面板（减负/挑战奖励层）：按卡分桶读门名，集齐三张或等待超时后点优先级最高那张卡的中心。"""
        order = gate_order(self.state)
        cards = {}
        for item in self.items:
            x, y, w, h = item["box"]
            if y > 560: continue
            name = next((n for n in order if n in normalize(item["text"])), None)
            if not name: continue
            for index, (left, right) in enumerate(GATE_PANEL_BANDS):
                if left <= x + w/2 < right and index not in cards: cards[index] = name
        now = time.monotonic()
        if not self.panel_since: self.panel_since = now
        if len(cards) < 3 and now - self.panel_since < GATE_PANEL_WAIT_S:
            self.phase("选择下一层", f"等待三张卡识别（已认到 {len(cards)} 张）")
            return True
        if not cards: return False
        index = min(cards, key=lambda i: order.index(cards[i]))
        self.phase("选择下一层", f"点第 {index+1} 张卡：{cards[index]}")
        self.click(*GATE_PANEL_POINTS[index], .8)
        return True

    def gate_choice(self):
        self.phase("选择下一层")
        options = []
        for item in self.items:
            if 160 <= item["box"][1] <= 300:
                for name in gate_order(self.state):
                    if name in normalize(item["text"]): options.append((gate_order(self.state).index(name), item))
        if options:
            _, item = min(options, key=lambda o:o[0]); x,y,w,h=item["box"]
            self.click(x+w/2,y+h/2,.8)
        elif any(name in self.text for name in self.state.disabled_families):
            raise RunHalt("下一层选择中没有可用的非禁用刻印，已保留现场")

    def navigate(self):
        if not self.nav_started:self.nav_started=time.monotonic()
        # 贴门时模型可能漏检：优先读游戏提供的门名和交互提示。
        prompt, at_name = self.gate_prompt()
        # 门名由左侧面板确认、但「前往」小卡片 OCR 读不到时（不同场景对比度不同），
        # 连续几帧都读不到就按门前标准位置补点，避免站在门口干等。
        missing = bool(at_name) and at_name not in self.state.disabled_families and not prompt
        self.prompt_missing = self.prompt_missing + 1 if missing else 0
        blind = self.prompt_missing >= GATE_BLIND_READS
        if self.state.target in self.state.disabled_families:
            self.target = None
            self.state.target = ""
        if time.monotonic()-self.nav_started>180:
            if self.enter_attempts and (prompt or blind) and at_name and not self.gate_pause_used:
                self.start_gate_pause_recovery()
                return
            raise RunHalt("本层找门超过 180 秒，现场已保存")
        left = "".join(normalize(i["text"]) for i in self.items if i["box"][0] < 370 and 210 < i["box"][1] < 480)
        # 只要画面里确实出现「前往」，就立刻交互：此时门一定在交互范围内，
        # 继续靠近/转视角只会错过窗口（门名读不到时也照点，交互提示本身就是授权）。
        prompt_only = bool(prompt) and not at_name
        if (prompt or blind) and at_name not in self.state.disabled_families and (
                at_name or prompt_only
                or (self.final_clear and re.search('下一层.*(作战|挑战)', left))
                or (self.state.target == "首领" and re.search("首领|挑战|最后", left))):
            actual = at_name or self.state.target or "首领"
            if self.state.target and actual != self.state.target:
                self.phase("门前复核", f"模型预判 {self.state.target}，游戏文字确认 {actual}，采用已确认门")
            limit = GATE_AFTER_PAUSE_ATTEMPTS if self.gate_pause_used else GATE_CLICK_MAX_ATTEMPTS
            if self.enter_attempts >= limit:
                if not self.gate_pause_used:
                    self.start_gate_pause_recovery()
                    return
                raise RunHalt("暂停并继续后又尝试前往 3 次仍未切层，现场已保存")
            self.enter_attempts += 1
            # “前往”文字在长条交互框左侧；优先点框内中部，失败后
            # 再用当前帧的文字位置和另一处框内位置，不能复用旧坐标。
            desktop = DesktopInput.available(self.context)
            offsets = GATE_CLICK_OFFSETS_PC if desktop else GATE_CLICK_OFFSETS
            offset = offsets[(self.enter_attempts - 1) % len(offsets)]
            if prompt:
                x, y, w, h = prompt["box"]
                point = (min(1040, x + w / 2 + offset), y + h / 2)
                note = ""
            else:
                blind = GATE_BLIND_PROMPT_PC if desktop else GATE_BLIND_PROMPT
                point = (min(1040, blind[0] + offset), blind[1])
                note = "（未读到前往提示，按门前位置补点）"
            self.phase("点击前往", f"{actual}，第 {self.enter_attempts} 次{note}，坐标 {int(point[0])},{int(point[1])}")
            self.save(True)
            self.enter_pending = self.state.floor
            self.state.target = actual
            self.enter_at = time.monotonic()
            self.enter_failure_reads = 0
            if self.final_clear:self.final_gate_clicked=True
            self.click(*point, 1.2)
            self.progress_at = time.monotonic()
            return
        detected_gates = self.detect_gates()
        gates = [gate for gate in detected_gates
                 if GATE_NAMES.get(gate.get('cls_index')) not in self.state.disabled_families]
        merchant=next((r for r in gates if r.get('cls_index')==13 and r.get('score',0)>=.55),None)
        if merchant and self.state.shop_enabled and not self.shop_done and self.find('商店',[690,250,300,95]):
            self.phase("打开商店", "查看本局银币可购买的刻印")
            self.click(830,286,.8)
            return
        if self.shop_done:gates=[r for r in gates if r.get('cls_index') not in (10,13)]
        visible = [r for r in gates if r.get("cls_index") in GATE_NAMES and r.get("score",0)>=.55]
        if self.target:
            selected = [r for r in visible if GATE_NAMES[r["cls_index"]] == self.state.target]
            gate = min(selected, key=lambda r:abs(r["box"][0]+r["box"][2]/2-self.target["box"][0]-self.target["box"][2]/2)) if selected else None
        else:
            gate = min(visible,key=lambda g:abs(g['box'][0]+g['box'][2]/2-640)) if self.final_clear and visible else choose_gate(gates, self.state)
        if gate:
            self.lost_frames = 0
            self.target = gate
            self.state.target = GATE_NAMES[gate["cls_index"]]
            box = gate["box"]; cx=box[0]+box[2]/2
            if abs(cx-640) > 100:
                self.phase("对准传送门", self.state.target)
                delta=max(-90,min(90,int((cx-640)*.25)))
                self.swipe(760,301,760+delta,301,200)
                return
            self.phase("靠近传送门", self.state.target + f"，第 {self.nav_steps+1} 步")
            self.motion.walk(self.context, max(-65,min(65,int((cx-640)*.35))), .25 if box[2]>=100 else .6)
            self.nav_steps += 1
            self.stop_event.wait(.65)
        else:
            self.lost_frames += 1
            if self.target and self.target["box"][2] >= 100 and self.lost_frames == 1:
                # 已贴近的门突然消失，可能越过交互范围；禁止继续前冲。
                self.phase("复核近门位置", "近门目标消失，短步后退后重新观察")
                self.motion.walk(self.context, 0, .25, dy=76)
                return
            frames = [r for r in gates if r.get("cls_index") in (8,24) and r.get("score",0)>=.3]
            blocked_visible = any(GATE_NAMES.get(g.get('cls_index')) in self.state.disabled_families
                                  and g.get('score', 0) >= .55 for g in detected_gates)
            # 商店遮挡：门就在商店后面，纯转视角永远看不到门框。
            # 安卓端用 pipeline 的「看到商店→前进」「在商店旁→直走」两个兜底；
            # 这里对齐它：只要视野里还有商店就继续往前挪，商店离开视野即停，
            # 不会像原来固定 2 步那样走不够、也不会按着不动。
            if self.shop_done and not visible and self.shop_steps < SHOP_PASS_STEPS:
                shops = [r for r in detected_gates
                         if r.get("cls_index") in (10, 13) and r.get("score", 0) >= .3]
                if shops:
                    self.shop_steps += 1
                    self.phase("绕开商店", f"商店挡住门框，向前通过（{self.shop_steps}/{SHOP_PASS_STEPS}）")
                    self.motion.walk(self.context, 0, .5, dy=-76)
                    self.nav_steps += 1
                    return
            if not frames and not visible and not blocked_visible:
                frames=red_portals(self.frame) or dormant_anchors(self.frame)
            if frames and not visible:
                self.frame_target=frames;self.frame_lost=0
                if self.nav_steps and self.nav_steps % 4 == 0:self.save(True)
                cx=sum(r["box"][0]+r["box"][2]/2 for r in frames)/len(frames)
                self.phase("靠近门框", "展开后再识别刻印体系")
                if abs(cx-640)>100:
                    self.swipe(760,301,760+max(-90,min(90,int((cx-640)*.25))),301,200)
                    return
                self.motion.walk(self.context,max(-65,min(65,int((cx-640)*.35))))
                self.nav_steps+=1
            else:
                if self.target and self.target["box"][2] < 100 and self.lost_frames <= 2:
                    self.phase("保持接近方向", "转向后目标被角色遮挡，先向前短走")
                    self.motion.walk(self.context,0,.5)
                    self.stop_event.wait(.65)
                    self.nav_steps+=1
                    return
                if self.frame_target and self.frame_lost < 3:
                    # 转向后角色可能遮住远处门；沿刚确认的方向短走，避免立即转走。
                    self.phase("保持接近方向", "门暂时被角色遮挡，短步重看")
                    self.motion.walk(self.context,0,.6)
                    self.frame_lost+=1;self.nav_steps+=1
                    return
                self.frame_target=None
                if (self.target and self.target["box"][2] >= 100 and self.lost_frames >= 3) or (self.turns and self.turns % 8 == 0):
                    if self.nav_recoveries >= 4: raise RunHalt("贴门恢复 4 次仍未读到门名，现场已保存")
                    # 小门框被岩柱遮住时，旧目标也必须释放；单纯转动视角无法脱离碰撞。
                    self.phase("恢复走门", "清除丢失目标，后退横移离开遮挡后重新识别")
                    self.motion.walk(self.context, 0, .7, dy=76)
                    self.motion.walk(self.context, -76 if self.nav_recoveries % 2 == 0 else 76, .8, dy=0)
                    self.nav_recoveries += 1
                    self.target = None; self.state.target=""; self.lost_frames=0
                    self.frame_target=None;self.frame_lost=0
                    self.turns += 1
                    return
                self.phase("转动视角找门", f"第 {self.turns+1} 次")
                self.save(True)
                # 桌面端视角拖动换算比模拟器小，单次多转一点、允许多转几轮，
                # 否则容易在门刚好卡在视野边缘时一直找不到。
                self.swipe(900, 301, 700, 301, 320)
                self.turns += 1
                if self.turns >= 40:
                    raise RunHalt("40 次视角搜索及位置恢复后仍未找到可确认的门，现场已保存")
        if self.nav_steps >= 40: raise RunHalt("靠近门 40 步仍未读到交互提示，现场已保存")

    def gate_prompt(self):
        # PC 的「前往」在右侧更靠下（实测 x≈1105..1250、y≈428..467），
        # 模拟器在 x 650..1050、y 190..410；两者都覆盖，避免 PC 永远读不到提示。
        prompt = self.find("前往", [620, 150, 640, 360])
        left = "".join(normalize(i["text"]) for i in self.items
                       if i["box"][0] < 370 and 210 < i["box"][1] < 480)
        # 禁用的门也要识别出身份，才能拒绝其交互，不能把它当未知门。
        family = next((name for name in dict.fromkeys(GATE_NAMES.values()) if name in left), None)
        if not family and re.search("下一层.*(作战|挑战)", left) and self.state.target == "首领":
            family = "首领"
        return prompt, family

    def wait_gate_entry(self):
        """门前持续不变才重试；加载或楼层 OCR 暂缺时禁止移动。"""
        if self.enter_pending is None:
            return False
        elapsed = time.monotonic() - self.enter_at
        if elapsed < GATE_CLICK_CHECK_S:
            return True
        observed = read_floor(self.items)
        prompt, family = self.gate_prompt()
        same_gate = (observed and observed[0] == self.enter_pending
                     and family == self.state.target
                     and (prompt or self.prompt_missing >= GATE_BLIND_READS))
        self.enter_failure_reads = self.enter_failure_reads + 1 if same_gate else 0
        if self.enter_failure_reads >= 2:
            self.enter_pending = None
            self.enter_failure_reads = 0
            self.phase("进门未生效", "同层门名和前往仍在，重新识别交互位置")
            if self.enter_attempts and self.enter_attempts % len(GATE_CLICK_OFFSETS) == 0:
                self.phase("调整门前位置", "连续点击未切层，短步后退后重新靠近")
                self.motion.walk(self.context, 0, .25, dy=76)
            # 调整后必须重新截图，不能在同一帧立即点击。
            return True
        # 点击后一直没切层、也没稳定读到门前信息：多半是擦过传送门（OCR 短暂看到「前往」），
        # 先反向走一小步并转视角，再重新靠近最近的门；次数有上限，用尽后回到原有超时逻辑。
        if (not same_gate and elapsed >= GATE_ENTER_RETRY_S
                and self.enter_recovery < GATE_ENTER_RECOVERIES):
            self.enter_recovery += 1
            self.enter_pending = None
            self.enter_failure_reads = 0
            self.target = None
            self.state.target = ""
            self.prompt_missing = 0
            self.nav_started = 0
            self.nav_steps = self.turns = 0
            self.phase("门前重试", f"点击前往未生效，后退并转视角重新靠近（第 {self.enter_recovery}/{GATE_ENTER_RECOVERIES} 次）")
            self.motion.walk(self.context, 0, .30, dy=96)
            self.swipe(760, 301, 640, 301, 260)
            return True
        if elapsed < GATE_LOAD_WAIT_S:
            return True
        if observed and observed[0] == self.enter_pending:
            self.enter_pending = None
            self.enter_failure_reads = 0
            self.target = None
            self.phase("重新确认门前位置", "等待切层超时，重新识别门和交互提示")
            return True
        raise RunHalt("进门后 30 秒仍无法确认楼层，已停止并保存现场")

    def start_gate_pause_recovery(self):
        """同层只恢复一次，不在加载画面里尝试打开暂停。"""
        if self.stopped():
            return
        self.gate_pause_used = True
        self.gate_recovery_phase = "pause"
        self.gate_recovery_at = time.monotonic()
        self.enter_pending = None
        self.enter_failure_reads = 0
        self.phase("暂停恢复门前交互", "多次前往无效，暂停后继续战斗再尝试")
        self.click(43, 36, .5)

    def recover_gate_pause(self):
        if self.gate_recovery_phase is None:
            return False
        if self.stopped():
            return True
        paused = all(word in self.text for word in ("战况报告", "状态列表", "往世乐土"))
        elapsed = time.monotonic() - self.gate_recovery_at
        if self.gate_recovery_phase == "pause":
            if paused and self.click_text("^继续战斗$", [800, 570, 480, 150], .6):
                self.gate_recovery_phase = "resume"
                self.gate_recovery_at = time.monotonic()
                self.phase("继续战斗恢复交互", "等待返回关卡，重新识别前往")
                return True
            if elapsed >= GATE_PAUSE_WAIT_S:
                raise RunHalt("门前恢复未能打开暂停或识别继续战斗，现场已保存")
            return True
        if not paused and self.arena():
            self.gate_recovery_phase = None
            self.enter_attempts = self.enter_failure_reads = 0
            self.nav_started = self.progress_at = time.monotonic()
            self.phase("暂停恢复完成", "重新识别门，最多再尝试前往 3 次")
            # 返回关卡这一帧只确认恢复，下次截图才允许点击。
            return True
        if elapsed >= GATE_PAUSE_WAIT_S:
            raise RunHalt("门前恢复点击继续战斗后未返回关卡，现场已保存")
        return True

    def frontend(self):
        text = self.text
        if '签到奖励' in text and '每日签到' in text:
            self.phase('关闭登录签到', '领取已出现的签到奖励')
            return self.click_text('^领取$', [600,610,350,110], .8)
        if "跳过剧情" in text and "确认" in text:
            self.phase("跳过对话"); return self.click_text("^确认$", [650,420,380,160])
        # 关内 HUD（有血量/层数/得分）不可能是对话：即使模板误命中也不点跳过，
        # 否则会在跑图或领奖画面里反复敲空格，把画面顶住不动。
        hud = ("抵达层数" in text or self.find(r"^\d+/\d+$", [0, 600, 400, 120]))
        if self.find("跳过", [1000,0,280,100]) and "历史" in text and not hud:
            # 全屏 OCR 有时把「自动」和「跳过」合成同一行，不能点合并框中心。
            self.phase("跳过对话"); return self.click(1200,40)
        if "锈蚀之徽" in text and "上限" in text:
            self.phase("关闭奖励提示")
            return self.click_text("确定|确认", [300,280,700,300])
        if "重新挑战本层" in text and "直接结算" in text:
            if self.retry_floor_attempts >= 2:
                raise RunHalt("同一首领层连续失败 2 次，已停止并保留现场")
            self.retry_floor_attempts += 1
            self.phase("重试失败楼层", f"第 {self.retry_floor_attempts} 次")
            if self.click_text("^重新挑战本层$", [700, 600, 300, 110], 1):
                return True
            # OCR 合并按钮时使用 1280×720 逻辑坐标的按钮中心。
            return self.click(883, 664, 1)
        # 有继续入口时保留本局进度，从当前楼层接续。
        if "直接结算" in text and "继续挑战" in text:
            # 失败停在首领层时，继续挑战才能保留本局刻印并重试；
            # 直接结算会回大厅，但再次打开深层序列仍会回到这张进度页。
            self.phase("恢复残留挑战", "继续上一轮首领层")
            if self.click_text("^继续挑战$", [1000, 560, 280, 150], 1):
                return True
            # OCR 将两个按钮合并时使用继续挑战按钮中心点兜底。
            # 画面展示为 1600×900，MAA 输入坐标是 1280×720。
            return self.click(988, 532, 1)
        if "当前挑战进度" in text and self.find("^直接结算$", [1000, 560, 280, 150]):
            self.phase("清理残留挑战", "退出无可继续的旧进度")
            return self.click_text("^直接结算$", [1000, 560, 280, 150], 1) or self.click(710, 532, 1)
        # 退出请求之后只处理收尾提示，绝不能再次经过新一局的入口。
        if self.settlement_requested:
            return False
        if "出战位" in text and "支援位" in text and "开始战斗" in text:
            self.phase("出战准备", "沿用当前角色、助战和追忆之证")
            self.state = RunState(**{key: getattr(self.state, key) for key in (
                "role", "variant", "exclusive_priority", "buff_priority", "gate_priority",
                "disabled_families", "shop_enabled")})
            self.fresh_run = True
            self.final_clear=self.final_exit=self.final_gate_clicked=self.settlement_requested=False
            self.settlement_result_seen=False
            self.checkpoint.unlink(missing_ok=True)
            self.progress_at = time.monotonic()
            return self.click_text("^开始战斗$", [930,590,350,130],1)
        if "首领预览" in text and "开始战斗" in text:
            self.phase("深层序列", "沿用游戏当前难度")
            return self.click_text("^开始战斗$", [990,480,290,150],1)
        if "命定的歧路" in text and "深层序列" in text:
            self.phase("进入深层序列")
            return self.click_text("深层序列", [1000,0,280,180],1)
        if "往世乐土" in text and ("记忆战场" in text or "万象虚境" in text):
            self.phase("进入往世乐土")
            return self.click_text("^往世乐土$", None,1)
        if self.find("^挑战$",[500,20,400,140]) and "出击" in text:
            self.phase("打开挑战入口")
            return self.click_text("^挑战$",[500,20,400,140],.8)
        if "女武神" in text and "补给" in text and "出击" in text:
            self.phase("从舰桥出发")
            return self.click_text("^出击$",[1050,230,230,260],1)
        return False

    def shop(self):
        if not self.state.shop_enabled:
            self.shop_done = True
            self.shop_exit_steps = 2
            self.phase("离开商店", "按任务设置跳过购买")
            self.click_text('返回$',[0,0,210,90],.8)
            return
        self.phase("商店补强", "优先购买元素穿透、全伤、武器相关刻印")
        self.progress_at=time.monotonic()
        coin_item=self.find(r'^\d+$',[1120,0,160,75])
        coins=int(normalize(coin_item['text'])) if coin_item else 0
        if self.shop_pending:
            title,before=self.shop_pending
            if coins<before:
                self.state.record(title)
                self.phase("商店购买成功",title)
            self.shop_seen.add(title)
            self.shop_pending=None
        candidates=[]
        for row in shop_rows(self.items):
            title=row['title']
            if row['price']<=coins and title not in self.shop_seen and not self.state.has(title):
                score=score_signet(row['text'],self.state)
                if score>=180:candidates.append((score,title,row['y']))
        if candidates and len(self.shop_seen)<8:
            _,title,y=max(candidates,key=lambda c:c[0])
            self.click(800,y,.3);self.read()
            if self.click_text('^购买刻印$',[1000,630,280,90],.8):self.shop_pending=(title,coins)
            return
        if self.shop_scrolls<3 and coins>=200:
            self.swipe(1100,592,1100,188,350);self.shop_scrolls+=1
            return
        self.shop_done=True;self.shop_exit_steps=2
        self.target=None;self.state.target='';self.turns=self.nav_steps=0;self.nav_started=0
        self.phase("离开商店", "购买结束，绕开摊位前往出口")
        self.click_text('返回$',[0,0,210,90],.8)

    def step(self):
        self.read()
        if "请选择下一层" not in self.text: self.panel_since = 0
        self.update_floor()
        if self.recover_gate_pause(): return
        if signet_detail_open(self.items):
            self.detail_attempts += 1
            if self.detail_attempts > 3:
                raise RunHalt("刻印术语弹层关闭 3 次未成功，已保存现场")
            self.phase("关闭刻印详情", "检测到详情弹层，返回当前流程")
            controller = self.context.tasker.controller
            if not controller.post_click_key(4).wait().succeeded:
                self.click_text("^[Xx×]$", [1180, 0, 100, 85], .5)
            self.stop_event.wait(.5)
            return
        self.detail_attempts = 0
        self.commit_signet()
        # 额外刻印机会结束后可能马上播放剧情提示。提示正文里会带有
        # “选择刻印”，如果先走刻印分支会因没有选项卡片而原地空转。
        # 只要右上角同时出现“跳过”和“历史”，先推进剧情提示。
        if self.find("跳过", [1000, 0, 280, 100]) and "历史" in self.text:
            self.frontend()
            return
        if "跳过剧情" in self.text and "确认" in self.text:
            self.frontend()
            return
        if '点击空白处关闭界面' in self.text:
            if self.settlement_requested and '挑战成功' in self.text and self.find(r'^18000$', [1000, 180, 280, 150]):
                self.settlement_result_seen = True
                self.checkpoint.write_text(json.dumps({'requested_at':time.time(), 'state':self.state.to_dict(), 'result_seen':True},ensure_ascii=False),encoding='utf-8')
                self.phase('确认挑战成功', '已核对成绩页：18000 分')
            else:
                if self.settlement_requested and not self.settlement_result_seen and self.settlement_animation_waits < 3:
                    self.settlement_animation_waits += 1
                    self.phase('等待成绩动画', '等待完整成绩文字出现再关闭')
                    self.stop_event.wait(1.2)
                    return
                self.phase('关闭奖励或成绩提示')
            self.click(640,650,.8)
            self.progress_at=time.monotonic()
            return
        # 在用户指定的额外英桀房间恢复时，也执行「进入后直接退出」。
        score=self.find(r'得分\d+',[0,60,250,100])
        if self.state.floor==18 and score and int(re.sub(r'\D','',normalize(score['text'])))>=18000:
            self.final_clear=self.final_exit=True
        # 只有同一楼层的门前提示持续存在才判定点击无效。
        # 黑屏、加载和新楼层待复核期间继续等待，禁止追加移动或战斗。
        if self.wait_gate_entry(): return
        # 失败成绩页没有楼层 HUD，先处理「重新挑战本层」，不要被通用
        # 失败模板当成新局残留页而点击返回。
        if self.state.floor == 0 and "重新挑战本层" in self.text and "直接结算" in self.text:
            if self.frontend():
                self.progress_at = time.monotonic()
            return
        # 首领开场提示「超时会导致战斗失败」不是失败结算。
        failed=self.find("^(战斗失败|挑战失败)$") or (not self.arena() and self.hit("往世乐土-战斗-战斗失败"))
        if failed and self.state.floor==0 and not self.final_exit:
            self.phase('清理残留失败页','尚未进入本局，返回后重新开始')
            self.click(640,650,1)
            return
        if failed and self.settlement_requested:
            self.phase('退出英桀挑战', '已按指定流程退出，继续到本局成绩')
            self.click(640,650,1);return
        if failed:
            raise RunHalt("本层战斗失败，已停止并保留现场；未计作通关")
        if "选择刻印" in self.text and ("刻印" in self.text or "核心" in self.text):
            self.select_signet(); return
        if "请选择下一层" in self.text and "传送锚点" in self.text:
            if not self.gate_panel(): self.gate_choice()
            return
        if "战况报告" in self.text and "状态列表" in self.text and "往世乐土" in self.text:
            self.sync_pause(); return
        if self.settlement_requested and self.final_clear and '命定的歧路' in self.text and '深层序列' in self.text:
            self.phase('结算完成','深层序列 17 层完成，任选英桀门后退出，已返回乐土大厅')
            self.state.result='通关';self.checkpoint.unlink(missing_ok=True)
            raise RunHalt('已完成深层序列并按指定方式退出结算')
        if self.frontend():
            self.progress_at = time.monotonic(); return
        if self.final_exit and '是否放弃并结算' in self.text and self.find('^放弃$',[300,430,340,130]):
            self.phase("确认结算")
            self.settlement_requested=True
            self.checkpoint.write_text(json.dumps({'requested_at':time.time(),'state':self.state.to_dict()},ensure_ascii=False),encoding='utf-8')
            self.click_text('^放弃$',[300,430,340,130],1)
            return
        if self.find('^购买刻印$',[0,60,220,90]) and '升级刻印' in self.text:
            self.shop();return
        if ("挑战结束" in self.text or self.hit("往世乐土-战斗-战绩结算") or self.hit("往世乐土-成绩结算")) and not self.arena():
            self.phase("结算")
            self.save(True)
            if self.final_clear:
                self.click_text("确定|确认|返回|完成", [280,540,760,180])
                return
            raise RunHalt("挑战已结束，但未确认完成全部楼层；保留结算现场")
        if self.state.floor >= self.state.total and self.hit("往世乐土-打完了"):
            self.phase("最终结算")
            result=self.hit("往世乐土-打完了");x,y,w,h=result.box
            self.click(x+w/2,y+h/2,1)
            return
        if self.arena():
            self.progress_at = time.monotonic()
            self.wait_stuck = 0
            if (self.state.floor == 1 and not self.state.build_verified
                    and not self.state.acquired
                    and time.monotonic() - self.floor_since < INITIAL_SIGNET_GRACE_S
                    and not self.final_exit):
                self.phase("等待初始刻印", "等待出生动画和初始专属选择")
                return
            if (self.state.floor == 0 or (self.fresh_run and self.state.floor == 1
                    and not self.state.build_verified)) and not self.final_exit:
                self.phase('等待初始刻印','等待出生动画与初始专属选择')
                if time.monotonic()-self.floor_since>45:raise RunHalt('出生后 45 秒仍未出现初始刻印，现场已保存')
                return
            if self.final_exit:
                self.phase('进入英桀房间后退出');self.click(43,36);return
            if not self.state.role_verified or not self.state.build_verified:
                self.phase("检查本局", f"打开暂停菜单核对角色与{self.required_signet()}")
                self.click(43,36); return
            post_battle = self.hit("角色战斗-战后禁用") or self.hit("乐土自动-刷新门")
            self.active_hud_frames=0 if post_battle else self.active_hud_frames+1
            if self.active_hud_frames >= 3:
                self.battle_finished=False
            if self.battle_finished or post_battle:
                if not self.peace_since: self.peace_since=time.monotonic()
                if time.monotonic()-self.peace_since<1.2:
                    self.phase("等待领奖", "等战后界面稳定"); return
                self.battle_finished = True
                score=self.find(r'得分\d+',[0,60,250,100])
                if self.state.floor>=self.state.total and score and int(re.sub(r'\D','',normalize(score['text'])))>=18000:
                    if not self.final_clear:
                        self.final_clear=True
                        self.phase("深层序列首领已击败", "任选一个英桀门进入后退出结算")
                if self.shop_exit_steps:
                    # 刚退出商店时先离开摊位再寻路：关内固定后退一步，
                    # 避免站在商店交互范围内直接进入找门流程。
                    self.motion.walk(self.context, 0, .25, dy=76)
                    self.shop_exit_steps -= 1
                    return
                self.navigate(); return
            self.peace_since=0
            self.target = None; self.state.target=""; self.turns = self.nav_steps = 0
            if time.monotonic()-self.floor_since > 360:
                raise RunHalt("本层战斗超过 6 分钟，可能输出不足或未能接敌")
            self.phase("战斗", f"{self.state.role}·{self.required_signet()}：按角色出招表")
            if time.monotonic() - getattr(self, 'combat_capture_at', 0) >= 8:
                self.save(True)
                self.combat_capture_at = time.monotonic()
            self.combat.run(self.context, self.combat_args)
            return
        # 关卡 HUD 存在但不在战斗（减负层待命、刚选完刻印）：
        # 先做一次角色/刻印校验（暂停菜单），确认无误再去寻路，避免带错配置跑图。
        if "抵达层数" in self.text:
            self.progress_at = time.monotonic()
            if not self.state.role_verified or not self.state.build_verified:
                self.phase("检查本局", f"选完刻印先核对角色与{self.required_signet()}")
                self.click(43, 36)
                return
            self.navigate()
            return
        if time.monotonic()-self.progress_at > 35:
            # 等待画面长时间不动：先按一次 Esc 退出可能存在的残留弹层，再重试；
            # 连续两次仍无进展才停止，避免减负层/过场被误判为未知画面。
            if self.wait_stuck < 2:
                self.wait_stuck += 1
                self.progress_at = time.monotonic()
                self.phase("等待画面", f"长时间无变化，按 Esc 尝试推进（{self.wait_stuck}/2）")
                self.context.tasker.controller.post_click_key(4).wait()
                self.stop_event.wait(.8)
                return
            raise RunHalt("当前画面连续 35 秒未能识别，已停止并保存截图")
        self.phase("等待画面", "加载、对话或界面切换")

    def run(self, context, argv):
        self.context = context
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
        allowed = ("role", "variant", "exclusive_priority", "buff_priority", "gate_priority", "disabled_families", "shop_enabled")
        settings = {key: params[key] for key in allowed if key in params}
        self.state = RunState(**settings)
        profile = CHARACTER_PROFILES.get(self.state.role, {}).get("variants", {}).get(self.state.variant)
        if not profile:
            # 角色/流派未适配时给出可读原因，避免后续按索引取档案时抛 KeyError。
            self.state.result = "需要处理"
            self.state.reason = f"角色或流派尚未适配：{self.state.role} / {self.state.variant}"
            self.report(self.state.reason)
            return False
        self.fresh_run = False
        self.detail_attempts = 0
        self.floor_candidate=None;self.floor_candidate_reads=0;self.active_hud_frames=0
        self.output=self.root/"development-notes"/"runs"/time.strftime("%Y%m%d-%H%M%S")
        self.output.mkdir(parents=True,exist_ok=True)
        self.progress_at=self.floor_since=time.monotonic()
        self.target=self.enter_pending=self.pending_signet=None
        self.frame_target=None;self.frame_lost=0
        self.shop_done=False
        self.shop_seen=set();self.shop_pending=None;self.shop_scrolls=self.shop_exit_steps=0
        self.shop_steps=0
        self.final_clear=False
        self.final_gate_clicked=self.final_exit=False
        self.settlement_requested=False
        self.settlement_result_seen=False
        self.settlement_animation_waits=0
        self.retry_floor_attempts=0
        self.checkpoint=self.root/('development-notes/pending-settlement-assistant.json' if getattr(self, 'stage_only', False) else 'development-notes/pending-settlement.json')
        if self.checkpoint.exists():
            checkpoint=json.loads(self.checkpoint.read_text(encoding='utf-8'))
            if time.time()-checkpoint.get('requested_at',0)<600:
                self.state=RunState(**checkpoint['state'])
                for key, value in settings.items(): setattr(self.state, key, value)
                self.state.result='运行中';self.state.reason=''
                self.final_clear=self.final_exit=self.settlement_requested=True
                self.settlement_result_seen=checkpoint.get('result_seen',False)
        # checkpoint 恢复会重建 state 对象，动作层必须跟着指向新对象；
        # 否则面板战斗仍按本次选项的角色出招，与恢复后的记录不一致。
        self.motion.state = self.state
        self.choice_signature="";self.choice_at=0;self.choice_empty=0;self.wait_stuck=0;self.enter_at=0;self.build_signature="";self.peace_since=0;self.battle_finished=False;self.nav_started=0
        self.enter_attempts = self.enter_failure_reads = 0
        self.enter_recovery = 0
        self.gate_pause_used = False
        self.gate_recovery_phase = None
        self.gate_recovery_at = 0
        self.panel_since = 0
        self.prompt_missing = 0
        self.nav_steps=self.turns=self.exclusive_refresh=self.build_scrolls=self.lost_frames=self.nav_recoveries=0
        self.combat_args=SimpleNamespace(task_detail=argv.task_detail, custom_action_param=json.dumps({"character":self.state.role,"variant":self.state.variant,"confirmed_signet":self.required_signet()}))
        try:
            while not self.stopped():
                self.step()
                self.stop_event.wait(.15)
            self.state.result="已停止"; self.state.reason="用户停止"
        except RunHalt as exc:
            self.state.reason=str(exc)
            if self.state.result != "通关": self.state.result="需要处理"
            self.report(self.state.reason)
        except Exception as exc:
            traceback.print_exc()
            self.state.result="异常停止";self.state.reason=f"{type(exc).__name__}: {exc}"
            self.report(self.state.reason)
        finally:
            context.tasker.controller.post_touch_up().wait()
            self.save(True)
            self.report(f"{self.state.result}：{self.state.reason}。记录：{self.output.name}")
        return self.state.result == "通关"


class AssistantElysianRun(ElysianRun):
    """原助手和集成验证共用入口，停止状态由框架传递。"""
    def __init__(self):
        super().__init__(threading.Event(), lambda msg: print(msg, flush=True),
                         lambda frame: None, Path(__file__).resolve().parents[3])

    def run(self, context, argv):
        self.stop_event.clear()
        try:
            return super().run(context, argv)
        finally:
            if self.state.result != "通关":
                ElysianPause().run(context, argv)


class ElysianPause(CustomAction):
    def run(self, context, argv):
        try:
            controller=context.tasker.controller
            controller.post_touch_up().wait()
            frame=controller.post_screencap().wait().get()
            if frame is None:return False
            active=context.run_recognition("战斗逻辑-战斗中",frame)
            hud=context.run_recognition("角色战斗-生命HUD",frame)
            if active and active.hit and hud and hud.hit:
                return controller.post_click(43,36).wait().succeeded
            return True
        except Exception: return False
