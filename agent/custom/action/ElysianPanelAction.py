"""乐土关内移动辅助：识别门、控制摇杆并恢复视角。"""
import json
import time
from types import SimpleNamespace
from maa.custom_action import CustomAction
from .Role.CharacterCombat import CharacterCombat

GATES = {"黄金": 19, "无限": 17, "浮生": 22}
NAMED = {1, 2, 3, 10, 11, 12, 13, 14, 15, 17, 18, 19, 20, 21, 22, 23}
LABELS = {1: "鏖灭", 2: "真我", 3: "空梦", 10: "商店", 11: "戒律", 12: "螺旋", 13: "商店", 14: "天慧", 15: "繁星", 17: "无限", 18: "刹那", 19: "黄金", 20: "救世", 21: "旭光", 22: "浮生", 23: "首领"}


class ElysianPanelAction(CustomAction):
    def __init__(self, stop_event, report, preview):
        super().__init__()
        self.stop_event, self.report, self.preview = stop_event, report, preview
        self.operation, self.target = "forward", "黄金"
        self.outcome = ""
        self.combat_handler = CharacterCombat()

    def stopped(self, context):
        return self.stop_event.is_set() or context.tasker.stopping

    def finish(self, text):
        self.outcome = text
        self.report(text)
        return True

    def capture(self, context):
        frame = context.tasker.controller.post_screencap().wait().get()
        if frame is None:
            raise RuntimeError("截图失败，请重新连接 MuMu")
        self.preview(frame)
        return frame

    def hit(self, context, name, frame):
        result = context.run_recognition(name, frame)
        return result if result and result.hit else None

    def arena(self, context, frame):
        return bool(self.hit(context, "战斗逻辑-战斗中", frame)
                    and self.hit(context, "角色战斗-生命HUD", frame))

    def walk(self, context, dx=0, duration=.6, dy=-76):
        controller = context.tasker.controller
        if self.stopped(context):
            return
        try:
            if not controller.post_touch_down(153, 571).wait().succeeded:
                raise RuntimeError("摇杆按下失败")
            if self.stopped(context):
                return
            if not controller.post_touch_move(153 + dx, 571 + dy).wait().succeeded:
                raise RuntimeError("摇杆移动失败")
            end = time.monotonic() + duration
            while time.monotonic() < end and not self.stopped(context):
                self.stop_event.wait(.02)
        finally:
            if not controller.post_touch_up().wait().succeeded:
                raise RuntimeError("摇杆松开失败，请在模拟器内检查")

    def confirmed_gate(self, context, frame):
        label = self.hit(context, "面板-门前身份", frame)
        prompt = self.hit(context, "面板-前往", frame)
        return prompt if label and prompt else None

    def run(self, context, argv):
        try:
            self.outcome = ""
            if self.stopped(context):
                return self.finish("已停止")
            frame = self.capture(context)
            if self.operation == "scan":
                result = context.run_recognition("面板-门检测", frame)
                items = result.raw_detail.get("all", []) if result else []
                names = [f"{LABELS[r['cls_index']]} {r['score']:.0%}" for r in items
                         if r.get("cls_index") in NAMED and r.get("score", 0) >= .3]
                return self.finish("当前识别（低于 55% 不用于走门）：" + ("、".join(names) if names else "没有门，请在战后场地调整视角"))
            if self.operation == "enter":
                prompt = self.confirmed_gate(context, frame)
                if not prompt:
                    return self.finish(f"未同时读到「{self.target}」和「前往」，没有点击")
                if self.stopped(context):
                    return self.finish("已停止")
                x, y, w, h = prompt.box
                if not context.tasker.controller.post_click(x+w//2, y+h//2).wait().succeeded:
                    raise RuntimeError("点击前往失败")
                self.stop_event.wait(.8)
                self.capture(context)
                return self.finish(f"已点击「{self.target}」门的前往，请查看关卡画面")
            if not self.arena(context, frame):
                return self.finish("当前不是可操作关卡：请进入战斗场地，并关闭暂停、对话或刻印选择窗口")
            if self.operation == "forward":
                self.report("按住左侧摇杆前进 0.6 秒…")
                self.walk(context)
                self.stop_event.wait(.2)
                self.capture(context)
                return self.finish("已停止" if self.stopped(context) else "前进输入已完成并松开摇杆；请对照画面确认角色位置变化")
            if self.operation == "combat":
                return self.combat(context, argv)
            return self.navigate(context)
        except Exception as exc:
            self.outcome = f"任务停止：{type(exc).__name__}: {exc}"
            self.report(self.outcome)
            return False

    def combat(self, context, argv):
        deadline = time.monotonic() + 60
        # 保持本次面板任务的身份；若每轮新建子任务，助战计时会每轮重置。
        combat_args = SimpleNamespace(task_detail=argv.task_detail, custom_action_param=json.dumps({
            "character": "窈窕谍影", "variant": "elysian_huashang", "confirmed_signet": "华裳"}))
        self.report("丽塔华裳战斗中（最多 60 秒），可随时停止")
        while time.monotonic() < deadline and not self.stopped(context):
            frame = self.capture(context)
            if not self.arena(context, frame):
                return self.finish("战斗暂停：出现菜单、对话或其他画面")
            if self.hit(context, "角色战斗-战后禁用", frame):
                return self.finish("检测到战后禁用按钮，已停止战斗；处理奖励后可使用找门")
            if self.stopped(context):
                break
            if not self.combat_handler.run(context, combat_args):
                return self.finish("角色出招执行结束，请检查当前画面")
            self.stop_event.wait(.05)
        return self.finish("已停止" if self.stopped(context) else "60 秒战斗测试结束；需要继续时再点战斗")

    def navigate(self, context):
        deadline, turns, steps = time.monotonic() + 40, 0, 0
        while time.monotonic() < deadline and steps < 24 and not self.stopped(context):
            frame = self.capture(context)
            if self.confirmed_gate(context, frame):
                return self.finish(f"已到「{self.target}」门前。需要过门时点「进入确认的门」")
            if not self.arena(context, frame):
                return self.finish("找门暂停：请关闭对话、暂停或奖励选择窗口")
            if not self.hit(context, "角色战斗-战后禁用", frame):
                return self.finish("尚未确认战斗结束；找门只在丽塔战后按钮禁用时运行")
            result = context.run_recognition("面板-门检测", frame)
            all_items = result.raw_detail.get("all", []) if result else []
            named = [r for r in all_items if r.get("cls_index") in NAMED and r.get("score", 0) >= .55]
            print(f"GATE_DETECTIONS {all_items}", flush=True)
            selected = [r for r in named if r["cls_index"] == GATES[self.target]]
            if len(selected) > 1:
                return self.finish("同类门识别到多个位置，已停止；请调整视角后重试")
            if selected:
                box = selected[0]["box"]
                cx, near = box[0] + box[2]/2, box[2] >= 100
                self.report(f"已识别「{self.target}」，靠近第 {steps+1} 步")
            else:
                frames = [r for r in all_items if r.get("cls_index") == 8 and r.get("score", 0) >= .3]
                if frames and not named:
                    cx = sum(r["box"][0]+r["box"][2]/2 for r in frames)/len(frames)
                    near = False
                    self.report(f"门尚未展开，靠近门框第 {steps+1} 步")
                else:
                    if named and steps == 0:
                        names = "、".join(dict.fromkeys(LABELS[r["cls_index"]] for r in named))
                        return self.finish(f"当前识别到：{names}；没有确认「{self.target}」。请换目标门或调整视角后再试")
                    if turns >= 6:
                        return self.finish(f"转动视角 6 次仍未确认「{self.target}」，已停止；可换门或手动调整视角")
                    self.report(f"搜索「{self.target}」：转动视角 {turns+1}/6")
                    if self.stopped(context):
                        break
                    if not context.tasker.controller.post_swipe(862, 301, 762, 301, 250).wait().succeeded:
                        raise RuntimeError("转动视角失败")
                    turns += 1
                    self.stop_event.wait(.3)
                    continue
            dx = max(-65, min(65, int((cx-640)*.35)))
            self.walk(context, dx, .25 if near else .6)
            steps += 1
            self.stop_event.wait(.25)
        self.capture(context)
        return self.finish("已停止" if self.stopped(context) else "本次找门已达时间/步数上限，已松开摇杆；请查看画面后再试")
