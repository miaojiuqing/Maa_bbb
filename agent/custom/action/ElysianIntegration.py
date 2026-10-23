"""原往世乐土任务与关内执行器的连接；复用宿主 Context，不创建控制器。"""
import json
import re
from pathlib import Path

from maa.custom_action import CustomAction
from maa.custom_recognition import CustomRecognition

from .ElysianRun import AssistantElysianRun, RunHalt
from .ElysianBuffSync import read_buff_targets
from ..utils.CharacterProfiles import CHARACTER_PROFILES
from ..utils.ElysianPolicy import DISABLABLE_FAMILIES, GATE_NAMES, normalize, read_floor
from ..utils.Logger import Logger


def parameters(node, section="action"):
    """兼容 Maa 返回的规范化节点和磁盘上的简写节点。"""
    node = node or {}
    value = node.get(section)
    return value.get("param", {}) if isinstance(value, dict) else node


def setting(context, name):
    value = parameters(context.get_node_data(name)).get("custom_action_param", {})
    return json.loads(value) if isinstance(value, str) else value


def action_parameters(argv):
    """读自定义动作本次收到的参数；缺失或非法时返回空字典。"""
    raw = getattr(argv, "custom_action_param", None)
    if isinstance(raw, str):
        try:
            value = json.loads(raw or "{}")
        except json.JSONDecodeError:
            return {}
    else:
        value = raw or {}
    return value if isinstance(value, dict) else {}


# 刷级链在“女武神准备出击界面”的 next 里把刻印选择排在接管前面，出击进入第一层后
# 它会先抢走初始专属刻印，所以交棒与接管都必须把 乐土关内-接管 插到这些列表最前面。
HANDOVER_NODES = (
    "乐土刷级-首层复刷-已进入女武神选择界面",
    "乐土刷级-浅层序列-已进入女武神准备战斗界面",
    "乐土刷级-减负模式-已进入女武神选择界面",
)


def node_next(context, name):
    """读取节点当前的 next；节点不存在或没有 next 时返回空列表。"""
    value = (context.get_node_data(name) or {}).get("next")
    return list(value) if isinstance(value, list) else []


def handover_patch(context, stop):
    """把 乐土关内-接管 插入出击链路最前。

    识别用的是关内接管自带的 ElysianInStage：准备界面与加载画面不命中，出击进入
    第一层（楼层 HUD、初始刻印页、对话、暂停页）才命中，因此不会抢走出击本身。
    stop=True 时命中即结束本任务，把控制权交给紧随其后的往世乐土任务。
    """
    patch = {}
    for name in HANDOVER_NODES:
        current = node_next(context, name)
        if current and "乐土关内-接管" not in current:
            patch[name] = {"next": ["乐土关内-接管"] + current}
    if stop:
        patch["乐土关内-接管"] = {
            "enabled": True,
            "action": "DoNothing",
            "focus": {"Node.Recognition.Succeeded": "已进入第一层，交棒给「往世乐土」任务接管"},
            "next": [],
        }
    return patch


def read_settings(context):
    role = setting(context, "乐土关内-角色配置")
    character = role.get("character", "窈窕谍影")
    variant = role.get("variant", "elysian_huashang")
    if variant not in CHARACTER_PROFILES.get(character, {}).get("variants", {}):
        raise ValueError("所选角色或流派尚未适配")
    result = {"role": character, "variant": variant,
              "shop_enabled": bool(setting(context, "乐土关内-商店配置").get("buy", False)),
              "exclusive_priority": [], "buff_priority": [], "gate_priority": []}
    disabled = setting(context, "乐土关内-禁用刻印配置").get("disabled", [])
    if not isinstance(disabled, list) or any(name not in DISABLABLE_FAMILIES for name in disabled):
        raise ValueError("禁用刻印设置无效")
    result["disabled_families"] = list(dict.fromkeys(disabled))
    expected = parameters(context.get_node_data("往世乐土-选刻印-真我刻印选择"), "recognition").get("expected", [])
    if isinstance(expected, str):
        expected = [expected]
    for item in expected:
        # 空值和未展开的 UI 占位符不是用户选择。
        if not item or "{" in item:
            continue
        for pattern in item.split("|"):
            if pattern.strip():
                re.compile(pattern.strip())
                result["exclusive_priority"].append(pattern.strip())
    if setting(context, "乐土关内-刻印配置").get("custom", False):
        for i in range(1, 11):
            node = context.get_node_data(f"往世乐土-选刻印-刻印选择-优先级_{i}") or {}
            if not node.get("enabled", True):
                continue
            templates = parameters(node, "recognition").get("template", [])
            if isinstance(templates, str):
                templates = [templates]
            for template in templates:
                category = Path(template.replace("\\", "/")).stem.removesuffix("_2")
                if category not in result["buff_priority"]:
                    result["buff_priority"].append(category)
    if setting(context, "乐土关内-选门配置").get("custom", False):
        for i in range(1, 11):
            node = context.get_node_data(f"往世乐土-寻路-选择门-优先级_{i}") or {}
            if not node.get("enabled", True):
                continue
            for label in parameters(node, "recognition").get("expected", []):
                family = GATE_NAMES.get(label)
                if family and family not in result["gate_priority"]:
                    result["gate_priority"].append(family)
    return result


