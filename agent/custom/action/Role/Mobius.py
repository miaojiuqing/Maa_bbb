"""
梅比乌斯 战斗逻辑
v1.0.0
作者 miaojiuqing
"""

import time
from maa.context import Context
from maa.custom_action import CustomAction

from ...utils.BattleCore import CombatActions


class Mobius(CustomAction):
    """梅比乌斯 战斗逻辑"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> CustomAction.RunResult:
        # 创建战斗工具箱，role_name 用于日志显示，写角色名方便排查问题
        工具箱 = CombatActions(context=context, role_name="梅比乌斯")
        工具箱.trigger_qte(1, True)
        工具箱.trigger_qte(2, True)

        # ===== 战斗流程开始 =====
        # 先放一个武器技
        工具箱.use_skill()
        time.sleep(0.5)  # 等待0.2s
        print("梅比乌斯进释放了武器技")

        # 如果大招能量够了就放大招
        # 大招释放后会直接获得3点特殊能量，并且在大招期间血条上有梅比乌斯头像的时候，每次点按大招都会获得一个特殊能量
        if 工具箱.check_status("战斗逻辑-梅比乌斯-能量够开大"):
            print("梅比乌斯大招能量充足，放大招")
            工具箱.long_ultimate_skill()#长按大招变身等待5秒
            # time.sleep(3)#如果是乐土的话整条注释
            if 工具箱.check_status("战斗逻辑-梅比乌斯-特殊能量"):#有特殊能量
                # for _ in range(20):# 大招普攻循环10次,其中十次用于放完大招后的动画时间,有时候大招能量够但是CD没好
                工具箱.use_ultimate_skill()
                time.sleep(0.08)
                工具箱.attack()#有能量会自己消耗，没能量就没正常普攻按了不会有反应
                time.sleep(0.08)
            print("梅比乌斯点大招时间结束") 

        # 若能量不足
        #进行A四下分支一下的循环
        else:
            print("梅比乌斯大招能量不足,普工打一套")
        # 普攻4下，攒出一个特殊能量条
            for _ in range(6):
                    工具箱.attack()
                    工具箱.use_ultimate_skill()   #进二合一，有能量会自己消耗，没能量就没正常普攻按了不会有反应
                    time.sleep(0.08)
            if 工具箱.check_status("战斗逻辑-梅比乌斯-特殊能量"):#有特殊能量
                for _ in range(6):
                    工具箱.attack()
                    工具箱.use_ultimate_skill() 
            print("梅比乌斯打了一下普攻")

        # 切换到下一个角色（这步很重要！不写的话不会自动换人）
        工具箱.switch()

        return CustomAction.RunResult(success=True)
    

    # if("有能量"):{
    #     "开大"
    #     "平A和点按Q循环十次"
    # }
    # else:{#没能量
    #     "普A四下然后点按Q再点按普攻"
    # },
    #  "切换角色"
