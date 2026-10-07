"""
完成后通知（内含「今日收益统计」：开局 set_crystal 记初始水晶、结束 show_crystal 算收益并通知）
作者:overflow65537

【重构待办 · 先保留不动】
  原调用点挂在 base/pipeline 的「进入游戏/打开游戏.json」与「进入游戏/停止游戏.json」，
  重构期间这两处 pipeline 还没重建，本模块先原样留着，等资源重建完再接回去。
  详见 docs/重构笔记.md
"""

from maa.context import Context
from maa.custom_action import CustomAction
from maa.define import OCRResult
import json


class Notice(CustomAction):
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        param: dict = json.loads(argv.custom_action_param)
        action = param.get("action")
        if action == "set_crystal":
            image = context.tasker.controller.post_screencap().wait().get()
            crystal_reco = context.run_recognition("识别水晶", image)
            if (
                crystal_reco
                and crystal_reco.hit
                and isinstance(crystal_reco.best_result, OCRResult)
            ):
                crystal = crystal_reco.best_result.text

            else:
                crystal = "0"

            context.tasker.resource.override_pipeline(
                {"资源变量": {"focus": {"start_crystal": crystal}}}
            )
        elif action == "show_crystal":
            image = context.tasker.controller.post_screencap().wait().get()
            end_crystal_reco = context.run_recognition("识别水晶", image)

            if (
                end_crystal_reco
                and end_crystal_reco.hit
                and isinstance(end_crystal_reco.best_result, OCRResult)
            ):
                end_crystal = end_crystal_reco.best_result.text
            else:
                end_crystal = "0"

            resource = context.get_node_object("资源变量")
            if resource is None:
                return CustomAction.RunResult(success=True)
            start_crystal = resource.focus.get("start_crystal")

            # 收益
            if start_crystal.isdigit() and end_crystal.isdigit():
                profit = int(end_crystal) - int(start_crystal)
                self.custom_notify(context, f"初始水晶: {start_crystal}, 结束水晶: {end_crystal}, 收益: {profit}")
        return CustomAction.RunResult(success=True)

    def custom_notify(self, context: Context, msg: str):
        """自定义通知"""
        context.override_pipeline(
            {"custom通知": {"focus": {"Node.Recognition.Succeeded": msg}}}
        )
        context.run_task("custom通知")
