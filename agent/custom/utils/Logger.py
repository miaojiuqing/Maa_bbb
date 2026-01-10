"""
自定义 Logger 组件
支持组件标识、HTML UI 输出和资源清理
"""

import html
import logging
import re
import sys
from pathlib import Path
from maa.context import Context


class Logger:
    """自定义 Logger 类，支持组件标识和 UI 输出"""

    # 颜色名称到16进制的映射
    COLOR_MAP = {
        "black": "#000000",
        "white": "#FFFFFF",
        "red": "#FF0000",
        "green": "#008000",
        "blue": "#0000FF",
        "yellow": "#FFFF00",
        "cyan": "#00FFFF",
        "magenta": "#FF00FF",
        "orange": "#FFA500",
        "purple": "#800080",
        "pink": "#FFC0CB",
        "brown": "#A52A2A",
        "gray": "#808080",
        "grey": "#808080",
    }

    def __init__(self, name: str, context: Context | None = None):
        """
        初始化 Logger

        Args:
            name: 组件名称，用于标识日志来源
        """
        self.name = name
        self.context = context
        self._logger = logging.getLogger(f"custom.{name}")
        self._logger.setLevel(logging.INFO)

        # 避免重复添加 handler
        if not self._logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self):
        """设置日志处理器"""
        # 获取日志文件路径（在 custom/utils 目录下）
        log_dir = Path(__file__).parent.parent.parent / "debug"
        log_file = log_dir / "agent.log"

        # 创建格式器
        formatter = logging.Formatter(
            "%(asctime)s - [%(name)s] - %(levelname)s - %(message)s - {self.name}",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # 文件处理器（追加模式）
        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        # 添加处理器
        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)

    def _normalize_color(self, color: str) -> str:
        """
        规范化颜色值

        Args:
            color: 颜色名称或16进制值

        Returns:
            16进制颜色值（带 # 前缀）
        """
        color = color.strip().lower()

        # 如果是颜色名称，转换为16进制
        if color in self.COLOR_MAP:
            return self.COLOR_MAP[color]

        # 如果已经是16进制格式，确保有 # 前缀
        if color.startswith("#"):
            return color
        elif re.match(r"^[0-9A-Fa-f]{6}$", color):
            return f"#{color}"

        # 默认返回黑色
        return "#000000"

    def _is_html(self, text: str) -> bool:
        """
        检查文本是否已经是 HTML 代码

        Args:
            text: 要检查的文本

        Returns:
            如果是 HTML 代码返回 True，否则返回 False
        """
        # 简单的 HTML 标签检测
        html_pattern = re.compile(r"<[^>]+>", re.IGNORECASE)
        return bool(html_pattern.search(text))

    def ui(self, text: str, color: str = "black") -> bool:
        """
        生成带颜色的 HTML 代码

        Args:
            text: 要显示的文本
            color: 颜色（颜色名称或16进制，如 "red" 或 "#FF0000"）

        Returns:
            是否成功
        """
        if not self.context:
            return False
        # 如果文本已经是 HTML，直接返回（忽略颜色）
        if self._is_html(text):
            html_code = text

        else:

            # 规范化颜色
            hex_color = self._normalize_color(color)

            # 转义 HTML 特殊字符
            escaped_text = html.escape(text)

            # 生成带颜色的 HTML
            html_code = f'<font color="{hex_color}">{escaped_text}</font>'

        result = self.context.run_task(
            "自定义信息_为了防止重复所以名字长一点",
            {
                "自定义信息_为了防止重复所以名字长一点": {
                    "focus": {
                        "Node.Recognition.Succeeded": html_code,
                    }
                }
            },
        )
        return bool(result)

    def debug(self, message: str, *args, **kwargs):
        """记录 DEBUG 级别日志"""
        self._logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        """记录 INFO 级别日志"""
        self._logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        """记录 WARNING 级别日志"""
        self._logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        """记录 ERROR 级别日志"""
        self._logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        """记录 CRITICAL 级别日志"""
        self._logger.critical(message, *args, **kwargs)

    def exception(self, message: str, *args, exc_info=True, **kwargs):
        """记录异常日志"""
        self._logger.exception(message, *args, exc_info=exc_info, **kwargs)

    def destroy(self):
        """
        销毁 Logger，清理所有资源
        应该在不再使用 Logger 时调用
        """
        if self._logger is None:
            return

        # 关闭所有 handlers
        handlers = self._logger.handlers[:]  # 创建副本避免迭代时修改
        for handler in handlers:
            handler.close()
            self._logger.removeHandler(handler)

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口，自动清理资源"""
        self.destroy()

    def __del__(self):
        """析构函数，确保资源被清理"""
        try:
            if hasattr(self, "_logger") and self._logger is not None:
                self.destroy()
        except Exception:
            # 析构函数中不应该抛出异常
            pass