class ElysianConfigure(CustomAction):
    def run(self, context, argv):
        try:
            params = action_parameters(argv)
            # 交棒模式：克莱茵打灰只负责走到准备界面并出击，进入第一层立刻结束本任务，
            # 由紧随其后的往世乐土任务带着它自己的完整关内配置接管初始专属刻印。
            # 只能由任务选项显式开启，默认不会走到这里。
            if params.get("handoff"):
                patch = handover_patch(context, stop=True)
                # 接口层同时是每打完一把回跳的中转节点，装好之后不再重复覆盖与刷屏。
                hooked = [name for name in patch if name != "乐土关内-接管"]
                if not hooked:
                    return True
                ok = context.override_pipeline(patch)
                if ok:
                    print(f"乐土交棒配置：已在 {hooked} 最前面插入接棒节点，"
                          f"出击进入第一层后结束本任务，交给往世乐土任务接管", flush=True)
                return ok
            enabled = bool((context.get_node_data("乐土关内-角色配置") or {}).get("enabled", False))
            # 所有覆盖仅属于当前任务；桌面端保持原流程。
            if not enabled:
                return True
            config = read_settings(context)
            patch = {"乐土关内-接管": {"enabled": True,
                     "action": {"type": "Custom", "param": {
                         "custom_action": "ElysianStage", "custom_action_param": config}}}}
            # 小助手原版的“真我刻印选择”是可选 OCR 节点。安卓端留空时，
            # Maa 会把空字符串当成“匹配任意 OCR 文本”，战斗 HUD 的数字也会
            # 被当成刻印并反复点击，导致流程永远进不了战斗。关内接管已经
            # 自己处理初始专属和后续刻印，因此从原版入口链移除这两个可选节点。
            # 只改当前任务的运行时覆盖，磁盘上的原版节点仍保留给桌面端/旧流程。
            # 进入第一层后由关内自循环独占画面。原版入口节点仍负责舰桥、
            # 乐土大厅、深层序列和战前配置；一旦识别到第一层初始刻印页，
            # 不再继续执行原版的刻印/领奖/跳转节点，避免同一帧与自循环抢输入。
            patch["往事乐土-乐土开始了"] = {"next": ["乐土关内-接管"]}
            # 任务中断或小助手重启后，画面可能已经停在深层序列的
            # 战前增益页。原入口链只从“已进入往世乐土”继续向下，
            # 这时会漏掉增益节点并反复回到“启动并进入游戏”。
            # 将深层序列识别加入入口恢复分支，沿用原版增益选择流程。
            patch["往世乐土-开始任务层"] = {
                "next": [
                    "往世乐土-总任务层",
                    "往世乐土-已进入往世乐土",
                    "往世乐土-已进入三位导航界面",
                    "往世乐土-已进入深层序列",
                    "乐土关内-接管",
                    "[JumpBack]启动并进入游戏",
                ]
            }
            # MuMu 当前 1600x900 显示映射到 1280x720 逻辑分辨率时，
            # 滚动条到底部的色块实际只有约 16 个连续像素；原版要求 30，
            # 导致“已滑动至最下方”永远识别失败并无限向下滑动。
            # 只覆盖本次安卓自定义任务，桌面端仍使用原始阈值。
            patch["往世乐土-增益选择-已滑动至最下方"] = {
                "recognition": {
                    "type": "ColorMatch",
                    "param": {
                        "roi": [1230, 509, 12, 20],
                        "upper": [159, 131, 86],
                        "lower": [159, 131, 86],
                        "count": 12,
                        "connected": True,
                    },
                }
            }
            # 入场及领奖流程复用原识别节点，安卓不发送 PC 的 Alt/Space/Esc。
            patch.update({
                # MuMu 上“跳过”图标由原节点识别为 [1182, 15, 36, 29]；
                # 直接点击其中心，避免 ClickKey/空格在对话阶段失效。
                "往世乐土-等爱莉说话": {
                    "action": {"type": "Click", "param": {"target": [1200, 30, 1, 1]}}
                },
                "往世乐土-战斗-对话ing": {
                    "action": {"type": "Click", "param": {"target": [1200, 30, 1, 1]}}
                },
                "往世乐土-打完领奖-按住alt后点击进入-按住": {"action": "DoNothing"},
                "往世乐土-打完领奖-已进入领奖入口": {"action": "DoNothing"},
                "往世乐土-打完领奖-重置鼠标状态": {"action": "DoNothing"},
                "往世乐土-打完领奖-领完奖点返回": {"action": {"type": "Click", "param": {"target": [42, 30, 1, 1]}}},
                "往世乐土-已进入深层序列": {"focus": {"Node.Recognition.Succeeded": "进入深层序列，沿用原战前准备流程"}},
            })
            sync_buffs = bool(setting(context, "乐土战前-同步配置").get("enabled", False))
            patch["乐土战前-同步增益"] = {
                "enabled": sync_buffs,
                "action": {"type": "Custom", "param": {
                    "custom_action": "ElysianBuffSync",
                    "custom_action_param": {"targets": read_buff_targets(context)}
                }}
            }
            # 开启时始终同步，即使游戏保留了上一周的选择；关闭时保留原入口。
            patch["往世乐土-已进入深层序列"]["next"] = [
                "乐土战前-同步增益" if sync_buffs else "往世乐土-未选择任何增益",
                "往世乐土-已进入三位导航界面",
                # 减负战斗优先；按钮不可用（模板不匹配）时自动落到下面的普通战斗。
                "[JumpBack]往世乐土-点击减负战斗",
                "[JumpBack]往世乐土-点击普通战斗",
            ]
            # 预置交棒：HANDOVER_NODES 里的三个准备界面节点属于「克莱茵打灰」的
            # 刷装甲等级链路，往世乐土任务走的是乐土导航入口链，本任务内不会命中
            # 它们；这段覆盖当前不产生实际效果，保留为后续让往世乐土直接复用
            # 刷级链路时的接棒预留。
            handover = handover_patch(context, stop=False)
            patch.update(handover)
            ok = context.override_pipeline(patch)
            if ok:
                print(f"乐土关内配置：{json.dumps(config, ensure_ascii=False)}", flush=True)
                if handover:
                    print(f"乐土交棒预置：已为 {list(handover)} 预留接棒插入（本任务不经过刷级链路）", flush=True)
            return ok
        except Exception as exc:
            print(f"乐土配置读取失败：{exc}", flush=True)
            return False


