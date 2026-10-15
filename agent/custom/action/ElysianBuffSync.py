"""同步战前增益的七个位置：先取消多余项，再补选，最后逐项复核。"""
import json
import threading

from maa.custom_action import CustomAction

from ..utils.Logger import Logger


BUFF_ROWS = (
    "往世乐土-增益选择-上半-换怪",
    "往世乐土-增益选择-上半-第二条",
    "往世乐土-增益选择-上半-第三条",
    "往世乐土-增益选择-下半-第四条",
    "往世乐土-增益选择-下半-第五条",
    "往世乐土-增益选择-下半-第六条",
    "往世乐土-增益选择-下半-第七条",
)

BUFF_COSTS = (0, 5, 5, 10, 10, 15, 15)


def rows_match(rows, costs):
    return ([row[0] for row in rows] == list(costs)
            and all(45 <= following[1] - current[1] <= 90
                    for current, following in zip(rows, rows[1:])))


def read_buff_targets(context):
    targets = []
    for row in BUFF_ROWS:
        node = context.get_node_data(row + "-实际选择-已选中") or {}
        recognition = node.get("recognition", {})
        kind = recognition.get("type") if isinstance(recognition, dict) else recognition
        # 原选项的“否”用 DirectHit 跳过该条；只读取配置，不复用其识别。
        targets.append(kind != "DirectHit")
    return targets


