"""
崩坏3战斗逻辑核心
v1.0.0
作者:overflow
"""

from maa.context import Context
from maa.define import ColorMatchResult, TemplateMatchResult, OCRResult
import time

import logging
import os
from datetime import datetime, timedelta


class CombatActions:
    """通用战斗功能"""

    def __init__(self, context: Context, role_name: str = ""):
        self.context = context
        self._clear_old_logs()
        self.logger = self._setup_logger(role_name)

    def _setup_logger(self, role_name: str):
        debug_dir = "debug"
        os.makedirs(debug_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d")
        log_file_name = f"custom_{timestamp}.log"
        log_file_path = os.path.join(debug_dir, log_file_name)

        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        logger.propagate = False

        file_handler = logging.FileHandler(log_file_path, mode="a", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            f"%(asctime)s - %(levelname)s - {role_name} - %(message)s"
        )
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

        return logger

    def __del__(self):
        """清理日志记录器资源"""
        try:
            if hasattr(self, "logger") and self.logger:
                # 安全地关闭所有处理器
                for handler in self.logger.handlers[:]:
                    try:
                        handler.close()
                    except:
                        pass
                    self.logger.removeHandler(handler)
        except:
            # 避免在析构函数中抛出异常
            pass

    def _clear_old_logs(self):
        debug_dir = "debug"
        if not os.path.isdir(debug_dir):
            return

        three_days_ago = datetime.now() - timedelta(days=3)
        for root, dirs, files in os.walk(debug_dir):
            for file in files:
                if file.startswith("custom_") and file.endswith(".log"):
                    try:
                        timestamp_str = file.split("_")[1].split(".")[0]
                        file_time = datetime.strptime(timestamp_str, "%Y%m%d")
                        if file_time < three_days_ago:
                            file_path = os.path.join(root, file)
                            os.remove(file_path)
                            self.logger.info(f"已删除过期日志文件: {file_path}")
                    except Exception as e:
                        self.logger.error(f"处理文件 {file} 时出错: {e}")

    def attack(self):
        """
        攻击
        执行一次攻击操作。
        """
        image = self.context.tasker.controller.post_screencap().wait().get()
        if self.context.run_recognition("战斗中", image):
            return self.context.run_action("攻击_action")
        return False

    def long_press_attack(self, duration: int = 1000):
        """
        长按攻击
        按住攻击键一段时间。
        :param duration: 长按时间（毫秒），默认1000
        """
        if duration != 1000:
            self.context.override_pipeline(
                {"长按攻击_action": {"action": {"param": {"duration": duration}}}}
            )
        return self.context.run_action("长按攻击_action")

    def dodge(self):
        """
        闪避
        执行一次闪避操作。
        """
        image = self.context.tasker.controller.post_screencap().wait().get()
        if self.context.run_recognition("战斗中", image):
            return self.context.run_action("闪避_action")
        return False

    def long_press_dodge(self, duration: int = 1000):
        """
        长按闪避
        按住闪避键一段时间。
        :param duration: 长按时间（毫秒），默认1000
        """
        if duration != 1000:
            self.context.override_pipeline(
                {"长按闪避_action": {"action": {"param": {"duration": duration}}}}
            )
        return self.context.run_action("长按闪避_action")

    def use_skill(self, duration: int = 0):
        """
        使用技能
        执行一次技能释放操作。
        :param duration: 技能释放后等待时间（毫秒），默认0
        """
        image = self.context.tasker.controller.post_screencap().wait().get()
        if self.context.run_recognition("战斗中", image):
            self.context.run_action("技能_action")
            time.sleep(duration / 1000)
            return True
        return False

    def use_ultimate_skill(self, duration: int = 0):
        """使用必杀技能"""
        image = self.context.tasker.controller.post_screencap().wait().get()
        if self.context.run_recognition("战斗中", image):
            self.context.run_action("必杀_action")
            time.sleep(duration / 1000)
            return True
        return False

    def down_attack(self, contact: int = 0):
        """
        按下攻击
        按下攻击操作。
        :param contact: 触摸编号
        """
        self.context.override_pipeline(
            {"按下攻击_action": {"action": {"param": {"contact": contact}}}}
        )
        return self.context.run_action("按下攻击_action")

    def up_attack(self, contact: int = 0):
        """
        松开攻击
        松开攻击操作。
        :param contact: 触摸编号
        """
        self.context.override_pipeline(
            {"松开攻击_action": {"action": {"param": {"contact": contact}}}}
        )
        return self.context.run_action("松开攻击_action")

    def trigger_qte(self, target: int = 1):
        """
        触发QTE/换人
        执行QTE或换人操作。
        :param target: QTE位置（1或2），默认1
        :return: 点击操作结果
        """
        image = self.context.tasker.controller.post_screencap().wait().get()
        if not self.context.run_recognition("战斗中", image):
            return False
        if target not in (1, 2):
            raise ValueError("target 参数必须为 1 或 2")
        return self.context.run_action(f"qte{target}")

    def lens_lock(self):
        """
        镜头锁定
        执行镜头锁定操作。
        """
        return self.context.run_action("锁定视角_action")

    def co_operation(self):
        """
        协同者
        协同者操作。
        """
        return self.context.run_action("协同者_action")

    def check_status(self, node: str, pipeline_override: dict = {}):
        """
        检查状态
        检查指定Pipeline节点状态，返回识别结果。
        :param node: Pipeline节点名
        :param pipeline_override: 节点覆盖参数
        :return: 识别结果或False
        """
        try:
            # 获取截图
            image = self.context.tasker.controller.post_screencap().wait().get()
            # 识别并返回结果
            result = self.context.run_recognition(node, image, pipeline_override)
            if result and result.hit:
                return result
            else:
                return False
        except Exception as e:
            self.logger.exception(node + ":" + str(e))
            return False

    def check_ultimate_energy_bar(self) -> bool:
        """
        检查必杀技能能量条
        检查必杀技能能量是否足够，足够时返回True。
        :return: bool
        """
        try:
            # 获取截图
            image = self.context.tasker.controller.post_screencap().wait().get()
            # 识别并返回结果
            energy_result = self.context.run_recognition("技能_能量条", image)
            ultimate_energy_result = self.context.run_recognition(
                "技能_必杀能量", image
            )
            if (
                energy_result
                and energy_result.hit
                and isinstance(energy_result.best_result, OCRResult)
                and ultimate_energy_result
                and ultimate_energy_result.hit
                and isinstance(ultimate_energy_result.best_result, OCRResult)
            ):
                result = energy_result.best_result.text
                try:
                    current_energy, max_energy = map(int, result.split("/"))
                    # 返回int百分比血量
                    if current_energy >= int(ultimate_energy_result.best_result.text):
                        return True
                    else:
                        return False
                except ValueError:
                    return False
            else:
                return False

        except Exception as e:
            self.logger.exception("检查技能_能量条:" + str(e))
            return False

    def get_hp_percent(self) -> int:
        """
        获取当前血量百分比
        识别当前角色血量百分比。
        :return: int，血量百分比（0~100）
        """
        image = self.context.tasker.controller.post_screencap().wait().get()
        result = self.context.run_recognition("检查血量百分比", image)

        if result and result.hit and isinstance(result.best_result, OCRResult):
            result = result.best_result.text
            try:
                current_hp, max_hp = map(int, result.split("/"))
                # 返回int百分比血量
                hp_percent = int((current_hp / max_hp) * 100)
                return min(max(hp_percent, 0), 100)
            except ValueError:
                return 0
        else:
            return 0
