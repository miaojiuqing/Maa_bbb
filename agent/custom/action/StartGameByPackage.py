"""极速启动使用当前资源的游戏包名，只在启动任务入口执行一次。"""

from maa.custom_action import CustomAction

from ..utils.Logger import Logger


class StartGameByPackage(CustomAction):
    def run(self, context, argv):
        logger = Logger("启动游戏", context)
        try:
            if context.tasker.stopping:
                return False
            node = context.get_node_data("模拟器包名游戏启动") or {}
            action = node.get("action", {})
            # 桌面端的同名节点是 ESC，隐藏的安卓选项不能启动桌面程序。
            if action.get("type") != "StartApp":
                return True
            package = action.get("param", {}).get("package", "").strip()
            if not package:
                logger.error("当前资源未配置游戏包名，无法极速启动")
                return False
            logger.info(f"按当前资源包名启动游戏：{package}")
            return context.tasker.controller.post_start_app(package).wait().succeeded
        except Exception as exc:
            logger.exception(f"启动游戏失败：{exc}")
            return False
        finally:
            logger.destroy()
