from maa.context import Context
from maa.custom_action import CustomAction
import json
from ..utils.Logger import Logger

from ..utils.RoleConfiguration import ROLE_CONFIG

"""
在战斗中识别角色
v1.0.0
作者 overflow
"""


class RecognitionRole(CustomAction):
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        image = context.tasker.controller.post_screencap().wait().get()
        for role_name, role_info in ROLE_CONFIG.items():
            result = context.run_recognition(
                entry="在战斗中检查角色",
                image=image,
                pipeline_override={
                    "在战斗中检查角色": {
                        "recognition": {
                            "param": {
                                "template": role_info["attack_template"],
                                "threshold": 0.8,
                            },
                        }
                    }
                },
            )
            if result and result.hit:
                context.override_pipeline(
                    {
                        "识别人物": {"enabled": False},
                        "战斗程序": {
                            "action": "Custom",
                            "custom_action": role_info["cls_name"],
                        },
                    }
                )
                return CustomAction.RunResult(success=True)
        context.override_pipeline(
            {
                "识别人物": {"enabled": False},
                "战斗程序": {
                    "action": "Custom",
                    "custom_action": "GeneralFight",
                },
            }
        )

        return CustomAction.RunResult(success=True)
