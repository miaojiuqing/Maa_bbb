"""
通用 战斗逻辑
v1.0.0
作者 miaojiuqing
"""

from maa.context import Context
from maa.custom_action import CustomAction
import time

from ...utils.BattleCore import CombatActions


class GeneralFight(CustomAction):
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        ATC = CombatActions(context, "GeneralFight")
        ATC.attack()  # 攻击一次
        ATC.use_skill()  # 使用技能
        for _ in range(10):  # 攻击10次,每次间隔50ms
            ATC.attack()
            time.sleep(0.05)
        ATC.dodge()  # 闪避一次
        time.sleep(0.01)  # 等待10ms,确保闪避生效
        ATC.long_press_attack()  # 长按攻击
        ATC.co_operation()  # 协同者
        ATC.use_ultimate_skill()  # 使用终极技能
        ATC.switch()  # 切换到下一个目标

        return CustomAction.RunResult(success=True)
