# -*- coding: utf-8 -*-
"""圣痕词缀解析规则（纯逻辑，不依赖 maa / 游戏运行环境，可离线单测）

游戏内词缀文本（OCR 结果）样例：
    "攻击提升9.0"                          -> 无条件类（任何角色都算有效）
    "虚数角色攻击提升13.0"                 -> 角色属性类
    "重炮、镰刀、火箭锤角色攻击提升22.7"   -> 武器类别类
    "暴击伤害提升4.95%"                    -> 无效词缀
    "生命上限提升235.4"                    -> 无效词缀

有效词缀（计入“有效总攻击力”）只有三类：
    1. 角色属性类：形如 "<属性>角色攻击提升xx.x"，仅当所选属性一致时有效
    2. 武器类别类：形如 "<武器1>、<武器2>…角色攻击提升xx.x"
       只要文本里出现的武器全部属于所选武器组即有效
       （不要求列全该组武器，也不要求顺序一致）
    3. 无条件类：形如 "攻击提升xx.x"，任何属性/武器的角色都有效
    其余一律视为无效词缀，按 0 计。

设计说明：本模块只有纯函数，方便用普通 Python 直接跑单测
（见 tools/test_affix_rules.py），不需要启动游戏或 MaaFramework。
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------
# 1. 词缀知识表（游戏内词缀种类有限，全部在这里维护）
# --------------------------------------------------------------------------

#: 角色的 6 种属性
ATTRIBUTES: Tuple[str, ...] = ("生物", "机械", "异能", "量子", "虚数", "星尘")

#: 属性名 -> 可接受的写法。游戏内第 6 种属性的文案是“星尘”；
#: “星辰”只是常见笔误，顺手一起认掉，不影响正常判定。
ATTRIBUTE_ALIASES: Dict[str, Tuple[str, ...]] = {
    "生物": ("生物",),
    "机械": ("机械", "机槭", "机戒"),
    "异能": ("异能", "异熊", "異能"),
    "量子": ("量子", "量孑"),
    "虚数": ("虚数", "虚敉"),
    "星尘": ("星尘", "星辰"),
}

#: 武器类别分组：菜单名 -> 该词条涵盖的武器（顺序无关，可只出现其中一部分）
WEAPON_GROUPS: "Dict[str, Tuple[Tuple[str, ...], ...]]" = {
    "大剑、拳套": (("大剑", "大刽"), ("拳套", "拳査")),
    "太刀、十字架、链刃": (("太刀",), ("十字架", "十字加"), ("链刃", "链刀")),
    "弓箭、环刃": (("弓箭", "弓箭"), ("环刃", "环刀", "环刃")),
    "重炮、镰刀、火箭锤": (("重炮", "重砲"), ("镰刀", "鎌刀"), ("火箭锤", "火箭鎚")),
    "梭镖、驱动核心、机关杖": (("梭镖", "梭镳", "棱镖"), ("驱动核心",), ("机关杖", "机关杖")),
    "双枪、骑枪、速射弩": (("双枪",), ("骑枪",), ("速射弩", "速射弓")),
}

#: 一个词缀行里可能混进来的面板标题等噪声（OCR 把标题一起框进来时兜底）
_NOISE_WORDS: Tuple[str, ...] = (
    "旧词缀技能",
    "新词缀技能",
    "词缀技能",
    "词缀",
    "技能",
)

#: “攻击提升”可能被 OCR 认错的写法
_ATTACK_TOKEN_RE = re.compile(r"攻击提[升井开什仟]")

#: 识别数字时的常见字符混淆（只在数字尾巴上应用）
_OCR_DIGIT_MAP = str.maketrans(
    {
        "O": "0", "o": "0", "D": "0", "Q": "0", "U": "0",
        "l": "1", "I": "1", "i": "1", "|": "1", "!": "1",
        "Z": "2", "z": "2",
        "A": "4", "a": "4",
        "S": "5", "s": "5",
        "G": "6", "b": "6",
        "T": "7", "?": "7",
        "B": "8",
        "g": "9", "q": "9",
    }
)

_NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")
_CJK_RE = re.compile(r"[^\u4e00-\u9fff]+")
_CJK_CHAR_RE = re.compile(r"[\u4e00-\u9fff]")
_DIGIT_RE = re.compile(r"\d")

#: 单条词缀数值的合理上限（有条件的紫词条上限为 23.0，留点余量）
_VALUE_MAX = 30.0

# 词缀种类标签
KIND_UNCONDITIONAL = "无条件"
KIND_ATTRIBUTE = "属性"
KIND_WEAPON = "武器"
KIND_INVALID = "无效"
KIND_AMBIGUOUS = "存疑"
KIND_UNREADABLE = "未识别"

#: 已知的“非攻击”词缀关键词。把「提升」和这些词放在一起的，就是确定的无效词缀。
#: 不在这个表里、却带「提升」+数字的，宁可标成“存疑”也不当成 0。
#: 想扩展直接往这里加即可（日志里 `(存疑…)` 的行就是候选）。
NON_ATTACK_KEYWORDS: Tuple[str, ...] = (
    "生命", "会心", "暴击", "能量", "伤害", "护盾", "防御", "抗性",
    "回复", "速度", "全伤", "冰冻", "火焰", "雷电", "物理", "元素",
)

#: “攻击提升”这四个字的指纹：命中两个及以上、又不是已知非攻击词缀就判为存疑
_ATTACK_FINGERPRINT: Tuple[str, ...] = ("攻", "击", "提", "升")

#: 分隔符（、，,/|·空格 等）
_SEPARATORS = "、，,／/|·・\\ 　+＆&"


# --------------------------------------------------------------------------
# 2. 文本归一化与数值提取
# --------------------------------------------------------------------------


def is_affix_text_plausible(text: object) -> bool:
    """OCR 结果看起来是不是“一条真正的词缀”，而不是噪声。

    游戏里每条词缀都带数值（攻击提升9.0 / 生命上限提升157.7 / 会心提升6.3 …），
    所以判据是：**至少要有一个数字，并且至少两个汉字**。

    这个判据是被真实日志逼出来的：某次运行里有 26 轮把
    「重炮、镰刀、火箭锤角色攻击提升22.7」读成了「核心」，
    于是那一侧的有效总攻击力从 31.7 掉到 9.0，程序就以为
    新刷出来的 12.3 更好，去点了「写入新词缀」——差点把一条好词缀冲掉。
    所以凡是这种“读不出数字”的行，一律当作没读到，交给上层重试或放弃。
    """
    norm = normalize_text(text)
    if not norm:
        return False
    if not _DIGIT_RE.search(norm):
        return False
    return len(_CJK_CHAR_RE.findall(norm)) >= 2


def normalize_text(text: object) -> str:
    """归一化 OCR 文本：全角转半角、去掉所有空白。

    Windows OCR 经常把中文逐字用空格隔开（如 "攻 击 提 升 9.0"），
    所以这里必须把所有空白全部删掉再匹配。
    """
    if text is None:
        return ""
    s = unicodedata.normalize("NFKC", str(text))
    s = re.sub(r"\s+", "", s)
    return s


def extract_attack_value(text: str) -> Optional[float]:
    """从一条词缀文本里取出 “攻击提升xx.x” 的数值。

    取不到返回 None。会在“攻击提升”之后的一小段文本里找数字，
    并容忍常见的 OCR 数字混淆（O->0、l->1 …）与小数点丢失（227 -> 22.7）。
    """
    norm = normalize_text(text)
    match = _ATTACK_TOKEN_RE.search(norm)
    if not match:
        return None

    tail = norm[match.end() : match.end() + 12]
    # 小数点被识别成逗号的情况
    tail = re.sub(r"(?<=\d)[,，](?=\d)", ".", tail)
    tail = tail.translate(_OCR_DIGIT_MAP)

    for num_match in _NUM_RE.finditer(tail):
        raw = num_match.group(0).replace(",", ".")
        try:
            value = float(raw)
        except ValueError:
            continue
        if value <= 0:
            continue
        if value > _VALUE_MAX:
            # 多半是小数点被 OCR 吃掉了，例如 22.7 -> 227、13.0 -> 130
            digits = raw.replace(".", "")
            if "." not in raw and len(digits) >= 2:
                try:
                    fixed = float(digits[:-1] + "." + digits[-1])
                except ValueError:
                    continue
                if 0 < fixed <= _VALUE_MAX:
                    return fixed
            continue
        return value
    return None


def _condition_part(text: str) -> Optional[str]:
    """取出 “攻击提升” 之前的条件部分（已清掉噪声字符），没有条件时返回 ""。"""
    norm = normalize_text(text)
    match = _ATTACK_TOKEN_RE.search(norm)
    if not match:
        return None
    prefix = norm[: match.start()]
    # 只保留中文，去掉 OCR 产生的标点/英文/数字噪声
    cond = _CJK_RE.sub("", prefix)
    for noise in _NOISE_WORDS:
        cond = cond.replace(noise, "")
    cond = cond.replace("角色", "")
    for sep in _SEPARATORS:
        cond = cond.replace(sep, "")
    return cond


def canonical_attribute(attribute: str) -> Optional[str]:
    """把用户/菜单给的属性写法归一到标准属性名（星辰 -> 星尘）。"""
    if attribute is None:
        return None
    text = str(attribute).strip()
    for canonical, aliases in ATTRIBUTE_ALIASES.items():
        if text == canonical or text in aliases:
            return canonical
    return None


#: 属性名里容易认错的字：key 是 OCR 可能读出来的字，value 是它可以等价于哪些字
_ATTR_CHAR_CONFUSIONS: Dict[str, Tuple[str, ...]] = {
    "尘": ("辰",), "辰": ("尘",),
    "子": ("孑",), "孑": ("子",),
    "数": ("敉",), "敉": ("数",),
    "能": ("熊",), "熊": ("能",),
    "械": ("槭", "戒"), "槭": ("械",), "戒": ("械",),
    "物": ("勿",), "勿": ("物",),
    "量": ("重",), "重": ("量",),
    "星": ("皇",), "皇": ("星",),
    "异": ("导",), "导": ("异",),
    "虚": ("虑",), "虑": ("虚",),
    "机": ("朿",), "生": ("牛",), "术": ("木",),
}


def _char_match(actual: str, expected: str) -> bool:
    """单个汉字是否等价（相同，或属于已知的易混字）。"""
    return actual == expected or actual in _ATTR_CHAR_CONFUSIONS.get(expected, ())


def match_attribute(cond: str) -> Optional[str]:
    """判断条件部分是不是某个角色属性，返回标准属性名。

    三级策略，越往后越保守：
      1. 完全等于某个属性名（或它的别名，例如 星辰 -> 星尘）
      2. 长度多一个字的包含匹配（OCR 多认了一个字）
      3. 两个汉字时逐字比对 6 个候选，**必须全字命中且唯一胜出**才认

    第 3 条就是给“量子 / 星尘”这类公认易混属性准备的（尘↔辰、子↔孑、量↔重…）。
    只要有第二个候选同样像，就返回 None —— 上层会把这行标成“存疑”，
    宁可停下也不拿它去判断该不该写入词缀。
    """
    for canonical, aliases in ATTRIBUTE_ALIASES.items():
        for alias in aliases:
            if cond == alias:
                return canonical
            if len(cond) == len(alias) + 1 and alias in cond:
                return canonical

    if len(cond) == 2:
        scored: List[Tuple[int, str]] = []
        for canonical, aliases in ATTRIBUTE_ALIASES.items():
            score = 0
            for alias in aliases:
                if len(alias) != 2:
                    continue
                score = max(
                    score,
                    sum(1 for a, b in zip(cond, alias) if _char_match(a, b)),
                )
            scored.append((score, canonical))
        scored.sort(reverse=True)
        if scored and scored[0][0] == 2 and (len(scored) == 1 or scored[0][0] > scored[1][0]):
            return scored[0][1]
    return None


def _build_weapon_index() -> List[Tuple[str, str, str]]:
    """(别名, 标准武器名, 所属组)，长名字排前面，避免互相截断。"""
    index: List[Tuple[str, str, str]] = []
    for group, tokens in WEAPON_GROUPS.items():
        for token in tokens:
            canonical = token[0]
            for alias in token:
                index.append((alias, canonical, group))
    index.sort(key=lambda item: len(item[0]), reverse=True)
    return index


_WEAPON_INDEX = _build_weapon_index()


def weapons_in(cond: str) -> Dict[str, str]:
    """找出条件部分里出现的武器名，返回 {标准武器名: 所属组}。

    这就是“多武器互相验证”的基础：一条词条通常会列 2~3 把武器，
    OCR 就算把其中一把认错，**另外一两把仍然能被认出来**，
    靠它们就能确定整行属于哪一组，不必要求每个字都对。
    """
    found: Dict[str, str] = {}
    rest = cond
    for alias, canonical, group in _WEAPON_INDEX:
        if alias and alias in rest:
            found[canonical] = group
            rest = rest.replace(alias, "")   # 抠掉，避免同一段文字被重复计数
    return found


def weapon_group_verdict(cond: str, group_name: str) -> str:
    """判定条件部分的武器属于哪个组。

    返回:
        "match"      命中所选组
        "foreign"    明确属于别的组（这是**确定的 0**，不是认错）
        "ambiguous"  跨组武器同时出现 / 一把武器都没认出来（多半是认错了）
    """
    found = weapons_in(cond)
    if found:
        groups = set(found.values())
        if len(groups) > 1:
            return "ambiguous"
        return "match" if groups == {group_name} else "foreign"

    # 一把武器都没认出来：退回“把本组武器名全部抠掉后是否为空”的老办法
    tokens = WEAPON_GROUPS.get(group_name) or ()
    rest = cond
    for alias in sorted((a for t in tokens for a in t), key=len, reverse=True):
        rest = rest.replace(alias, "")
    for sep in _SEPARATORS:
        rest = rest.replace(sep, "")
    return "match" if rest == "" else "ambiguous"


# --------------------------------------------------------------------------
# 3. 单条词缀 / 一侧词缀的判定
# --------------------------------------------------------------------------


@dataclass
class AffixLine:
    """一条词缀的解析结果。"""

    raw: str = ""
    value: float = 0.0          # 计入有效总攻击力的数值（无效时 0）
    shown: Optional[float] = None  # 文本里读到的数值（无论是否有效）
    kind: str = KIND_UNREADABLE
    effective: bool = False
    plausible: bool = False     # OCR 文本看起来像不像一条真词缀
    trustworthy: bool = False   # 这一行的“贡献值”是否可信（存疑时为 False）
    note: str = ""

    @property
    def readable(self) -> bool:
        return self.kind != KIND_UNREADABLE

    def describe(self) -> str:
        if not self.raw.strip():
            return "未识别到文本"
        if self.shown is None:
            return f"{self.kind}: {self.raw!r}"
        return f"{self.kind}: {self.raw!r} -> {self.shown}"

    def describe_short(self) -> str:
        if not self.raw.strip():
            return "(未识别)"
        if self.effective:
            return f"{self.raw}(有效{self.shown})"
        if self.kind == KIND_AMBIGUOUS:
            return f"{self.raw}(存疑，不计也不信)"
        if self.shown is not None:
            return f"{self.raw}(无效)"
        return f"{self.raw}({self.kind})"


def classify_line(
    text: str,
    attribute: str,
    weapon_group: str,
) -> AffixLine:
    """判定单条词缀文本对指定角色是否有效。

    关键区别（这是踩坑之后加的）：
      「无效」= 我们**确定**这条词缀对当前角色没贡献（例如生命上限提升）；
      「存疑」= 这条看起来像攻击词条，但条件没认出来 —— **不可以当成 0**，
               否则会把该侧的有效攻击力低估，进而误判“新的更好”去写入。
               存疑会让这一侧 overall 变成“不可靠”，从而禁止写入。

    Args:
        text: OCR 得到的词缀文本
        attribute: 所选角色属性（ATTRIBUTES 之一，也接受“星辰”）
        weapon_group: 所选武器组菜单名（WEAPON_GROUPS 的 key）
    """
    raw = "" if text is None else str(text)
    line = AffixLine(raw=raw)
    line.plausible = is_affix_text_plausible(raw)
    line.trustworthy = line.plausible

    if not line.plausible:
        line.kind = KIND_UNREADABLE
        line.note = "OCR 文本不像词缀（没有数字 / 汉字太少）"
        return line

    value = extract_attack_value(raw)
    cond = _condition_part(raw)

    if cond is None:
        norm = normalize_text(raw)
        # 「攻击提升」这四个字里命中两个及以上，又不是已知的非攻击词缀
        # -> 多半是它们被认错了（攻击->攻去、提升->提丹…）。
        # 这种情况绝对不能算成 0：真实日志里就是这么把 31.7 低估成 9.0 的。
        # 用“命中两个字”而不是写死「提升」，是为了连“升”也被认错时仍能兜住。
        fingerprint = sum(1 for ch in _ATTACK_FINGERPRINT if ch in norm)
        if fingerprint >= 2 and not any(k in norm for k in NON_ATTACK_KEYWORDS):
            line.kind = KIND_AMBIGUOUS
            line.trustworthy = False
            line.note = (
                f"疑似“攻击提升”被认错（命中 {fingerprint} 个字），"
                f"也不是已知的非攻击词缀"
            )
            return line
        line.kind = KIND_INVALID
        line.note = "不含“攻击提升”（属于其它类型词缀，确定的 0）"
        return line

    line.shown = value
    if value is None:
        line.kind = KIND_AMBIGUOUS
        line.trustworthy = False
        line.note = "认出了“攻击提升”但没读出数值"
        return line

    wanted_attribute_name = canonical_attribute(attribute)
    if wanted_attribute_name is None:
        line.kind = KIND_AMBIGUOUS
        line.trustworthy = False
        line.note = f"未知的角色属性 {attribute!r}"
        return line

    # 1) 无条件类
    if cond == "":
        line.kind = KIND_UNCONDITIONAL
        line.effective = True
        line.value = value
        return line

    # 2) 角色属性类
    matched_attribute = match_attribute(cond)
    if matched_attribute is not None:
        line.kind = KIND_ATTRIBUTE
        if matched_attribute == wanted_attribute_name:
            line.effective = True
            line.value = value
        else:
            line.note = f"属性为{matched_attribute}，与所选{wanted_attribute_name}不符"
        return line

    # 3) 武器类别类（多武器互相验证）
    verdict = weapon_group_verdict(cond, weapon_group)
    if verdict == "match":
        line.kind = KIND_WEAPON
        line.effective = True
        line.value = value
        return line
    if verdict == "foreign":
        line.kind = KIND_INVALID
        line.note = f"条件 {cond!r} 明确属于别的武器组"
        return line

    line.kind = KIND_AMBIGUOUS
    line.trustworthy = False
    line.note = f"条件 {cond!r} 既不像属性也不像已知武器组，疑似认错"
    return line


@dataclass
class SideResult:
    """一侧（旧词缀 / 新词缀）的判定结果。"""

    total: float = 0.0
    lines: List[AffixLine] = field(default_factory=list)
    readable: bool = True
    reliable: bool = True   # 每一行都读成了像样的词缀，才敢据此做“写入”这种不可逆操作

    @property
    def best_single(self) -> float:
        """单条最高有效攻击力（“只洗一条高攻”模式用）。"""
        return max((line.value for line in self.lines), default=0.0)

    def summary(self) -> str:
        return " + ".join(
            (f"{line.shown}" if line.effective else "0") for line in self.lines
        )

    def detail(self) -> str:
        return " | ".join(line.describe_short() for line in self.lines)


def evaluate_side(
    texts: Sequence[str],
    attribute: str,
    weapon_group: str,
) -> SideResult:
    """把一侧（通常 2 行）的词缀文本汇总成有效总攻击力。

    readable=False 表示 OCR 完全没读到内容；
    reliable=False 表示有行读成了噪声，调用方**不可以**据此点「写入新词缀」。
    """
    lines = [classify_line(t, attribute, weapon_group) for t in texts]
    result = SideResult(lines=lines)
    result.total = round(sum(line.value for line in lines), 4)
    result.readable = any(line.readable for line in lines)
    # 只要有一行“存疑”（疑似认错的攻击词条），这一侧就不许用来做写入判断
    result.reliable = all(line.trustworthy for line in lines)
    return result


def validate_selection(attribute: str, weapon_group: str) -> Optional[str]:
    """校验下拉框选项是否合法，合法返回 None，否则返回错误说明。"""
    known_attribute = any(attribute in aliases for aliases in ATTRIBUTE_ALIASES.values())
    if not known_attribute:
        return f"未知的角色属性: {attribute!r}（可选: {'/'.join(ATTRIBUTES)}）"
    if weapon_group not in WEAPON_GROUPS:
        return (
            f"未知的武器类别: {weapon_group!r}"
            f"（可选: {'/'.join(WEAPON_GROUPS.keys())}）"
        )
    return None


def weapon_group_menu_names() -> List[str]:
    """返回武器组菜单名列表（供文档 / 自检使用）。"""
    return list(WEAPON_GROUPS.keys())