class ElysianBuffSync(CustomAction):
    def stopped(self):
        return self.context.tasker.stopping

    def wait(self, seconds):
        self.delay.wait(seconds)
        if self.stopped():
            raise RuntimeError("用户停止战前增益同步")

    def capture(self):
        if self.stopped():
            raise RuntimeError("用户停止战前增益同步")
        frame = self.context.tasker.controller.post_screencap().wait().get()
        if frame is None:
            raise RuntimeError("无法截取战前增益页面")
        return frame

    def hit(self, name, frame, override=None):
        result = self.context.run_recognition(name, frame, override or {})
        if result is None:
            raise RuntimeError(f"战前增益识别未执行：{name}")
        return result if result.hit else None

    def scroll_list(self, x, y1, y2):
        if self.stopped():
            raise RuntimeError("用户停止战前增益同步")
        scratch = "乐土战前-条目检测"
        result = self.context.run_action(scratch, pipeline_override={scratch: {
            "action": {"type": "Swipe", "param": {
                "begin": [x, y1, 1, 1], "end": [x, y2, 1, 1],
                "duration": 300, "end_hold": 500
            }}
        }})
        if not result or not result.success:
            raise RuntimeError("战前增益列表滑动失败")
        self.wait(.6)

    def edge(self, upper):
        if upper:
            self.buff_start()
            return
        marker = "往世乐土-增益选择-已滑动至最下方"
        for attempt in range(13):
            if self.hit(marker, self.capture()):
                return
            if attempt == 12:
                break
            # 关卡文字、首领预览和增益是不同的输入区域，一处无效时换区域。
            # MuMu实际验证需要拖动后停留，原版200ms直接松开的输入会被吞掉。
            x, y = ((60, 350), (750, 300), (1000, 260), (1220, 350))[attempt % 4]
            self.scroll_list(x, y, y - 150)
        raise RuntimeError("无法确认战前增益列表已到" + ("顶部" if upper else "底部"))

    def buff_start(self):
        # 本页最上方是关卡效果和首领预览，不是增益第1条。
        # 从可确认的底部向回找，避免把整页顶端或旧的首领图标当成增益起点。
        self.edge(False)
        for attempt in range(13):
            frame = self.capture()
            rows = self.cost_rows(frame)
            first = next((row for row in rows if row[0] == 0), None)
            if first:
                y = first[1]
                if 300 <= y <= 360:
                    following = rows[rows.index(first):rows.index(first) + 3]
                    if rows_match(following, BUFF_COSTS[:3]):
                        self.logger.info("已定位战前增益第1～3条，开始核对勾选")
                        return
                # 将第一条对齐至前三条识别区域，短距离慢滑，避免滑过头。
                delta = max(-60, min(60, 330 - y))
                if not delta:
                    raise RuntimeError("已找到增益第一条，但无法同时定位第二、第三条")
            else:
                delta = 60
            if attempt == 12:
                break
            self.scroll_list(95, 450, 450 + delta)
        raise RuntimeError("无法定位战前增益第一条，已停止并保留现场")

    def cost_rows(self, frame):
        # 旧模板中的数字被裁去一半，0 与 5 也能得到高分匹配。
        # 只识别左侧完整负荷数字，再按画面顺序区分两个5、10和15。
        scratch = "乐土战前-条目检测"
        result = self.hit(scratch, frame, {scratch: {
            "enabled": True, "recognition": {"type": "OCR", "param": {
                "roi": [70, 125, 100, 400], "roi_offset": [0, 0, 0, 0],
                "expected": ["^(0|5|10|15)$"], "order_by": "Vertical", "threshold": .8
            }}
        }})
        rows = []
        for item in result.filtered_results if result else []:
            text = item.text.strip()
            if text not in {"0", "5", "10", "15"}:
                continue
            x, y, w, h = item.box
            center = int(y + h / 2)
            # 首尾被列表裁切的数字不能用于定位复核。
            if 140 <= center <= 500 and h >= 20:
                rows.append((int(text), center))
        return sorted(rows, key=lambda row: row[1])

    def row_y(self, index, frame):
        rows = self.cost_rows(frame)
        if index < 3:
            start = next((i for i, row in enumerate(rows) if row[0] == 0), None)
            visible = rows[start:start + 3] if start is not None else []
            expected = BUFF_COSTS[:3]
            offset = index
        else:
            if not self.hit("往世乐土-增益选择-已滑动至最下方", frame):
                raise RuntimeError("核对下半增益时列表未到底部")
            visible = rows[-4:]
            expected = BUFF_COSTS[3:]
            offset = index - 3
        if not rows_match(visible, expected):
            raise RuntimeError(f"无法可靠定位战前增益第 {index + 1} 条，负荷顺序为 {rows}")
        return visible[offset][1]

    def row_state(self, index):
        frame = self.capture()
        y = self.row_y(index, frame)
        # 模板本身高31像素，原30像素ROI装不下它，会将已勾选恒判为未选。
        checkbox = [1155, y - 30, 65, 60]
        scratch = "乐土战前-勾选检测"
        override = {scratch: {"enabled": True, "recognition": {
            "type": "TemplateMatch", "param": {
                "roi": checkbox, "template": ["周常/往世乐土/增益选择/已选中.png"]
            }
        }}}
        selected = bool(self.hit(scratch, frame, override))
        return selected, (1186, y)

    def set_row(self, index, desired):
        for attempt in range(3):
            selected, point = self.row_state(index)
            if selected == desired:
                return
            if attempt == 2:
                raise RuntimeError(f"战前增益第 {index + 1} 条无法" + ("选中，可能负荷不足" if desired else "取消"))
            self.logger.info(f"战前增益第 {index + 1} 条：" + ("补选" if desired else "取消旧选择"))
            if self.stopped():
                raise RuntimeError("用户停止战前增益同步")
            if not self.context.tasker.controller.post_click(*point).wait().succeeded:
                raise RuntimeError("战前增益点击失败")
            self.wait(.5)
            if self.hit("往世乐土-增益选择-增益负荷", self.capture()):
                raise RuntimeError(f"战前增益第 {index + 1} 条触发负荷上限，无法满足当前配置")

    def sync(self, targets):
        for desired in (False, True):
            for upper, indexes in ((True, range(3)), (False, range(3, 7))):
                self.edge(upper)
                for index in indexes:
                    if targets[index] == desired:
                        self.set_row(index, desired)
        # 全部选择完成后再复核，防止游戏因互斥或刷新取消先前勾选。
        for upper, indexes in ((True, range(3)), (False, range(3, 7))):
            self.edge(upper)
            for index in indexes:
                selected, _ = self.row_state(index)
                if selected != targets[index]:
                    raise RuntimeError(f"战前增益第 {index + 1} 条最终状态与配置不一致")

    def run(self, context, argv):
        self.context = context
        self.delay = threading.Event()
        self.logger = Logger("战前增益", context)
        try:
            raw = argv.custom_action_param
            params = json.loads(raw) if isinstance(raw, str) else raw
            targets = params.get("targets", [])
            if len(targets) != 7 or any(type(value) is not bool for value in targets):
                raise ValueError("战前增益目标必须包含七个是/否设置")
            self.logger.ui("按配置核对战前增益：先取消旧选择，再补选", "cyan")
            self.sync(targets)
            if not context.override_pipeline({"乐土战前-同步增益": {"enabled": False}}):
                raise RuntimeError("战前增益同步完成标记失败")
            self.logger.info(f"战前增益同步完成：{targets}")
            self.logger.ui("战前增益已逐项核对，与配置一致", "cyan")
            return True
        except Exception as exc:
            self.logger.error(str(exc))
            if not self.stopped():
                self.logger.ui(f"战前增益同步停止：{exc}", "red")
            return False
        finally:
            self.logger.destroy()
