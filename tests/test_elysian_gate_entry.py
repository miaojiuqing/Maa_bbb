"""验证门前点击无效时恢复，并确保加载期间不会追加输入。"""
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from agent.custom.action.ElysianRun import ElysianRun, RunHalt


def gate_items(floor=14, family="浮生"):
    # 取自第14层卡门现场的 OCR 几何信息，不依赖本机日志路径。
    return [
        {"text": f"抵达层数-{floor}/17", "box": [94, 10, 118, 25]},
        {"text": f"后获得「{family}」的刻印", "box": [38, 336, 182, 22]},
        {"text": "日前往", "box": [700, 273, 60, 24]},
    ]


class GateEntryTests(unittest.TestCase):
    def setUp(self):
        self.run = ElysianRun(threading.Event(), Mock(), Mock(), ".")
        self.run.context = SimpleNamespace(tasker=SimpleNamespace(stopping=False))
        self.run.state.floor, self.run.state.total = 14, 17
        self.run.state.target = "浮生"
        self.run.items = gate_items()
        self.run.enter_pending, self.run.enter_at = 14, 100
        self.run.enter_attempts, self.run.enter_failure_reads = 1, 0
        self.run.phase = Mock()
        self.run.save = Mock()
        self.run.click = Mock(return_value=True)
        self.run.motion.walk = Mock()
        self.run.nav_started = 99
        self.run.final_clear = False
        self.run.text = ""
        self.run.gate_pause_used = False
        self.run.gate_recovery_phase = None
        self.run.gate_recovery_at = 0
        self.run.arena = Mock(return_value=True)

    def wait_at(self, now):
        with patch("agent.custom.action.ElysianRun.time.monotonic", return_value=now):
            return self.run.wait_gate_entry()

    def test_same_gate_requires_two_observations_before_retry(self):
        self.assertTrue(self.wait_at(102))
        self.assertEqual(self.run.enter_failure_reads, 0)
        self.assertTrue(self.wait_at(104))
        self.assertEqual(self.run.enter_pending, 14)
        self.assertTrue(self.wait_at(105))
        self.assertIsNone(self.run.enter_pending)
        self.run.motion.walk.assert_not_called()
        # 下一帧重新识别，重试使用另一位置，不会原地盲等20秒。
        with patch("agent.custom.action.ElysianRun.time.monotonic", return_value=106):
            self.run.navigate()
        self.run.click.assert_called_once_with(730.0, 285.0, 1.2)
        self.assertEqual(self.run.enter_pending, 14)

    def test_first_click_uses_inside_of_interaction_bar(self):
        self.run.enter_pending = None
        self.run.enter_attempts = 0
        with patch("agent.custom.action.ElysianRun.time.monotonic", return_value=104):
            self.run.navigate()
        self.run.click.assert_called_once_with(810.0, 285.0, 1.2)
        self.assertEqual(self.run.enter_attempts, 1)

    def test_loading_and_unconfirmed_new_floor_never_move_or_click(self):
        for items in ([], gate_items(floor=15), gate_items(family="天慧")):
            self.run.items = items
            self.assertTrue(self.wait_at(115))
            self.assertEqual(self.run.enter_pending, 14)
            self.assertEqual(self.run.enter_failure_reads, 0)
        self.run.motion.walk.assert_not_called()
        self.run.click.assert_not_called()

    def test_three_failed_clicks_reposition_once_then_reobserve(self):
        self.run.enter_attempts = 3
        self.assertTrue(self.wait_at(104))
        self.assertTrue(self.wait_at(105))
        self.run.motion.walk.assert_called_once_with(self.run.context, 0, .25, dy=76)
        self.run.click.assert_not_called()
        self.assertFalse(self.wait_at(106))
        self.assertEqual(self.run.motion.walk.call_count, 1)

    def test_confirmed_floor_change_clears_pending_and_attempts(self):
        self.run.items = gate_items(floor=15)
        self.run.floor_candidate = None
        self.run.final_gate_clicked = False
        self.run.update_floor()
        self.assertEqual(self.run.enter_pending, 14)
        self.run.update_floor()
        self.assertEqual(self.run.state.floor, 15)
        self.assertIsNone(self.run.enter_pending)
        self.assertEqual(self.run.enter_attempts, 0)

    def test_timeout_and_retry_limit_stop_instead_of_unbounded_input(self):
        self.run.items = []
        with self.assertRaises(RunHalt):
            self.wait_at(131)
        self.run.items = gate_items()
        self.run.enter_pending = None
        self.run.gate_pause_used = True
        self.run.enter_attempts = 3
        with patch("agent.custom.action.ElysianRun.time.monotonic", return_value=106):
            with self.assertRaises(RunHalt):
                self.run.navigate()
        self.run.click.assert_not_called()

    def test_failed_clicks_pause_resume_and_allow_only_three_more_attempts(self):
        self.run.enter_pending = None
        self.run.enter_attempts = 6
        with patch("agent.custom.action.ElysianRun.time.monotonic", return_value=106):
            self.run.navigate()
        self.assertTrue(self.run.gate_pause_used)
        self.assertEqual(self.run.gate_recovery_phase, "pause")
        self.run.click.assert_called_once_with(43, 36, .5)
        self.run.click.reset_mock()
        # 暂停未确认时不能盲点继续或追加门前输入。
        with patch("agent.custom.action.ElysianRun.time.monotonic", return_value=107):
            self.assertTrue(self.run.recover_gate_pause())
        self.run.click.assert_not_called()
        self.run.text = "往世乐土战况报告状态列表继续战斗"
        self.run.items = [{"text": "继续战斗", "box": [930, 635, 160, 40]}]
        with patch("agent.custom.action.ElysianRun.time.monotonic", return_value=108):
            self.assertTrue(self.run.recover_gate_pause())
        self.run.click.assert_called_once_with(1010.0, 655.0, .6)
        self.assertEqual(self.run.gate_recovery_phase, "resume")
        self.run.click.reset_mock()
        self.run.items = gate_items()
        self.run.text = "抵达层数14/17前往浮生"
        with patch("agent.custom.action.ElysianRun.time.monotonic", return_value=109):
            self.assertTrue(self.run.recover_gate_pause())
        self.assertIsNone(self.run.gate_recovery_phase)
        self.assertEqual(self.run.enter_attempts, 0)
        self.run.click.assert_not_called()
        for attempt in range(1, 4):
            with patch("agent.custom.action.ElysianRun.time.monotonic", return_value=110 + attempt):
                self.run.navigate()
            self.assertEqual(self.run.enter_attempts, attempt)
            self.run.enter_pending = None
        with patch("agent.custom.action.ElysianRun.time.monotonic", return_value=115):
            with self.assertRaisesRegex(RunHalt, "暂停并继续"):
                self.run.navigate()
        self.assertEqual(self.run.click.call_count, 3)

    def test_pause_recovery_times_out_or_respects_user_stop(self):
        self.run.gate_recovery_phase = "pause"
        self.run.gate_recovery_at = 100
        for phase in ("pause", "resume"):
            self.run.gate_recovery_phase = phase
            self.run.arena.return_value = False
            with patch("agent.custom.action.ElysianRun.time.monotonic", return_value=111):
                with self.assertRaises(RunHalt):
                    self.run.recover_gate_pause()
        self.run.context.tasker.stopping = True
        self.assertTrue(self.run.recover_gate_pause())
        self.run.click.assert_not_called()

    def test_door_timeout_uses_pause_recovery_once_and_next_floor_resets_it(self):
        with patch("agent.custom.action.ElysianRun.time.monotonic", return_value=201):
            self.run.navigate()
        self.assertTrue(self.run.gate_pause_used)
        with patch("agent.custom.action.ElysianRun.time.monotonic", return_value=202):
            with self.assertRaisesRegex(RunHalt, "100 秒"):
                self.run.navigate()
        self.run.items = gate_items(floor=15)
        self.run.floor_candidate = None
        self.run.final_gate_clicked = False
        self.run.update_floor()
        self.run.update_floor()
        self.assertFalse(self.run.gate_pause_used)
        self.assertIsNone(self.run.gate_recovery_phase)


if __name__ == "__main__":
    unittest.main()
