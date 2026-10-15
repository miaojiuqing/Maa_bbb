"""验证旧增益同步、取消优先、状态复核和无效点击的有界退出。"""
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from agent.custom.action.ElysianBuffSync import BUFF_ROWS, ElysianBuffSync, rows_match


class BuffSyncTests(unittest.TestCase):
    def action(self, states):
        action = ElysianBuffSync()
        action.context = SimpleNamespace(tasker=SimpleNamespace(stopping=False))
        action.states = list(states)
        action.logger = Mock()
        action.delay = threading.Event()
        action.edge = Mock()
        action.row_state = Mock(side_effect=lambda index: (action.states[index], (index, 100)))
        action.capture = Mock(return_value=object())
        action.hit = Mock(return_value=None)
        action.wait = Mock()
        controller = Mock()

        def click(index, y):
            action.states[index] = not action.states[index]
            return SimpleNamespace(wait=lambda: SimpleNamespace(succeeded=True))

        controller.post_click.side_effect = click
        action.context.tasker.controller = controller
        return action

    def test_old_week_selections_are_cancelled_before_adding_any_new_one(self):
        action = self.action([False, True, True, False, True, False, True])
        targets = [True, False, True, True, False, False, True]
        action.sync(targets)
        self.assertEqual(action.states, targets)
        self.assertEqual([call.args[0] for call in action.context.tasker.controller.post_click.call_args_list], [1, 4, 0, 3])
        # 第3、6、7条原本一致，保持不点。
        self.assertEqual(action.context.tasker.controller.post_click.call_count, 4)

    def test_matching_selection_and_all_off_do_not_reenable_old_buffs(self):
        for states in ([True, False, True, False, True, False, False], [False] * 7):
            action = self.action(states)
            action.sync(states)
            action.context.tasker.controller.post_click.assert_not_called()
        action = self.action([True] * 7)
        action.sync([False] * 7)
        self.assertEqual(action.states, [False] * 7)

    def test_no_effect_clicks_stop_after_two_attempts(self):
        action = self.action([False] * 7)
        action.context.tasker.controller.post_click.side_effect = None
        action.context.tasker.controller.post_click.return_value.wait.return_value.succeeded = True
        with self.assertRaisesRegex(RuntimeError, "无法选中"):
            action.set_row(0, True)
        self.assertEqual(action.context.tasker.controller.post_click.call_count, 2)

    def test_load_limit_or_user_stop_never_continues_to_other_choices(self):
        action = self.action([False] * 7)
        action.hit.return_value = object()
        with self.assertRaisesRegex(RuntimeError, "负荷上限"):
            action.sync([True] * 7)
        self.assertEqual(action.context.tasker.controller.post_click.call_count, 1)
        action = self.action([False] * 7)
        action.context.tasker.stopping = True
        with self.assertRaisesRegex(RuntimeError, "用户停止"):
            action.set_row(0, True)
        action.context.tasker.controller.post_click.assert_not_called()

    def test_final_verification_detects_mutually_exclusive_or_changed_choice(self):
        action = self.action([True] * 7)
        reads = 0

        def state(index):
            nonlocal reads
            reads += 1
            return (False if reads > 7 and index == 0 else True), (index, 100)

        action.row_state.side_effect = state
        with self.assertRaisesRegex(RuntimeError, "最终状态"):
            action.sync([True] * 7)

    def test_missing_row_does_not_mean_unchecked(self):
        action = ElysianBuffSync()
        action.context = Mock()
        action.capture = Mock(return_value=object())
        action.hit = Mock(return_value=None)
        with self.assertRaisesRegex(RuntimeError, "无法可靠定位"):
            action.row_state(0)

    def test_checkbox_roi_fits_whole_template_without_changing_disabled_original(self):
        action = ElysianBuffSync()
        action.context = Mock()
        action.capture = Mock(return_value=object())
        action.row_y = Mock(return_value=330)
        action.hit = Mock(return_value=object())
        selected, point = action.row_state(0)
        self.assertTrue(selected)
        self.assertEqual(point, (1186, 330))
        action.context.override_pipeline.assert_not_called()
        scratch = action.hit.call_args.args[2]["乐土战前-勾选检测"]
        self.assertEqual(scratch["recognition"]["param"]["roi"], [1155, 300, 65, 60])
        # 实际模板高31像素，旧ROI高30导致选中恒判为未选。
        self.assertGreaterEqual(scratch["recognition"]["param"]["roi"][3], 31)

    def test_scroll_is_bounded_and_success_marker_only_written_on_success(self):
        action = ElysianBuffSync()
        action.context = Mock()
        action.context.tasker.stopping = False
        action.capture = Mock(return_value=object())
        action.hit = Mock(return_value=None)
        action.wait = Mock()
        with self.assertRaisesRegex(RuntimeError, "无法确认"):
            action.edge(True)
        self.assertEqual(action.context.run_action.call_count, 12)
        for call in action.context.run_action.call_args_list:
            swipe = call.kwargs["pipeline_override"]["乐土战前-条目检测"]["action"]["param"]
            self.assertEqual(swipe["end_hold"],500)
            self.assertGreater(swipe["begin"][1],swipe["end"][1])
        action.context.tasker.controller.post_click.assert_not_called()
        for success in (True, False):
            context = Mock()
            context.tasker.stopping = False
            context.override_pipeline.return_value = True
            action = ElysianBuffSync()
            action.sync = Mock(side_effect=None if success else RuntimeError("识别失败"))
            with patch("agent.custom.action.ElysianBuffSync.Logger"):
                self.assertEqual(action.run(context, SimpleNamespace(custom_action_param={"targets": [False]*7})), success)
            if success:
                context.override_pipeline.assert_called_once_with({"乐土战前-同步增益": {"enabled": False}})
            else:
                context.override_pipeline.assert_not_called()

    def test_buff_start_searches_back_from_bottom_without_old_top_icon(self):
        action = ElysianBuffSync()
        action.context = Mock()
        action.context.tasker.stopping = False
        action.capture = Mock(return_value=object())
        action.logger = Mock()
        action.wait = Mock()
        action.hit = Mock(return_value=object())
        action.cost_rows = Mock(side_effect=[[], [(0,330),(5,391),(5,452)]])
        action.edge(True)
        names = [call.args[0] for call in action.hit.call_args_list]
        self.assertEqual(names, ["往世乐土-增益选择-已滑动至最下方"])
        swipe = action.context.run_action.call_args.kwargs["pipeline_override"]["乐土战前-条目检测"]["action"]["param"]
        self.assertEqual(swipe["end"], [95,510,1,1])
        self.assertEqual(swipe["end_hold"], 500)
        action.context.tasker.controller.post_click.assert_not_called()

    def test_buff_start_realigns_first_row_and_rejects_duplicate_rows(self):
        action = ElysianBuffSync()
        action.context = Mock()
        action.context.tasker.stopping = False
        action.capture = Mock(return_value=object())
        action.logger = Mock()
        action.wait = Mock()
        action.hit = Mock(return_value=object())
        action.cost_rows = Mock(side_effect=[[(0,200),(5,261),(5,322)], [(0,330),(5,391),(5,391)]])
        with self.assertRaisesRegex(RuntimeError, "第二、第三条"):
            action.edge(True)
        self.assertEqual(action.context.run_action.call_count, 1)
        action.context.tasker.controller.post_click.assert_not_called()

    def test_buff_start_missing_first_row_has_bounded_scroll_and_no_clicks(self):
        action = ElysianBuffSync()
        action.context = Mock()
        action.context.tasker.stopping = False
        action.capture = Mock(return_value=object())
        action.hit = Mock(return_value=object())
        action.cost_rows = Mock(return_value=[])
        action.wait = Mock()
        with self.assertRaisesRegex(RuntimeError, "无法定位.*第一条"):
            action.edge(True)
        self.assertEqual(action.context.run_action.call_count, 12)
        action.context.tasker.controller.post_click.assert_not_called()

    def test_complete_cost_digits_and_order_distinguish_duplicate_prices(self):
        action = ElysianBuffSync()
        action.context = Mock()
        items = [SimpleNamespace(text=text, box=[80,y,55,32])
                 for text,y in (("5",428),("0",308),("5",368),("10",510))]
        action.hit = Mock(return_value=SimpleNamespace(filtered_results=items))
        frame = object()
        self.assertEqual(action.cost_rows(frame), [(0,324),(5,384),(5,444)])
        self.assertEqual(action.row_y(1,frame),384)
        self.assertEqual(action.row_y(2,frame),444)
        action.hit.return_value.filtered_results = items[:1]
        with self.assertRaisesRegex(RuntimeError,"无法可靠定位"):
            action.row_y(0,frame)

    def test_bottom_positions_require_last_four_costs_and_bottom_marker(self):
        action = ElysianBuffSync()
        action.cost_rows = Mock(return_value=[(5,180),(5,241),(10,303),(10,364),(15,425),(15,485)])
        action.hit = Mock(return_value=object())
        self.assertEqual(action.row_y(3,object()),303)
        self.assertEqual(action.row_y(4,object()),364)
        self.assertEqual(action.row_y(5,object()),425)
        self.assertEqual(action.row_y(6,object()),485)
        action.hit.return_value = None
        with self.assertRaisesRegex(RuntimeError,"未到底部"):
            action.row_y(3,object())
        self.assertFalse(rows_match([(0,330),(5,391),(5,391)],(0,5,5)))
        self.assertFalse(rows_match([(0,330),(5,350),(5,391)],(0,5,5)))


if __name__ == "__main__":
    unittest.main()
