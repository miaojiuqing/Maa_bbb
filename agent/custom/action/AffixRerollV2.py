# -*- coding: utf-8 -*-
"""圣痕洗词缀 V2（智能版）

与旧的“正则版”任务（entry: 洗词缀）并存，互不影响。

界面上一个下拉框切换两种模式：
    直接洗词缀      —— 普通重构，按【两条有效攻击力之和】择优
    词缀锁洗词缀    —— 定向重构（锁定一条只洗另一条），同样按【两条之和】择优

【启动页面 = 重构结果页】
    任务要求你先点一次「词缀重构」，停在**重构结果页**再开始 —— 就是能同时看到
    「旧词缀技能 / 新词缀技能」两块面板和「保留旧词缀 / 写入新词缀」两个按钮的那一页。

    为什么不从主页（普通重构页 / 定向重构页）启动：
      · 主页左下那小块「词缀技能」面板显示不全 —— 词缀名一长就被面板自己截掉，
        定向重构页上被锁定的那条还会被游戏自己的「已锁定」标记盖住；
      · 在结果页上，旧/新两块面板都是干净完整的，旧词缀就是"我现在身上的"，
        直接拿来判达标和择优最准；
      · 而且能走到结果页本身就说明你已经在定向重构页点过一次重构，
        也就意味着**锁已经设好了**。

【锁定的那条怎么认】
    锁定的词缀不会被重构，所以它在「旧词缀技能」和「新词缀技能」里长得**一模一样**。
    于是拿两批逐行比对：**只有一条完全相同** => 那条就是锁定的，
    同时也证明确实锁了一条（而不是两条都没锁、重构把两条都洗了）。

【循环】
    结果页：读旧(身上的) + 读新(候选) -> 旧达标就结束
            -> 新的有效总攻击力更高就点「写入新词缀」
            -> 否则：普通模式点「再次重构」**原地**换一批（不回主页，快一倍）；
                     锁模式没有「再次重构」，只能点「保留旧词缀」
    提交（写入/保留）之后游戏一定回到主页 -> 点「词缀重构」回到结果页 -> 继续

「刷到更好的就先写入」：只要新词缀的有效总攻击力更高，就先写入保底（哪怕还没到目标）。

单条高攻（开关，默认关）：在总和择优之外**追加**两条判据 ——
    写入：新词缀任意一条 ≥ 达标值且高于旧的同一条；完成：手里任意一条 ≥ 达标值。
    词缀锁模式下强制按关闭处理。

安全策略（写词缀不可逆，宁可停下也不猜）：
    - 每行 OCR 文本必须“像一条真词缀”（有数字 + 至少两个汉字）才算读到
    - 存疑的行（像攻击词条但条件认不出来）不算 0，会让整侧不可靠
    - **只有两侧都可靠、且新侧确实更好时，才会点「写入新词缀」**
    - 写后校验：下一轮读到的旧词缀必须等于上一轮写入的值
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, Tuple

from maa.context import Context
from maa.custom_action import CustomAction

from ..utils.AffixRules import (
    AffixLine,
    SideResult,
    canonical_attribute,
    evaluate_side,
    normalize_text,
    validate_selection,
)
from ..utils.Logger import Logger

# --------------------------------------------------------------------------
# 模式
# --------------------------------------------------------------------------
MODE_PLAIN = "直接洗词缀"
MODE_LOCK = "词缀锁洗词缀"
MODE_NAMES: Tuple[str, ...] = (MODE_PLAIN, MODE_LOCK)

# --------------------------------------------------------------------------
# pipeline 节点名（与 洗词缀V2.json 保持一致）
# --------------------------------------------------------------------------
# —— 重构结果页（任务从这里启动）——
NODE_OCR_OLD: Tuple[str, ...] = ("洗词缀V2-识别-旧词缀1", "洗词缀V2-识别-旧词缀2")
NODE_OCR_NEW: Tuple[str, ...] = ("洗词缀V2-识别-新词缀1", "洗词缀V2-识别-新词缀2")
NODE_CLICK_KEEP = "洗词缀V2-点击-保留旧词缀"
NODE_CLICK_WRITE = "洗词缀V2-点击-写入新词缀"
NODE_CLICK_REROLL = "洗词缀V2-点击-再次重构"

#: 用来确认“人确实停在重构结果页”
RESULT_MARKERS: Tuple[Tuple[str, str], ...] = (
    (NODE_CLICK_KEEP, "「保留旧词缀」按钮"),
    (NODE_CLICK_WRITE, "「写入新词缀」按钮"),
)

# —— 主页标记（提交之后回到主页，要靠这些确认 + 找重投按钮）——
NODE_HOME_PANEL = "洗词缀V2-主页-验证-词缀技能面板"
NODE_NORMAL_PREVIEW = "洗词缀V2-普通-验证-培养预览"
NODE_NORMAL_TEN = "洗词缀V2-普通-验证-十次重构按钮"
NODE_NORMAL_ROLL = "洗词缀V2-普通-点击-词缀重构"
NODE_LOCK_TAB = "洗词缀V2-锁-验证-定向重构页签"
NODE_LOCK_PREVIEW = "洗词缀V2-锁-验证-培养预览"
NODE_LOCK_ROLL = "洗词缀V2-锁-点击-词缀重构"

# —— 界面参数载体 ——
NODE_PARAM_MODE = "洗词缀V2-参数-模式"
NODE_PARAM_CONFIRM = "洗词缀V2-参数-确认词缀锁"
NODE_PARAM_SINGLE = "洗词缀V2-参数-单条高攻"
NODE_PARAM_SINGLE_VALUE = "洗词缀V2-参数-单条达标值"
NODE_PARAM_ATTR = "洗词缀V2-参数-角色属性"
NODE_PARAM_WEAPON = "洗词缀V2-参数-武器类别"
NODE_PARAM_TARGET = "洗词缀V2-参数-目标总攻击力"
NODE_PARAM_LIMIT = "洗词缀V2-参数-重构次数上限"

#: 主页定义：markers 确认“人还在这一页”，roll 是重投按钮，
#: fast_reroll 是该模式结果页上的「再次重构」（有的话能原地重投，不用回主页）
HOME_PLAIN: Dict[str, Any] = {
    "label": "普通重构页",
    "markers": (
        (NODE_NORMAL_PREVIEW, "右侧「重新生成2个词缀技能…」说明"),
        (NODE_NORMAL_TEN, "右下「十次重构」按钮"),
        (NODE_HOME_PANEL, "左下「词缀技能」面板"),
    ),
    "roll": NODE_NORMAL_ROLL,
    "fast_reroll": NODE_CLICK_REROLL,
}
HOME_LOCK: Dict[str, Any] = {
    "label": "定向重构页",
    "markers": (
        (NODE_LOCK_TAB, "顶部「定向重构」页签"),
        (NODE_LOCK_PREVIEW, "右侧「锁定的词缀…」说明"),
        (NODE_HOME_PANEL, "左下「词缀技能」面板"),
    ),
    "roll": NODE_LOCK_ROLL,
    # 词缀锁的结果页没有「再次重构」，只能保留/写入，所以这里为 None
    "fast_reroll": None,
}

#: 入口节点 custom_action_param 里可以调的默认值（界面上的选项会覆盖前 7 项）
#: 这几个默认值和 tools/gen_affix_task.py 里的 DEFAULT_* 保持一致
DEFAULTS: Dict[str, Any] = {
    "模式": MODE_PLAIN,
    "确认词缀锁": "No",
    "单条高攻": "Yes",
    "单条达标值": 22.9,
    "属性": "异能",
    "武器": "弓箭、环刃",
    "目标攻击力": 42.0,
    "最大重构次数": 500,
    # ---- 下面这些没有做到界面里，想改直接改 pipeline JSON ----
    "重构等待": 2.0,
    "写入等待": 2.0,
    "OCR重试次数": 3,
    "不可靠上限": 8,
}

YES_VALUES = ("Yes", "yes", "是", "True", "true", "1")


class AffixRerollV2(CustomAction):
    """智能洗词缀：按有效攻击力自动在新旧词缀之间择优，直到达标。"""

    # ------------------------------------------------------------------
    # 参数
    # ------------------------------------------------------------------
    def _read_node_param(
        self, context: Context, node: str, logger: Logger
    ) -> Optional[Any]:
        """读取某个 pipeline 节点上挂的参数（界面下拉框/开关/输入框写进去的值）。"""
        try:
            data = context.get_node_data(node)
        except Exception as exc:
            logger.warning(
                f"读取节点参数失败（{node}）: {exc}；"
                f"界面上的选择可能不会生效，将使用 pipeline 里的默认值"
            )
            return None
        if not isinstance(data, dict):
            return None

        value = data.get("custom_action_param")
        if value is None:
            action = data.get("action")
            if isinstance(action, dict):
                param = action.get("param")
                if isinstance(param, dict):
                    value = param.get("custom_action_param")
        if value is None or value == "":
            return None
        return value

    def _load_params(
        self, context: Context, argv: Any, logger: Logger
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = dict(DEFAULTS)

        try:
            raw = getattr(argv, "custom_action_param", None)
            if raw:
                parsed = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(parsed, dict):
                    params.update(
                        {k: v for k, v in parsed.items() if v not in (None, "")}
                    )
        except Exception as exc:  # pragma: no cover - 防御性
            logger.warning(f"解析入口参数失败，使用默认值: {exc}")

        for key, node in (
            ("模式", NODE_PARAM_MODE),
            ("确认词缀锁", NODE_PARAM_CONFIRM),
            ("单条高攻", NODE_PARAM_SINGLE),
            ("属性", NODE_PARAM_ATTR),
            ("武器", NODE_PARAM_WEAPON),
        ):
            value = self._read_node_param(context, node, logger)
            if value is not None:
                params[key] = str(value).strip()

        for key, node, caster in (
            ("单条达标值", NODE_PARAM_SINGLE_VALUE, float),
            ("目标攻击力", NODE_PARAM_TARGET, float),
            ("最大重构次数", NODE_PARAM_LIMIT, int),
        ):
            value = self._read_node_param(context, node, logger)
            if value is None:
                continue
            try:
                params[key] = int(float(value)) if caster is int else float(value)
            except (TypeError, ValueError):
                logger.warning(
                    f"界面参数 {key} 取值 {value!r} 不合法，沿用默认值 {params[key]!r}"
                )

        params["模式"] = str(params["模式"]).strip()
        params["属性"] = str(params["属性"]).strip()
        params["武器"] = str(params["武器"]).strip()
        return params

    # ------------------------------------------------------------------
    # 截图 / 识别 / 点击
    # ------------------------------------------------------------------
    def _screencap(self, context: Context):
        return context.tasker.controller.post_screencap().wait().get()

    def _ocr_text(self, context: Context, node: str, image) -> str:
        try:
            detail = context.run_recognition(node, image)
        except Exception:
            return ""
        if detail is None:
            return ""

        best = getattr(detail, "best_result", None)
        text = getattr(best, "text", "") if best is not None else ""
        if text:
            return str(text)

        parts: List[str] = []
        for item in getattr(detail, "all_results", None) or []:
            piece = getattr(item, "text", "")
            if piece:
                parts.append(str(piece))
        return "".join(parts)

    def _locate(
        self, context: Context, node: str
    ) -> Optional[Tuple[int, int, int, int]]:
        """跑一次识别，命中就返回 box (x, y, w, h)。"""
        try:
            detail = context.run_recognition(node, self._screencap(context))
        except Exception:
            return None
        if detail is None or not getattr(detail, "hit", False):
            return None

        box = getattr(detail, "box", None)
        if box is None:
            return None
        try:
            x, y, w, h = (int(v) for v in box)
        except (TypeError, ValueError):
            return None
        if w <= 0 or h <= 0:
            return None
        return (x, y, w, h)

    def _visible(self, context: Context, node: str) -> bool:
        return self._locate(context, node) is not None

    def _find_and_click(
        self,
        context: Context,
        node: str,
        logger: Logger,
        label: str,
        attempts: int = 3,
    ) -> bool:
        """OCR 定位按钮文字，然后点文字框的**正中**。

        pipeline 里故意不写 target：MaaFramework 对四元组 target 会在矩形内
        随机取点（官方文档：a random point will be selected within the
        rectangle），矩形一大就会点到别的界面上去。这里把 box 缩成 1x1，
        让随机点退化成确定的一个像素。
        """
        attempts = max(1, int(attempts))
        for attempt in range(1, attempts + 1):
            box = self._locate(context, node)
            if box is None:
                if attempt < attempts:
                    logger.info(f"「{label}」第 {attempt} 次没认到，重试…")
                    time.sleep(0.4)
                    continue
                logger.error(f"没能定位到「{label}」（OCR 未命中，不敢乱点）")
                return False

            x, y, w, h = box
            cx, cy = x + w // 2, y + h // 2
            logger.info(f"「{label}」文字框 [{x}, {y}, {w}, {h}] -> 点击正中 ({cx}, {cy})")
            try:
                result = context.run_action(node, box=(cx, cy, 1, 1))
            except Exception as exc:
                logger.error(f"点击「{label}」异常: {exc}")
                return False
            if result is None or getattr(result, "success", True):
                return True
            logger.warning(f"点击「{label}」失败，重试…")
            time.sleep(0.4)
        return False

    # ------------------------------------------------------------------
    # 读词缀
    # ------------------------------------------------------------------
    def _read_side(
        self,
        context: Context,
        nodes: Tuple[str, ...],
        logger: Logger,
        label: str,
        attribute: str,
        weapon: str,
        attempts: int,
    ) -> SideResult:
        """读一侧的若干行词缀；读到噪声就重新截图重试。"""
        attempts = max(1, int(attempts))
        side: Optional[SideResult] = None
        for attempt in range(1, attempts + 1):
            image = self._screencap(context)
            texts = [self._ocr_text(context, node, image) for node in nodes]
            side = evaluate_side(texts, attribute, weapon)
            if side.reliable:
                return side
            if attempt < attempts:
                logger.info(f"{label} 第 {attempt} 次读到噪声（{side.detail()}），重试…")
                time.sleep(0.5)
        return side if side is not None else SideResult(lines=[], reliable=False)

    # ------------------------------------------------------------------
    # 判据
    # ------------------------------------------------------------------
    def _reached(
        self,
        side: SideResult,
        target: float,
        single_on: bool,
        single_value: float,
    ) -> Tuple[bool, str]:
        """这一侧是否已经满足目标。"""
        if side.total >= target:
            return True, f"有效总攻击力 {side.total} ≥ 目标 {target}"
        if single_on and side.best_single >= single_value:
            return True, f"单条有效攻击力 {side.best_single} ≥ 达标值 {single_value}"
        return False, ""

    def _decide_write(
        self,
        old_side: SideResult,
        new_side: SideResult,
        single_on: bool,
        single_value: float,
    ) -> Tuple[bool, str]:
        """要不要写入新词缀。

        **只有两侧都可靠时才会写入**——写词缀是不可逆的。
        总和优先（这样“两条都有效但单条都不高”的好词缀不会被错过），
        单条达标作为额外条件。
        """
        if not old_side.reliable or not new_side.reliable:
            return False, "有一侧读到的内容不可靠，不敢比较"
        if new_side.total > old_side.total:
            return True, f"有效总攻击力更高 {new_side.total} > {old_side.total}"
        if (
            single_on
            and new_side.best_single >= single_value
            and new_side.best_single > old_side.best_single
        ):
            return True, (
                f"单条有效攻击力 {new_side.best_single} ≥ {single_value}"
                f"（且高于旧的 {old_side.best_single}）"
            )
        return False, f"新 {new_side.total} 不比旧 {old_side.total} 好"

    # ------------------------------------------------------------------
    # 认「锁定的那条」
    # ------------------------------------------------------------------
    @staticmethod
    def _same_line(a: AffixLine, b: AffixLine) -> bool:
        """两行是不是同一条词缀。

        优先比原始文本（锁定的词缀不会被重构，两块面板上文本应该一模一样）；
        文本略有差异时退一步比「类型 + 数值」。
        """
        a_norm = normalize_text(a.raw)
        b_norm = normalize_text(b.raw)
        if a_norm and a_norm == b_norm:
            return True
        return (
            a.plausible
            and b.plausible
            and a.kind == b.kind
            and a.shown is not None
            and a.shown == b.shown
        )

    def _detect_locked_row(
        self, old_side: SideResult, new_side: SideResult, logger: Logger
    ) -> Tuple[Optional[int], bool]:
        """用「旧/新两批里没变的那条」判断锁在哪一条。

        返回 (0-based 索引 或 None, 是否判断明确)：
            (i,  True)  明确：只有第 i 条没变 -> 锁的就是它
            (None, True) 明确：两条都变了 -> 根本没锁
            (None, False) 判断不了（读不准 / 两条都没变）
        """
        if not old_side.reliable or not new_side.reliable:
            return None, False
        same = [
            index
            for index, (old_line, new_line) in enumerate(
                zip(old_side.lines, new_side.lines)
            )
            if self._same_line(old_line, new_line)
        ]
        if len(same) == 1:
            return same[0], True
        if not same:
            return None, True
        return None, False

    # ------------------------------------------------------------------
    # 页面
    # ------------------------------------------------------------------
    def _missing_markers(self, context: Context, home: Dict[str, Any]) -> List[str]:
        return [label for node, label in home["markers"] if not self._visible(context, node)]

    def _enter_result_page(
        self, context: Context, logger: Logger, home: Dict[str, Any], wait: float
    ) -> bool:
        """在主页点「词缀重构」，并确认真的回到了结果页。"""
        logger.info(f"在{home['label']}点「词缀重构」，回到结果页")
        if not self._find_and_click(context, home["roll"], logger, "词缀重构"):
            logger.ui(f"❌ 在{home['label']}找不到「词缀重构」按钮，已停止", "red")
            return False
        time.sleep(wait)
        if not self._visible(context, NODE_CLICK_WRITE):
            logger.error("点了「词缀重构」但没有回到结果页")
            logger.ui(
                "⚠️ 没有回到重构结果界面（可能材料不足或界面变了），已停止",
                "orange",
            )
            return False
        return True

    # ------------------------------------------------------------------
    # 入口
    # ------------------------------------------------------------------
    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        logger = Logger("洗词缀V2", context)

        try:
            params = self._load_params(context, argv, logger)
        except Exception as exc:
            logger.error(f"读取参数失败: {exc}")
            return CustomAction.RunResult(success=False)

        mode = params["模式"]
        if mode not in MODE_NAMES:
            message = f"未知的洗词缀模式: {mode!r}（可选: {'/'.join(MODE_NAMES)}）"
            logger.error(message)
            logger.ui(f"❌ {message}", "red")
            return CustomAction.RunResult(success=False)

        attribute = params["属性"]
        weapon = params["武器"]
        target = float(params["目标攻击力"])
        limit = max(1, int(params["最大重构次数"]))
        single_value = float(params["单条达标值"])
        single_on = str(params["单条高攻"]).strip() in YES_VALUES
        home = HOME_PLAIN if mode == MODE_PLAIN else HOME_LOCK

        problem = validate_selection(attribute, weapon)
        if problem:
            logger.error(problem)
            logger.ui(f"❌ 参数不合法：{problem}", "red")
            return CustomAction.RunResult(success=False)

        attr_canonical = canonical_attribute(attribute) or attribute

        # 词缀锁模式下强制忽略单条高攻（避免出现说不清的行为）
        if mode == MODE_LOCK and single_on:
            single_on = False
            logger.warning("词缀锁模式下不支持「单条高攻」，已按关闭处理")
            logger.ui("ℹ️ 词缀锁模式下已忽略「单条高攻」设置（按关闭处理）", "orange")

        logger.info(
            f"参数: 模式={mode} 属性={attr_canonical} 武器类别={weapon} "
            f"目标总攻击力={target} 单条高攻={'开' if single_on else '关'}"
            f"{f'（达标值 {single_value}）' if single_on else ''} 重构上限={limit}"
        )
        logger.ui(
            f"开始智能洗词缀【{mode}】：{attr_canonical} / {weapon} / 目标 {target}"
            + (f" 或 单条 {single_value}" if single_on else "")
        )

        # 词缀锁是稀有材料，必须二次确认（界面默认“否”）
        if mode == MODE_LOCK and str(params["确认词缀锁"]).strip() not in YES_VALUES:
            message = (
                "词缀锁洗词缀需要先把“确认使用词缀锁”勾成【是】再开始"
                "（词缀锁材料每周有获取上限，属于稀有资源）"
            )
            logger.error(message)
            logger.ui(f"❌ {message}", "red")
            return CustomAction.RunResult(success=False)

        return self._run_result_loop(
            context,
            logger,
            params,
            home,
            mode,
            attribute,
            weapon,
            target,
            limit,
            single_on,
            single_value,
        )

    # ------------------------------------------------------------------
    # 主循环（从重构结果页启动）
    # ------------------------------------------------------------------
    def _run_result_loop(
        self,
        context: Context,
        logger: Logger,
        params: Dict[str, Any],
        home: Dict[str, Any],
        mode: str,
        attribute: str,
        weapon: str,
        target: float,
        limit: int,
        single_on: bool,
        single_value: float,
    ) -> CustomAction.RunResult:
        roll_wait = float(params["重构等待"])
        write_wait = float(params["写入等待"])
        ocr_retries = max(1, int(params["OCR重试次数"]))
        unreliable_limit = max(1, int(params["不可靠上限"]))
        home_label = home["label"]
        fast_reroll = home.get("fast_reroll")

        # ---- 0. 必须停在重构结果页 ----
        missing = [label for node, label in RESULT_MARKERS if not self._visible(context, node)]
        if missing:
            logger.error(f"没停在重构结果页，缺少: {missing}")
            logger.ui(
                "❌ 请先点一次「词缀重构」，停在**重构结果页**再开始任务"
                "（就是能同时看到「旧词缀技能 / 新词缀技能」和「保留旧词缀 / 写入新词缀」的那一页）。"
                "缺少：" + "、".join(missing),
                "red",
            )
            return CustomAction.RunResult(success=False)

        logger.info("已确认停在重构结果页，开始比较旧/新词缀")

        locked_index: Optional[int] = None
        pending_side: Optional[SideResult] = None
        write_mismatch = 0
        unreliable_streak = 0
        empty_new_streak = 0
        last_total = 0.0
        best_seen = 0.0

        for round_index in range(1, limit + 1):
            old_side = self._read_side(
                context, NODE_OCR_OLD, logger, "旧词缀", attribute, weapon, ocr_retries
            )
            new_side = self._read_side(
                context, NODE_OCR_NEW, logger, "新词缀", attribute, weapon, ocr_retries
            )
            logger.info(
                f"[第 {round_index} 轮] 旧 总={old_side.total} 单条={old_side.best_single}"
                f"(可靠={old_side.reliable}) | "
                f"新 总={new_side.total} 单条={new_side.best_single}"
                f"(可靠={new_side.reliable})"
            )

            # 健康检查：结果页两块面板都应该是干净可读的
            if old_side.reliable:
                unreliable_streak = 0
            else:
                unreliable_streak += 1
                logger.warning(
                    f"结果页旧词缀读不准（连续 {unreliable_streak} 轮）：{old_side.detail()}"
                )
                if unreliable_streak >= unreliable_limit:
                    logger.ui(
                        "❌ 连续多轮在结果页读不出正常的旧词缀，已停止，请检查 ROI / 分辨率",
                        "red",
                    )
                    return CustomAction.RunResult(success=False)

            if not new_side.readable:
                empty_new_streak += 1
                logger.warning(f"新词缀读不到内容（连续 {empty_new_streak} 轮）")
                if empty_new_streak >= 3:
                    logger.ui(
                        "⚠️ 连续多轮读不到新词缀内容（可能界面变了），已停止", "orange"
                    )
                    return CustomAction.RunResult(success=False)
            else:
                empty_new_streak = 0

            # ---- 词缀锁：确认确实锁了一条，并认出是哪一条 ----
            if mode == MODE_LOCK:
                index, definite = self._detect_locked_row(old_side, new_side, logger)
                if definite and index is None:
                    message = (
                        "旧/新两批词缀里**没有任何一条保持不变**，说明当前没有锁定词缀"
                        "（否则锁定的那条不会被重构）。请回到定向重构页锁定一条要保留的词缀，"
                        "再点「词缀重构」重新进入结果页后开始任务"
                    )
                    logger.error(message)
                    logger.ui(f"❌ {message}", "red")
                    return CustomAction.RunResult(success=False)
                if index is not None and index != locked_index:
                    locked_index = index
                    logger.info(
                        f"锁定的是第 {index + 1} 条（旧/新两批里只有它没变）"
                    )

            # ---- 写后校验：上一轮写入的值，这一轮旧词缀里应该看得到 ----
            if pending_side is not None and old_side.reliable:
                if abs(old_side.total - pending_side.total) > 0.05:
                    write_mismatch += 1
                    logger.warning(
                        f"上一轮写入后，旧词缀读到 {old_side.total}，"
                        f"与预期 {pending_side.total} 不一致（连续 {write_mismatch} 次）"
                    )
                    if write_mismatch >= 2:
                        logger.ui(
                            "⚠️ 连续两次「写入新词缀」后旧词缀都不是写入的值，"
                            "写入似乎没生效，已停止（检查是否有二次确认弹窗）",
                            "orange",
                        )
                        return CustomAction.RunResult(success=False)
                else:
                    write_mismatch = 0
                pending_side = None

            # ---- 达标判定：结果页的旧词缀就是“我现在身上的” ----
            if old_side.reliable:
                last_total = old_side.total
                best_seen = max(best_seen, old_side.total)
                done, why = self._reached(old_side, target, single_on, single_value)
                if done:
                    extra = (
                        f"，锁定第 {locked_index + 1} 条" if locked_index is not None else ""
                    )
                    message = f"✅ 完成：{why}（{old_side.detail()}{extra}）"
                    logger.info(message)
                    # 顺手把这次候选按「保留旧词缀」收掉：离开时界面是干净的，
                    # 也不会把这次没用的候选留在页面上等你手动处理
                    if self._find_and_click(
                        context, NODE_CLICK_KEEP, logger, "保留旧词缀"
                    ):
                        logger.info("已按「保留旧词缀」收尾，界面回到主页")
                    else:
                        logger.warning(
                            "收尾时没能点到「保留旧词缀」，请手动处理一下界面"
                        )
                    logger.ui(message, "green")
                    return CustomAction.RunResult(success=True)

            # ---- 择优 ----
            write, why = self._decide_write(old_side, new_side, single_on, single_value)

            if write:
                gap = target - new_side.total
                if gap > 0:
                    message = (
                        f"⭐ 新词缀更优（{why}，还差 {gap:.1f} 到目标），先写入新词缀保底"
                    )
                else:
                    message = f"⭐ 新词缀更优（{why}），写入新词缀"
                logger.info(message + f"（{new_side.detail()}）")
                logger.ui(message)
                if not self._find_and_click(
                    context, NODE_CLICK_WRITE, logger, "写入新词缀"
                ):
                    return CustomAction.RunResult(success=False)
                pending_side = new_side
            else:
                if fast_reroll is not None and self._visible(context, fast_reroll):
                    # 快速路径：结果页上直接「再次重构」，原地换一批，不回主页
                    logger.info(f"保留旧词缀（{why}）→ 用「再次重构」原地重投，不回主页")
                    if not self._find_and_click(
                        context, fast_reroll, logger, "再次重构"
                    ):
                        return CustomAction.RunResult(success=False)
                    time.sleep(roll_wait)
                    continue

                # 锁模式的结果页没有「再次重构」，只能保留 -> 回主页 -> 再进结果页
                logger.info(f"保留旧词缀（{why}）")
                if not self._find_and_click(
                    context, NODE_CLICK_KEEP, logger, "保留旧词缀"
                ):
                    return CustomAction.RunResult(success=False)
                pending_side = old_side if old_side.reliable else None

            # ---- 提交之后游戏一定回到主页：确认后点「词缀重构」回来 ----
            time.sleep(write_wait)
            missing = self._missing_markers(context, home)
            if missing:
                logger.error(f"提交之后没有回到{home_label}: {missing}")
                logger.ui(
                    f"⚠️ 提交之后没有回到{home_label}，已停止（缺少：" + "、".join(missing) + "）",
                    "orange",
                )
                return CustomAction.RunResult(success=False)

            if not self._enter_result_page(context, logger, home, roll_wait):
                # 回不去结果页（多半材料用完了）。如果刚提交的值其实已经达标
                # （总攻击力或单条达标值任一满足），那就正常收工，不要报失败。
                if pending_side is not None:
                    done, why = self._reached(
                        pending_side, target, single_on, single_value
                    )
                    if done:
                        message = (
                            f"✅ 完成（未做二次确认）：提交后读数满足「{why}」，"
                            "材料似乎已用尽，就此结束"
                        )
                        logger.info(message)
                        logger.ui(message, "green")
                        return CustomAction.RunResult(success=True)
                logger.ui(
                    "⚠️ 提交后没能回到结果页（可能材料不足），已停止", "orange"
                )
                return CustomAction.RunResult(success=False)

        logger.error(f"已达到重构次数上限 {limit}")
        logger.ui(
            f"⚠️ 已重构 {limit} 次仍未达标（当前总攻击力 {last_total}，"
            f"过程中最高 {best_seen}），已停止",
            "orange",
        )
        return CustomAction.RunResult(success=False)


class AffixRerollV2ParamHolder(CustomAction):
    """空动作：只用来承载界面下拉框/开关/输入框写进来的参数。

    每个选项各自 override 一个这种节点上的 custom_action_param，互不覆盖；
    AffixRerollV2 运行时再用 context.get_node_data() 把它们读回来。
    """

    def run(
        self, context: Context, argv: CustomAction.RunArg
    ) -> CustomAction.RunResult:
        return CustomAction.RunResult(success=True)