class ElysianInStage(CustomRecognition):
    def analyze(self, context, argv):
        try:
            result = context.run_recognition("乐土自动-OCR", argv.image)
            rows = [{"text": r.text, "box": list(r.box)} for r in result.all_results] if result and result.hit else []
            text = normalize("".join(r["text"] for r in rows))
            # 入场界面、战前增益、角色详情均不能触发接管。
            # 未选择时右下角按钮是灰色的，OCR 可能完全读不到“选择刻印”；
            # 用页面标题作为主判据，仍要求同时出现真我/祝福/专属内容，
            # 避免把普通战斗或战前配置页误判成刻印页。
            initial_button = any(
                "选择刻印" in r["text"] and r["box"][0] > 850 and r["box"][1] > 560
                for r in rows
            )
            initial_title = any(
                marker in text for marker in ("请选择英桀的刻印", "选择英桀的刻印", "真我的刻印")
            )
            initial = (initial_button or initial_title) and (
                "祝福" in text or "真我" in text or "专属" in text or "核心" in text
            )
            # “真我定制”模板在爱莉对话的背景上偶尔会提前命中。
            # 对话仍属于入场流程，接管器应先点右上角跳过，再等待
            # 初始专属刻印页面，而不是把这次识别当成失败退出。
            dialogue = (
                any("跳过" in r["text"] for r in rows if r["box"][1] < 100)
                and "历史" in text
                and ("爱莉希雅" in text or "开场白" in text)
            )
            floor = read_floor(rows)
            hud = context.run_recognition("角色战斗-生命HUD", argv.image) if floor else None
            resumed = bool(floor and hud and hud.hit)
            paused = all(word in text for word in ("战况报告", "状态列表", "往世乐土"))
            if initial or resumed or paused or dialogue:
                scene = "initial_signet" if initial else "dialogue" if dialogue else "resume"
                return CustomRecognition.AnalyzeResult(box=[0, 0, 1, 1], detail={"scene": scene})
            return None
        except Exception as exc:
            print(f"乐土关内交接识别失败：{exc}", flush=True)
            return None


class ElysianStage(AssistantElysianRun):
    """只负责入场后的流程；主任务负责准备及周常领奖。"""
    stage_only = True

    def frontend(self):
        if not self.settlement_requested and (
            ("命定的歧路" in self.text and "深层序列" in self.text)
            or ("出战位" in self.text and "开始战斗" in self.text)
            or ("首领预览" in self.text and "开始战斗" in self.text)
        ):
            raise RunHalt("关内执行期间返回了准备界面，保留现场，未计作通关")
        return super().frontend()

    def run(self, context, argv):
        # 注册对象可复用，但冷却和进度不能串到下一次任务。
        self.__init__()
        logger = Logger("往世乐土", context)

        def report(message):
            logger.info(message)
            if not context.tasker.stopping:
                logger.ui(message, "cyan")

        self.report = report
        self.motion.report = report
        try:
            return super().run(context, argv)
        except Exception as exc:
            # 配置/检查点异常也不能越过 Maa 的 ctypes 回调边界。
            logger.exception(f"关内执行失败：{exc}")
            from .ElysianRun import ElysianPause
            ElysianPause().run(context, argv)
            return False
        finally:
            logger.destroy()
