"""乐土刻印界面的保守选择器；不处理商店、刷新和场景内走门。"""
import re
import time
from maa.custom_action import CustomAction


class ElysianRealmSelection(CustomAction):
    def __init__(self):
        super().__init__()
        self.last_screen = None
        self.last_time = 0
        self.last_pending = None
        self.acquired = []

    @staticmethod
    def score(text):
        # 非星环华裳流。精确核心名称优先，其后按描述排序。
        if ("物理" in text and "元素" not in text) or "冰冻" in text or "火焰" in text:
            return -100
        if "风致" in text or "霆袭" in text:
            return -90
        priorities = [
            ("华裳", 1000), ("尽善", 950), ("粉黛", 900),
            ("黄金的余音", 880), ("鏖灭的余烬", 880),
            ("空梦.*空集.*空我.*空欢", 880),
            ("元素穿透", 180), ("敌人受到的.*提高", 160),
            ("造成的.*全伤害", 150), ("提高.*全伤害", 150), ("造成的.*元素", 145), ("元素伤害", 145),
            ("生命.*上限", 120), ("能量上限", 115),
            ("武器.*伤害", 110), ("每秒回复能量", 60),
        ]
        return max([score for pattern, score in priorities if re.search(pattern, text)] or [10])

    def run(self, context, argv):
        if context.tasker.stopping:
            return False
        frame = context.tasker.controller.post_screencap().wait().get()
        result = context.run_recognition("乐土试验-OCR", frame)
        if not result or not result.hit:
            return True
        items = result.all_results
        texts = [r.text for r in items]
        joined = "|".join(texts)
        is_choice = "请选择英桀的刻印" in joined or ("解锁核心刻印" in joined and "选择刻印" in joined)
        is_gate = "请选择下一层" in joined and "传送锚点" in joined
        if not (is_choice or is_gate):
            return True
        signature = tuple(sorted(r.text for r in items if r.box[1] >= 140))
        if not hasattr(self, "observed") or self.observed != signature:
            self.observed = signature
            return True
        if signature == self.last_screen and time.monotonic() - self.last_time < 5:
            return True
        if self.last_pending and signature != self.last_screen:
            self.acquired.append(self.last_pending)
            self.last_pending = None

        if is_choice:
            candidates = []
            for top, bottom in [(180, 323), (332, 477), (485, 636)]:
                rows = [r for r in items if r.box[0] >= 625 and top <= r.box[1] < bottom]
                text = " ".join(r.text for r in rows)
                if rows:
                    candidates.append((self.score(text), text, (875, (top + bottom) // 2)))
            if not candidates:
                return True
            _, chosen, point = max(candidates, key=lambda row: row[0])
            if not self.click(context, point):
                return False
            time.sleep(0.35)
            frame = context.tasker.controller.post_screencap().wait().get()
            checked = context.run_recognition("乐土试验-OCR", frame)
            if not checked or not any("选择刻印" == r.text for r in checked.all_results):
                return True
            if not self.click(context, (1128, 674)):
                return False
            self.last_pending = chosen
            print(f"SIGNET_SELECT {chosen}", flush=True)
        else:
            # 优先凑齐黄金基础/核心；已有核心后转向鏖灭。
            golden_core = any("黄金的余音" in s for s in self.acquired)
            order = ["真我", "鏖灭", "黄金", "繁星", "空梦", "螺旋", "天慧", "戒律", "浮生", "旭光", "无限", "刹那", "救世"] if golden_core else ["真我", "黄金", "鏖灭", "繁星", "空梦", "螺旋", "天慧", "戒律", "浮生", "旭光", "无限", "刹那", "救世"]
            aliases = {"鏖灭": ("鏖灭", "麈灭", "鏖天")}
            found = [(order.index(name), r) for name in order for r in items if any(alias in r.text for alias in aliases.get(name, (name,))) and 175 <= r.box[1] <= 260]
            if not found:
                return False
            _, chosen = min(found, key=lambda row: row[0])
            x, y, w, h = chosen.box
            if not self.click(context, (x + w // 2, y + h // 2)):
                return False
            print(f"GATE_SELECT {chosen.text}", flush=True)
        self.last_screen = signature
        self.last_time = time.monotonic()
        return True

    @staticmethod
    def click(context, point):
        if context.tasker.stopping:
            return False
        return context.tasker.controller.post_click(*point).wait().succeeded
