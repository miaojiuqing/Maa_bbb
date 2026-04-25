"""
梅比乌斯 战斗逻辑
v1.1.0
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

        #初始化冷却时间变量，防止第一次运行报错
        if not hasattr(self, 'last_ult_time'):
            self.last_ult_time = 0
        # 如果大招能量够了就放大招
        # 大招释放后会直接获得3点特殊能量，并且在大招期间血条上有梅比乌斯头像的时候，每次点按大招都会获得一个特殊能量
        current_time = time.time()  # 获取当前时间戳

        # 判断是否过了20秒冷却
        if current_time - self.last_ult_time >= 25:
            if 工具箱.check_status("战斗逻辑-梅比乌斯-能量够开大"):  # 能量所需100
                print("梅比乌斯大招能量充足，放大招")
                工具箱.long_ultimate_skill()  # 长按大招变身等待5秒
                # time.sleep(3)#如果是乐土的话整条注释
                if 工具箱.check_status("战斗逻辑-梅比乌斯-特殊能量"):  # 有特殊能量
                    # for _ in range(20):# 大招普攻循环10次,其中十次用于放完大招后的动画时间,有时候大招能量够但是CD没好
                    工具箱.use_ultimate_skill()
                    time.sleep(0.08)
                    工具箱.attack()  # 有能量会自己消耗，没能量就没正常普攻按了不会有反应
                    time.sleep(0.08)
                print("梅比乌斯点大招时间结束")

                # 【修复点2】关键修复：释放大招后，必须更新最后释放时间，否则冷却不会生效，或者会一直卡在冷却中
                self.last_ult_time = current_time

            # 若能量不足（但在冷却时间窗口内，或者刚初始化）
            # 进行A四下分支一下的循环
            else:
                print("梅比乌斯大招能量不足,普工打一套")
                # 普攻4下，攒出一个特殊能量条
                for _ in range(6):
                    工具箱.attack()
                    工具箱.use_ultimate_skill()  # 进二合一，有能量会自己消耗，没能量就没正常普攻按了不会有反应
                    time.sleep(0.08)
                if 工具箱.check_status("战斗逻辑-梅比乌斯-特殊能量"):  # 有特殊能量
                    for _ in range(6):
                        工具箱.attack()
                        工具箱.use_ultimate_skill()
                print("梅比乌斯打了一下普攻")
        # 若还在冷却时间内
        else:
            # 直接开始QJQJ
            print(f"梅比乌斯大招冷却中，跳过本次循环 (剩余冷却: {25 - (current_time - self.last_ult_time):.1f}s)")
            # 如果希望冷却期间也普攻，可以保留下面的代码，否则可以注释掉以节省性能
            for _ in range(6):
                工具箱.attack()
                工具箱.use_ultimate_skill()
                time.sleep(0.08)
            if 工具箱.check_status("战斗逻辑-梅比乌斯-特殊能量"):
                for _ in range(6):
                    工具箱.attack()
                    工具箱.use_ultimate_skill()

        # 切换到下一个角色（这步很重要！不写的话不会自动换人）
        工具箱.switch()

        return CustomAction.RunResult(success=True)