"""
孑遗千星 战斗逻辑
v1.0.0
作者 miaojiuqing
"""

from maa.context import Context
from maa.custom_action import CustomAction
from ...utils.BattleCore import CombatActions


class SpinaAstera(CustomAction):
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        context.run_action("自动战斗-乐土-薇塔战斗循环")
        return CustomAction.RunResult(success=True)
