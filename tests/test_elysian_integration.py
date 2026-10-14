"""用真实 Maa 资源验证任务选项、关内交接和出招表打包，不连接游戏。"""

import importlib.util
import json
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import jsonc
from maa.resource import Resource
from maa.tasker import LoggingLevelEnum, Tasker

from agent.custom.action.ElysianIntegration import ElysianConfigure, read_settings


ROOT = Path(__file__).resolve().parents[1]
Tasker.set_stdout_level(LoggingLevelEnum.Off)


class ResourceContext:
    def __init__(self, resource):
        self.resource = resource

    def get_node_data(self, name):
        return self.resource.get_node_data(name)

    def override_pipeline(self, patch):
        return self.resource.override_pipeline(patch)


class ElysianIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.resource = Resource()
        self.assertTrue(
            self.resource.post_bundle(ROOT / "assets/resource/base").wait().status.succeeded
        )
        self.context = ResourceContext(self.resource)
        self.options = jsonc.loads(
            (ROOT / "assets/tasks/周常/往世乐土.json").read_text(encoding="utf-8")
        )["option"]

    def apply_case(self, option, case):
        selected = next(c for c in self.options[option]["cases"] if c["name"] == case)
        self.assertTrue(self.resource.override_pipeline(selected.get("pipeline_override", {})))

    def defaults(self):
        self.apply_case("往世乐土-关内角色", "窈窕谍影")
        self.apply_case("往世乐土-关内流派", "华裳")
        self.apply_case("往世乐土-商店处理策略-安卓", "自动购买")
        self.apply_case("往世乐土-刻印优先级自选", "No")
        self.apply_case("往世乐土-门的选择优先级", "No")
        # 模拟前端将留空的真我刻印输入展开为空字符串。
        input_override = self.options["往世乐土-真我刻印自选"]["pipeline_override"]
        self.assertTrue(self.resource.override_pipeline(json.loads(
            json.dumps(input_override).replace("{真我刻印自选优先级_1}", "")
        )))

    def test_defaults_reach_runtime(self):
        self.defaults()
        result = read_settings(self.context)
        self.assertEqual((result["role"], result["variant"]), ("窈窕谍影", "elysian_huashang"))
        self.assertTrue(result["shop_enabled"])
        for key in ("exclusive_priority", "buff_priority", "gate_priority"):
            self.assertEqual(result[key], [])
        self.assertEqual(result["disabled_families"], [])

    def test_disabled_signet_option_is_last_and_reaches_stage(self):
        document = jsonc.loads((ROOT / "assets/tasks/周常/往世乐土.json").read_text(encoding="utf-8"))
        self.assertEqual(document["task"][0]["option"][-1], "往世乐土-禁用刻印")
        self.assertEqual(self.options["往世乐土-禁用刻印"]["default_case"], "无")
        self.defaults()
        self.apply_case("往世乐土-禁用刻印", "鏖灭")
        self.assertTrue(ElysianConfigure().run(self.context, None))
        parameters = self.resource.get_node_data("乐土关内-接管")["action"]["param"]["custom_action_param"]
        self.assertEqual(parameters["disabled_families"], ["鏖灭"])
        self.apply_case("往世乐土-禁用刻印", "无")
        self.assertEqual(read_settings(self.context)["disabled_families"], [])

    def test_prebattle_switch_routes_sync_with_each_target(self):
        self.defaults()
        self.apply_case("往世乐土-战前增益选择", "Yes")
        targets = [True, False, True, False, True, False, False]
        for index, desired in enumerate(targets, 1):
            self.apply_case(f"乐土-战前buff-{index}", "Yes" if desired else "No")
        self.assertTrue(ElysianConfigure().run(self.context, None))
        sync = self.resource.get_node_data("乐土战前-同步增益")
        self.assertTrue(sync["enabled"])
        self.assertEqual(sync["action"]["param"]["custom_action_param"]["targets"], targets)
        next_nodes = [item["name"] for item in self.resource.get_node_data("往世乐土-已进入深层序列")["next"]]
        self.assertEqual(next_nodes[0], "乐土战前-同步增益")
        self.assertNotIn("往世乐土-未选择任何增益", next_nodes)
        self.apply_case("往世乐土-战前增益选择", "No")
        self.assertTrue(ElysianConfigure().run(self.context, None))
        self.assertFalse(self.resource.get_node_data("乐土战前-同步增益")["enabled"])
        self.assertEqual(self.resource.get_node_data("往世乐土-已进入深层序列")["next"][0]["name"], "往世乐土-未选择任何增益")

    def test_custom_priorities_and_shop_reach_runtime(self):
        self.defaults()
        self.apply_case("往世乐土-商店处理策略-安卓", "绕过不购买")
        self.apply_case("往世乐土-刻印优先级自选", "Yes")
        self.apply_case("往世乐土-门的选择优先级", "Yes")
        for priority in range(3, 11):
            self.apply_case(f"乐土-道中刻印优先级_{priority}", f"乐土-道中刻印优先级{priority}_不启用")
            self.apply_case(f"乐土-选门优先级_{priority}", f"乐土选门优先级-{priority}-不选")
        self.apply_case("乐土-道中刻印优先级_1", "乐土-道中刻印优先级1_全伤")
        self.apply_case("乐土-道中刻印优先级_2", "乐土-道中刻印优先级2_易伤")
        self.apply_case("乐土-选门优先级_1", "乐土选门优先级-1-空梦")
        self.apply_case("乐土-选门优先级_2", "乐土选门优先级-2-真我")
        self.resource.override_pipeline({
            "往世乐土-选刻印-真我刻印选择": {"expected": ["华裳|尽善"]}
        })
        result = read_settings(self.context)
        self.assertFalse(result["shop_enabled"])
        self.assertEqual(result["exclusive_priority"], ["华裳", "尽善"])
        self.assertEqual(result["buff_priority"], ["全伤", "易伤"])
        self.assertEqual(result["gate_priority"], ["空梦", "真我"])

    def test_configure_hands_off_to_stage_executor(self):
        self.defaults()
        self.assertTrue(ElysianConfigure().run(self.context, None))
        stage = self.resource.get_node_data("乐土关内-接管")
        self.assertTrue(stage["enabled"])
        self.assertEqual(stage["action"]["param"]["custom_action"], "ElysianStage")
        self.assertEqual(stage["action"]["param"]["custom_action_param"]["role"], "窈窕谍影")
        self.assertEqual(
            [item["name"] for item in self.resource.get_node_data("往事乐土-乐土开始了")["next"]],
            ["乐土关内-接管"],
        )

    def test_desktop_keeps_original_flow(self):
        before = self.resource.get_node_data("往事乐土-乐土开始了")
        self.assertTrue(ElysianConfigure().run(self.context, None))
        self.assertFalse(self.resource.get_node_data("乐土关内-接管")["enabled"])
        self.assertEqual(self.resource.get_node_data("往事乐土-乐土开始了"), before)

    def test_build_includes_and_loads_character_profile(self):
        sys.path.insert(0, str(ROOT / "tools"))
        try:
            with patch.object(sys, "argv", ["install.py", "local-test", "win", "x64"]):
                namespace = runpy.run_path(str(ROOT / "tools/install.py"), run_name="install_test")
        finally:
            sys.path.pop(0)
        (ROOT / "debug").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "debug") as temporary:
            package = Path(temporary).resolve()
            self.assertTrue(package.is_relative_to(ROOT / "debug"))
            (package / "interface.json").write_text(json.dumps({"agent": {}}), encoding="utf-8")
            namespace["install_agent"].__globals__["install_path"] = package
            namespace["install_agent"]()
            self.assertTrue((package / "characters/rita_elysian_huashang.json").is_file())
            spec = importlib.util.spec_from_file_location(
                "packaged_profiles", package / "agent/custom/utils/CharacterProfiles.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertIn("elysian_huashang", module.CHARACTER_PROFILES["窈窕谍影"]["variants"])


if __name__ == "__main__":
    unittest.main()
