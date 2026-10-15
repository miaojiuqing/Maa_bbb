"""禁用规则必须高于门优先级、核心评分和商店购买评分。"""
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from agent.custom.action.ElysianRun import ElysianRun, RunHalt
from agent.custom.utils.ElysianPolicy import RunState, choose_gate, gate_order, score_signet, signet_disabled


class DisabledSignetTests(unittest.TestCase):
    def setUp(self):
        self.state = RunState(disabled_families=["鏖灭"], gate_priority=["鏖灭", "螺旋"],
                              buff_priority=["全伤"], exclusive_priority=["鏖兵"])

    def test_all_aomie_names_are_excluded_even_without_family_heading(self):
        names = ("剑锋·剑冢·剑痕", "赤骨·赤血·赤练", "狂信·狂人·狂言",
                 "命路·命舛·命刻", "无妄·无心·无归", "唯神·唯我·唯一",
                 "鏖斗·鏖战·鏖杀·鏖灭", "鏖兵·鏖剪·鏖馘·鏖灭",
                 "非人·非鬼·非神·非天", "一人·一面·一契·一途",
                 "千钧·千转·千难·千劫", "焚身·焚骨·焚心·焚魂",
                 "无死·无生·无灭·无存", "故土·故国·故友·故人")
        for name in names:
            with self.subTest(name=name):
                text = name + "+1 全伤害提高"
                self.assertTrue(signet_disabled(text, self.state))
                self.assertLess(score_signet(text, self.state), 0)
        self.assertTrue(signet_disabled("唯神 唯我 唯—", self.state))
        self.assertTrue(signet_disabled("文字不完整", self.state, "鏖灭"))
        self.assertFalse(signet_disabled("第一幕「魔术」 全伤害提高", self.state))

    def test_blocked_gate_never_wins_even_with_user_priority(self):
        blocked = {"cls_index": 1, "score": .99}
        spiral = {"cls_index": 12, "score": .8}
        self.assertNotIn("鏖灭", gate_order(self.state))
        self.assertIs(choose_gate([blocked, spiral], self.state), spiral)
        self.assertIsNone(choose_gate([blocked], self.state))

    def test_none_preserves_default_policy(self):
        default = RunState()
        self.assertIn("鏖灭", gate_order(default))
        self.assertEqual(score_signet("鏖兵·鏖剪·鏖馘·鏖灭", default), 1500)
        self.assertEqual(score_signet("剑锋·剑冢·剑痕 全伤害提高", default), 300)

    def executor(self):
        run = ElysianRun(threading.Event(), Mock(), Mock(), ".")
        run.state = self.state
        run.context = SimpleNamespace(tasker=SimpleNamespace(stopping=False))
        run.phase = Mock()
        run.save = Mock()
        run.click = Mock(return_value=True)
        run.click_text = Mock(return_value=False)
        run.read = Mock()
        run.choice_signature = ""
        run.choice_at = 0
        run.exclusive_refresh = 0
        return run

    def test_mixed_reward_skips_aomie_and_only_blocked_reward_halts(self):
        run = self.executor()
        rows = [{"text": "剑锋·剑冢·剑痕 全伤害提高", "point": (580, 251)},
                {"text": "宝玉的宣叙 能量上限提高", "point": (580, 404)}]
        run.items, run.text = [], "请选择刻印"
        root = Path(__file__).resolve().parents[1] / "debug"
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            run.output = Path(temporary)
            with patch("agent.custom.action.ElysianRun.choice_rows", return_value=rows):
                run.select_signet()
        run.click.assert_called_once_with(580, 404, delay=.3)
        run.click.reset_mock()
        run.text = "鏖灭的刻印"
        with patch("agent.custom.action.ElysianRun.choice_rows", return_value=rows):
            with self.assertRaisesRegex(RunHalt, "禁用刻印"):
                run.select_signet()
        run.click.assert_not_called()

    def test_shop_never_purchases_blocked_high_score_item(self):
        run = self.executor()
        run.items = [{"text": "1000", "box": [1190, 10, 40, 25]}]
        run.shop_pending = None
        run.shop_seen = set()
        run.shop_scrolls = 0
        run.swipe = Mock()
        row = {"title": "鏖兵·鏖剪·鏖馘·鏖灭", "text": "鏖兵·鏖剪·鏖馘·鏖灭", "price": 200, "y": 250}
        with patch("agent.custom.action.ElysianRun.shop_rows", return_value=[row]):
            run.shop()
        run.click.assert_not_called()
        run.click_text.assert_not_called()

    def test_blocked_gate_prompt_never_clicks_or_walks_towards_it(self):
        run = self.executor()
        run.items = [{"text": "前往", "box": [700, 273, 60, 24]},
                     {"text": "后获得「鏖灭」的刻印", "box": [38, 336, 182, 22]}]
        run.text = "前往后获得鏖灭的刻印"
        run.nav_started = 100
        run.state.target = "鏖灭"
        run.target = {"cls_index": 1, "score": .99, "box": [600, 150, 200, 400]}
        run.detect_gates = Mock(return_value=[run.target])
        run.motion.walk = Mock()
        run.swipe = Mock()
        run.enter_attempts = run.lost_frames = run.nav_steps = run.turns = run.nav_recoveries = 0
        run.gate_pause_used = run.final_clear = run.shop_done = False
        run.frame_target = None
        with patch("agent.custom.action.ElysianRun.time.monotonic", return_value=101):
            run.navigate()
        run.click.assert_not_called()
        run.motion.walk.assert_not_called()
        run.swipe.assert_called_once()  # 转动视角寻找其他门。


if __name__ == "__main__":
    unittest.main()
