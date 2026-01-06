"""
真理之律者 战斗逻辑
v1.0.0
作者 overflow
"""

import time
from maa.context import Context
from maa.custom_action import CustomAction
from ..AutoBattle.Core import CombatActions


class HerrscherOfTruth(CustomAction):
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        action = CombatActions(context=context, role_name="真理之律者")

        if action.check_status("检查常规状态_真理之律者"):
            action.use_skill()
            time.sleep(0.01)
            action.dodge()
            time.sleep(0.01)
            action.long_press_attack(700)

            for _ in range(20):
                if action.check_ultimate_energy_bar():
                    action.use_ultimate_skill()
                    break
                action.attack()
                time.sleep(0.1)

        else:

            action.use_skill()
            time.sleep(0.01)
            action.dodge()
            time.sleep(0.01)
            if action.check_ultimate_energy_bar():
                action.use_ultimate_skill()
            time.sleep(0.01)
            for _ in range(20):
                if action.check_status("检查大招阶段动能跳满_真理之律者"):
                    action.long_press_attack(700)
                action.attack()
                time.sleep(0.1)

        return CustomAction.RunResult(success=True)
