"""单次短距离走门验证。只靠近已指定的门；交互另行确认。"""
import json
import time
from maa.custom_action import CustomAction


class ElysianGateApproach(CustomAction):
    def __init__(self):
        super().__init__()
        self.steps = 0

    def run(self, context, argv):
        params = json.loads(argv.custom_action_param or "{}")
        selected = int(params.get("class_index", 19))
        if context.tasker.stopping:
            return False
        image = context.tasker.controller.post_screencap().wait().get()
        if params.get("search"):
            before = context.run_recognition("乐土试验-门检测", image)
            visible = [r for r in (before.raw_detail.get("all", []) if before else []) if r.get("cls_index") not in (0, 4, 5, 6, 7, 9, 16) and r.get("score", 0) >= .55]
            if visible:
                print(f"GATE_SEARCH found={visible}", flush=True)
                return False
            if self.steps >= 6:
                print("GATE_SEARCH step limit reached", flush=True)
                return False
            context.tasker.controller.post_swipe(862, 301, 762, 301, 250).wait()
            self.steps += 1
            image = context.tasker.controller.post_screencap().wait().get()
            found = context.run_recognition("乐土试验-门检测", image)
            print(f"GATE_SEARCH after={found.raw_detail if found else None}", flush=True)
            return True
        if params.get("interact"):
            label = context.run_recognition("乐土试验-门前身份", image)
            prompt = context.run_recognition("乐土试验-前往", image)
            if selected not in (19, 17, 22) or not label or not label.hit or not prompt or not prompt.hit:
                print("GATE_ENTER refused: identity/prompt not confirmed", flush=True)
                return False
            x, y, w, h = prompt.box
            print(f"GATE_ENTER confirmed class={selected} label={label.best_result.text}", flush=True)
            return context.tasker.controller.post_click(x + w // 2, y + h // 2).wait().succeeded
        if self.steps >= 6:
            print("GATE_APPROACH step limit reached", flush=True)
            return False
        result = context.run_recognition("乐土试验-门检测", image)
        detections = result.raw_detail.get("all", []) if result else []
        if params.get("reveal"):
            named = [r for r in detections if r.get("cls_index") in (1, 2, 3, 10, 11, 12, 13, 14, 15, 17, 18, 19, 20, 21, 22, 23) and r.get("score", 0) >= .55]
            if named:
                print(f"GATE_REVEAL named={named}", flush=True)
                return False
            frames = [r for r in detections if r.get("cls_index") == 8 and r.get("score", 0) >= .3]
            if not frames:
                print("GATE_REVEAL no frames visible", flush=True)
                return False
            cx = sum(r["box"][0] + r["box"][2] / 2 for r in frames) / len(frames)
            gates = [{"box": [int(cx)-10, 0, 20, 20], "label": "unopened_group"}]
        else:
            gates = [r for r in detections if r.get("cls_index") == selected and r.get("score", 0) >= .55]
        if len(gates) != 1:
            print(f"GATE_APPROACH refused: expected one confident gate, got {gates}", flush=True)
            return False
        gate = gates[0]
        x, y, w, h = gate["box"]
        print(f"GATE_APPROACH before={gate}", flush=True)
        if w >= 115:
            print("GATE_APPROACH near gate; inspect interaction prompt", flush=True)
            return False
        # 将屏幕水平误差转换为小幅侧向摇杆偏移；每次只走 600ms。
        dx = max(-65, min(65, int((x + w / 2 - 640) * .35)))
        controller = context.tasker.controller
        try:
            if not controller.post_touch_down(153, 571).wait().succeeded:
                return False
            if not controller.post_touch_move(153 + dx, 495).wait().succeeded:
                return False
            end = time.monotonic() + .6
            while time.monotonic() < end and not context.tasker.stopping:
                time.sleep(.02)
        finally:
            controller.post_touch_up().wait()
        self.steps += 1
        image = context.tasker.controller.post_screencap().wait().get()
        after = context.run_recognition("乐土试验-门检测", image)
        print(f"GATE_APPROACH after={after.raw_detail if after else None}", flush=True)
        return True
