"""用真实 Maa 资源验证启动参数以及桌面选项不会禁用安卓启动。"""

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import jsonc
from maa.resource import Resource
from maa.tasker import LoggingLevelEnum, Tasker

from agent.custom.action.StartGameByPackage import StartGameByPackage


ROOT = Path(__file__).resolve().parents[1]
Tasker.set_stdout_level(LoggingLevelEnum.Off)
OPTIONS = jsonc.loads((ROOT / "assets/tasks/游戏启动.json").read_text(encoding="utf-8"))["option"]


def selected_case(name, value):
    return next(case for case in OPTIONS[name]["cases"] if case["name"] == value).get("pipeline_override", {})


class GameStartTests(unittest.TestCase):
    def load(self, *paths):
        resource = Resource()
        for path in paths:
            self.assertTrue(resource.post_bundle(ROOT / "assets/resource" / path).wait().status.succeeded)
        return resource

    def apply(self, resource, name, value):
        override = selected_case(name, value)
        if override:
            self.assertTrue(resource.override_pipeline(override))

    def run_fast_start(self, resource, stopping=False, succeeded=True):
        controller = Mock()
        controller.post_start_app.return_value.wait.return_value.succeeded = succeeded
        context = SimpleNamespace(
            get_node_data=resource.get_node_data,
            tasker=SimpleNamespace(stopping=stopping, controller=controller),
        )
        with patch("agent.custom.action.StartGameByPackage.Logger"):
            result = StartGameByPackage().run(context, None)
        return result, controller

    def test_android_launch_modes_and_hidden_desktop_option(self):
        for fast in ("Yes", "No"):
            for desktop_esc in ("Yes", "No"):
                with self.subTest(fast=fast, desktop_esc=desktop_esc):
                    resource = self.load("base")
                    self.apply(resource, "不自行启动游戏", fast)
                    self.apply(resource, "启动游戏时不断尝试输入ESC", desktop_esc)
                    fallback = resource.get_node_data("模拟器包名游戏启动")
                    self.assertTrue(fallback["enabled"])
                    self.assertEqual(fallback["action"]["type"], "StartApp")
                    self.assertEqual(fallback["action"]["param"]["package"], "com.miHoYo.enterprise.NGHSoD")
                    self.assertEqual(resource.get_node_data("启动并进入游戏")["action"]["type"], "DoNothing")
                    entry = resource.get_node_data("登录方式选择接口")
                    self.assertEqual(entry["action"]["type"], "Custom" if fast == "Yes" else "DoNothing")
                    if fast == "Yes":
                        self.assertEqual(entry["action"]["param"]["custom_action"], "StartGameByPackage")
                        result, controller = self.run_fast_start(resource)
                        self.assertTrue(result)
                        controller.post_start_app.assert_called_once_with(fallback["action"]["param"]["package"])

    def test_channel_packages_are_preserved(self):
        interface = jsonc.loads((ROOT / "assets/interface.json").read_text(encoding="utf-8"))
        for entry in interface["resource"]:
            if "安卓端" not in entry.get("controller", []):
                continue
            paths = [path.removeprefix("./resource/") for path in entry["path"]]
            with self.subTest(resource=entry["name"]):
                resource = self.load(*paths)
                expected = resource.get_node_data("模拟器包名游戏启动")["action"]["param"]["package"]
                self.apply(resource, "不自行启动游戏", "Yes")
                self.apply(resource, "启动游戏时不断尝试输入ESC", "No")
                self.assertTrue(resource.get_node_data("模拟器包名游戏启动")["enabled"])
                self.assertTrue(expected)
                result, controller = self.run_fast_start(resource)
                self.assertTrue(result)
                controller.post_start_app.assert_called_once_with(expected)

    def test_desktop_esc_remains_optional(self):
        for paths in (("base", "resource_win32"), ("base", "resource_win32", "resource_win32_jp")):
            for esc in ("Yes", "No"):
                with self.subTest(paths=paths, esc=esc):
                    resource = self.load(*paths)
                    # 模拟前端保留隐藏的安卓选项关闭值。
                    self.apply(resource, "不自行启动游戏", "No")
                    self.apply(resource, "启动游戏时不断尝试输入ESC", esc)
                    self.assertEqual(resource.get_node_data("启动并进入游戏")["action"]["type"], "DoNothing")
                    fallback = resource.get_node_data("模拟器包名游戏启动")
                    self.assertEqual(fallback["enabled"], esc == "Yes")
                    self.assertEqual(fallback["action"]["type"], "ClickKey")
                    self.assertEqual(fallback["action"]["param"]["key"], [27])
                    self.apply(resource, "不自行启动游戏", "Yes")
                    result, controller = self.run_fast_start(resource)
                    self.assertTrue(result)
                    controller.post_start_app.assert_not_called()

    def test_empty_package_and_cancel_do_not_start_app(self):
        resource = self.load("base")
        result, controller = self.run_fast_start(resource, stopping=True)
        self.assertFalse(result)
        controller.post_start_app.assert_not_called()
        self.assertTrue(resource.override_pipeline({
            "模拟器包名游戏启动": {"action": {"type": "StartApp", "param": {"package": ""}}}
        }))
        result, controller = self.run_fast_start(resource)
        self.assertFalse(result)
        controller.post_start_app.assert_not_called()

    def test_controller_start_failure_is_reported(self):
        resource = self.load("base")
        result, controller = self.run_fast_start(resource, succeeded=False)
        self.assertFalse(result)
        controller.post_start_app.assert_called_once_with("com.miHoYo.enterprise.NGHSoD")


if __name__ == "__main__":
    unittest.main()
