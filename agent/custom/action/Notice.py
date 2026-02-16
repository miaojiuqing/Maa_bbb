"""
完成后通知
作者:overflow65537
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
                return CustomAction.RunResult(success=False)
            start_crystal = resource.focus.get("start_crystal")

            # 收益
            if start_crystal.isdigit() and end_crystal.isdigit():
                profit = int(end_crystal) - int(start_crystal)

                self.custom_notify(context, "初始水晶:")
                self.custom_notify(context, start_crystal)
                self.custom_notify(context, "当前水晶:")
                self.custom_notify(context, end_crystal)
                self.custom_notify(context, "收益:")
                self.custom_notify(context, str(profit))

        return CustomAction.RunResult(success=True)

    def custom_notify(self, context: Context, msg: str):
        """自定义通知"""
        context.override_pipeline(
            {"custom通知": {"focus": {"Node.Recognition.Succeeded": msg}}}
        )
        context.run_task("custom通知")
