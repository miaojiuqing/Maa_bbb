"""
真理之律者 战斗逻辑
v1.0.0
作者 overflow
"""

import time
from maa.context import Context
from maa.custom_action import CustomAction
from ...utils.BattleCore import CombatActions


class HerrscherOfTruth(CustomAction):
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        action = CombatActions(context=context, role_name="真理之律者")

        if action.check_status("检查常规状态_真理之律者"):
            print("检查常规状态_真理之律者 成功")
            action.use_skill()
            time.sleep(0.01)
            for _ in range(3):
                action.attack()
                time.sleep(0.1)
            action.long_press_attack(700)
            time.sleep(0.01)

            for _ in range(10):
                if action.check_ultimate_energy_bar():
                    print("使用大招 成功")
                    break
                if context.tasker.stopping:
                    return CustomAction.RunResult(success=True)
                action.attack()
                time.sleep(0.1)
            action.use_ultimate_skill()
        else:
            print("检查常规状态_真理之律者 失败")
            action.use_skill()
            time.sleep(0.01)
            action.dodge()
            time.sleep(0.01)
            if action.check_ultimate_energy_bar():
                action.use_ultimate_skill()
            time.sleep(0.01)
            for _ in range(20):
                if action.check_status("检查必杀阶段动能条满_真理之律者"):
                    print("检查必杀阶段动能条满_真理之律者 成功")
                    action.long_press_attack(700)
                if context.tasker.stopping:
                    return CustomAction.RunResult(success=True)
                action.attack()
                time.sleep(0.05)

        return CustomAction.RunResult(success=True)
