"""
炽愿吉星 战斗逻辑
v1.0.0
作者 miaojiuqing
"""

from maa.context import Context
from maa.custom_action import CustomAction
from ...utils.BattleCore import CombatActions


class FieryWishingStar(CustomAction):
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        ATC = CombatActions(context=context, role_name="炽愿吉星")
        context.run_action("自动战斗-乐土-新春虫战斗循环")
        ATC.switch()
        return CustomAction.RunResult(success=True)
