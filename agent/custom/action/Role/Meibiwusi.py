"""
梅比乌斯 战斗逻辑
v1.0.0
作者 miaojiuqing
"""

import time
from maa.context import Context
from maa.custom_action import CustomAction

from ...utils.BattleCore import CombatActions


class Meibiwusi(CustomAction):
    """梅比乌斯 战斗逻辑"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> CustomAction.RunResult:
        # 创建战斗工具箱，role_name 用于日志显示，写角色名方便排查问题
        工具箱 = CombatActions(context=context, role_name="梅比乌斯")

        # ===== 战斗流程开始 =====
        # 先放一个武器技
        工具箱.use_skill()
        time.sleep(0.5)  # 等待0.2s
        print("梅比乌斯进释放了武器技")

        # 如果大招能量够了就放大招
        # 大招释放后会直接获得3点特殊能量，并且在大招期间血条上有梅比乌斯头像的时候，每次点按大招都会获得一个特殊能量
        if 工具箱.check_ultimate_energy_bar():
            print("梅比乌斯大招能量充足，放大招")
            工具箱.long_ultimate_skill()#长按大招变身等待5秒
            time.sleep(5)
        #动画播放完毕后，检查血条上有没有梅比乌斯的头像，有的话就“点按大招”和“点按普攻”循环
            if 工具箱.check_status("战斗逻辑-梅比乌斯-大招状态检查"):
                print("梅比乌斯大招状态检查成功,开始大招普攻循环")
                for _ in range(10):# 大招普攻循环10次
                    工具箱.use_ultimate_skill()
                    time.sleep(0.25)
                    工具箱.attack()
                    time.sleep(0.25)
                    print("梅比乌斯点大招时间结束") 

        # 若能量不足
        #进行A四下分支一下的循环
        else:
            print("梅比乌斯大招能量不足,普工打一套")
        # 普攻4下，攒出一个特殊能量条
            for _ in range(4):
                    工具箱.attack()
            # 点按大招消耗特殊能量条,以进行一次分支攻击，然后再接一个平A触发特殊攻击
            工具箱.use_ultimate_skill()   #进行一个点按大招的动作，消耗特殊能量强化一次普攻
            print("梅比乌斯点按了一下大招进行分支攻击") 
            time.sleep(0.25)            #等一会，点按之后有个小动画
            工具箱.attack()             #进行一个平A的动作     
            print("梅比乌斯点按了一下普攻进行强化平A")
            time.sleep(0.25)

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
