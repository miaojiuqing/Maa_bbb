from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context


@AgentServer.custom_action("my_action_111")
class MyCustomAction(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:

        print("my_action_111 is running!")

        return True

from maa.agent import AgentServer, CustomAction, Context, CustomActionRunArg
import time

# 右键按下动作（contact:1 代表右键）
@AgentServer.custom_action("RightTouchDown")
class RightTouchDownAction(CustomAction):
    def run(self, context: Context, argv: CustomActionRunArg) -> bool:
        x = argv.get("x", 0)
        y = argv.get("y", 0)
        context.send_command({
            "command": "TouchDown",
            "params": {
                "contact": 1,  # 右键标识
                "x": x,
                "y": y
            }
        })
        time.sleep(0.1)  # 模拟按下时长
        return True

# 右键抬起动作（contact:1 与按下一致）
@AgentServer.custom_action("RightTouchUp")
class RightTouchUpAction(CustomAction):
    def run(self, context: Context, argv: CustomActionRunArg) -> bool:
        x = argv.get("x", 0)
        y = argv.get("y", 0)
        context.send_command({
            "command": "TouchUp",
            "params": {
                "contact": 1,  # 与按下的右键标识一致
                "x": x,
                "y": y
            }
        })
        time.sleep(0.1)
        return True