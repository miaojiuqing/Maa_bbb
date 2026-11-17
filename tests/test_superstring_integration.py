"""验证模拟器超弦空间的配队分流、动作注册和运行资源。"""

import ast
import importlib.util
import json
import re
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from maa.resource import Resource
from maa.tasker import LoggingLevelEnum, Tasker

from agent.custom.action.SuperstringCombat import SuperstringCombat


ROOT = Path(__file__).resolve().parents[1]
TASK_PATH = ROOT / "assets/tasks/周期性/超弦空间new.json"
PIPELINE_PATH = ROOT / "assets/resource/base/pipeline/周期性任务/超弦空间new/超弦空间new.json"
TASK = json.loads(TASK_PATH.read_text(encoding="utf-8"))
PIPELINE = json.loads(PIPELINE_PATH.read_text(encoding="utf-8"))
TOP_ROOM = "超弦空间new-流程-上方房间待挑战"
BOTTOM_ROOM = "超弦空间new-流程-下方房间待挑战"
Tasker.set_stdout_level(LoggingLevelEnum.Off)


class SuperstringIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.resource = Resource()
        self.assertTrue(self.resource.post_bundle(ROOT / "assets/resource/base").wait().status.succeeded)

    def apply_case(self, option, value):
        case = next(item for item in TASK["option"][option]["cases"] if item["name"] == value)
        self.assertTrue(self.resource.override_pipeline(case.get("pipeline_override", {})))

    def next_names(self, node):
        return [item["name"] for item in self.resource.get_node_data(node)["next"]]

    def test_upper_and_lower_teams_are_independent(self):
        for upper in ("不更换编队", "A队", "B队", "C队", "D队"):
            for lower in ("不更换编队", "A队", "B队", "C队", "D队"):
                with self.subTest(upper=upper, lower=lower):
                    self.resource = Resource()
                    self.assertTrue(self.resource.post_bundle(ROOT / "assets/resource/base").wait().status.succeeded)
                    self.apply_case("超弦空间new-前三关预设编队", upper)
                    self.apply_case("超弦空间new-高危区预设编队", lower)
                    for node in ("超弦空间new-流程-上下两层未解锁", TOP_ROOM,
                                 "超弦空间new-流程-第四间待挑战"):
                        self.assertEqual(self.next_names(node), ["超弦空间new-点击战斗准备-上三区"])
                    self.assertEqual(self.next_names(BOTTOM_ROOM), ["超弦空间new-点击战斗准备-下层"])
                    for group, selected in (("上三区", upper), ("下层", lower)):
                        self.assertEqual(
                            self.next_names(f"超弦空间new-点击战斗准备-{group}"),
                            ["超弦空间new-点击开始战斗"] if selected == "不更换编队"
                            else [f"超弦空间new-{group}点击预设队伍"],
                        )
                        if selected != "不更换编队":
                            self.assertEqual(self.next_names(f"超弦空间new-{group}点击预设队伍"),
                                             [f"超弦空间new-{group}选择{selected}"])

    def test_room_recognition_regions_are_separate(self):
        top_roi = PIPELINE[TOP_ROOM]["roi"]
        bottom_roi = PIPELINE[BOTTOM_ROOM]["roi"]
        self.assertLessEqual(top_roi[1] + top_roi[3], bottom_roi[1])
        for selection in ("Yes", "No"):
            self.apply_case("超弦空间new-只打前三层", selection)
            choices = self.next_names("超弦空间new-流程-检查当期深渊挑战情况")
            self.assertIn(TOP_ROOM, choices)
            self.assertIn(BOTTOM_ROOM, choices)

    def test_signet_style_assist_actions_are_not_team_switches(self):
        action = SuperstringCombat()
        role, team = action._load({"role": "窈窕谍影", "variant": "standard", "team": "default"})
        self.assertEqual(team["opening"], [])
        self.assertIn("switch_1", role["touch_actions"])
        self.assertNotIn("support_1", role["touch_actions"])

    def test_presets_use_ocr_results_and_confirm_the_scheme(self):
        for group in ("上三区", "下层"):
            for letter in "ABCD":
                node = PIPELINE[f"超弦空间new-{group}选择{letter}队"]
                self.assertEqual(node["recognition"], "OCR")
                self.assertEqual(node["expected"], [f"{letter}.*队"])
                self.assertNotIn("target", node)
                self.assertEqual(node["next"], ["超弦空间new-使用预设方案"])
        self.assertEqual(PIPELINE["超弦空间new-使用预设方案"]["next"], ["超弦空间new-点击开始战斗"])

    def test_recommendation_dialog_returns_to_the_battle_flow(self):
        nodes = self.resource.get_node_data("超弦空间new-点击开始战斗")["next"]
        recommendation = next(item for item in nodes if item["name"].endswith("-推荐特性"))
        self.assertTrue(recommendation["jump_back"])
        self.assertIn("超弦空间new-流程-编队完成后进入战斗流程", self.next_names("超弦空间new-点击开始战斗"))

    def test_last_room_needs_a_positive_score(self):
        node = PIPELINE["超弦空间new-流程-四层均已挑战完毕"]
        self.assertEqual(node["recognition"], "OCR")
        for text in ("0", "", "未解锁"):
            self.assertFalse(any(re.search(pattern, text) for pattern in node["expected"]))
        for text in ("1", "6000", "6 000", "6,000"):
            self.assertTrue(any(re.search(pattern, text) for pattern in node["expected"]))
        self.assertEqual(TASK["option"]["超弦空间new-只打前三层"]["default_case"], "No")

    def test_registration_is_inside_the_embedded_agent_scan_root(self):
        source = ast.parse((ROOT / "agent/CustomFile.py").read_text(encoding="utf-8"))
        registration = next(node for node in source.body if isinstance(node, ast.ClassDef)
                            and node.name == "SuperstringCombat_Cls")
        decorator = registration.decorator_list[0]
        self.assertEqual(ast.unparse(decorator.func), "AgentServer.custom_action")
        self.assertEqual(decorator.args[0].value, "SuperstringCombat")
        imports = [node for node in source.body if isinstance(node, ast.ImportFrom)]
        self.assertTrue(any(node.module == "agent.custom.action.SuperstringCombat" for node in imports))
        combat = ast.parse((ROOT / "agent/custom/action/SuperstringCombat.py").read_text(encoding="utf-8"))
        self.assertFalse(any(isinstance(node, ast.ClassDef) and node.decorator_list for node in combat.body))

    def test_profiles_are_in_the_agent_tree_used_by_packaging(self):
        with patch.object(sys, "path", [str(ROOT / "tools"), *sys.path]):
            with patch.object(sys, "argv", ["install.py", "test-superstring", "win", "x64"]):
                namespace = runpy.run_path(str(ROOT / "tools/install.py"), run_name="install_test")
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory)
            (package / "interface.json").write_text(json.dumps({"agent": {}}), encoding="utf-8")
            namespace["install_agent"].__globals__["install_path"] = package
            namespace["install_agent"]()
            destination = package / "agent"
            for relative in ("roles/rita_standard.json", "teams/default.json"):
                self.assertTrue((destination / "custom/profiles/superstring" / relative).is_file())
            spec = importlib.util.spec_from_file_location(
                "packaged_superstring", destination / "custom/action/SuperstringCombat.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            role, team = module.SuperstringCombat()._load(
                {"role": "窈窕谍影", "variant": "standard", "team": "default"}
            )
            self.assertEqual(role["character"], "窈窕谍影")
            self.assertEqual(team["name"], "默认队伍")

    def test_callback_stops_clicking_after_leaving_battle(self):
        controller = Mock()
        controller.post_screencap.return_value.wait.return_value.get.return_value = object()
        controller.post_click.return_value.wait.return_value.succeeded = True
        context = SimpleNamespace(tasker=SimpleNamespace(controller=controller, stopping=False))
        arguments = SimpleNamespace(custom_action_param={"role": "窈窕谍影", "variant": "standard", "team": "default"},
                                    task_detail=SimpleNamespace(task_id=1))
        action = SuperstringCombat()
        with patch.object(action, "_fighting", return_value=True):
            self.assertTrue(action.run(context, arguments))
        controller.post_click.assert_called_once_with(1045, 512)
        with patch.object(action, "_fighting", return_value=False):
            self.assertTrue(action.run(context, arguments))
        controller.post_click.assert_called_once()


if __name__ == "__main__":
    unittest.main()
