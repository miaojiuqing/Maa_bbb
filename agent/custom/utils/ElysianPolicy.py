"""乐土决策使用同一份本局记录；纯函数可离线回放。"""
import re
from dataclasses import dataclass, field, asdict
from .CharacterProfiles import CHARACTER_PROFILES

GATE_NAMES = {1: "鏖灭", 2: "真我", 3: "空梦", 10: "商店", 11: "戒律", 12: "螺旋", 13: "商店", 14: "天慧", 15: "繁星", 17: "无限", 18: "刹那", 19: "黄金", 20: "救世", 21: "旭光", 22: "浮生", 23: "首领"}
DISABLABLE_FAMILIES = {"鏖灭"}
# 暂停菜单“增益列表”里会出现的英桀名；角色专属与核心由 characters 目录汇总。
FAMILY_MARKERS = ("空梦", "繁星", "戒律", "天慧", "浮生", "无限", "旭光", "刹那", "救世")
# 商店与混合奖励没有体系标题，按刻印名称和核心效果识别鏖灭。
# 普通名称不含“鏖灭”，不能只过滤这两个字。
AOMIE_MARKERS = ("鏖", "赤骨", "剑锋·剑冢", "无妄·无心", "唯神·唯我",
                 "狂信·狂人", "命路·命舛", "无死·无生", "千钧·千转",
                 "非人·非鬼", "一人·一面", "焚身·焚骨", "故土·故国",
                 "燃血解放", "燃血狱衣")


def known_signets():
    """全部角色档案里出现过的刻印名，用于判断第一层是否已经弹出初始专属。"""
    names = set(FAMILY_MARKERS)
    for variants in CHARACTER_PROFILES.values():
        for profile in variants.get("variants", {}).values():
            plan = profile.get("signet_plan", {})
            names.add(profile.get("requires_signet", ""))
            names.update(plan.get("exclusive", []))
            names.update(plan.get("cores", []))
    names.discard("")
    return tuple(sorted(names))


KNOWN_SIGNETS = known_signets()


def key_exclusives(profile):
    """关键专属：必需刻印加方案里的下一个；方案抄写有误时也不会漏掉必需项。"""
    required = profile.get("requires_signet", "")
    others = [name for name in profile.get("signet_plan", {}).get("exclusive", []) if name != required]
    return ([required] if required else []) + others[:1]


@dataclass
class RunState:
    role: str = "窈窕谍影"
    variant: str = "elysian_huashang"
    floor: int = 0
    total: int = 17
    role_verified: bool = False
    build_verified: bool = False
    acquired: list = field(default_factory=list)
    families: dict = field(default_factory=dict)
    phase: str = "准备"
    target: str = ""
    result: str = "运行中"
    reason: str = ""
    # 默认为原实测策略。小助手仅传入当前任务中明确启用的自定义项。
    exclusive_priority: list = field(default_factory=list)
    buff_priority: list = field(default_factory=list)
    gate_priority: list = field(default_factory=list)
    disabled_families: list = field(default_factory=list)
    shop_enabled: bool = True
    def has(self, name): return any(name in s for s in self.acquired)
    def record(self, text, family=""):
        if text not in self.acquired:
            self.acquired.append(text)
            if family: self.families[family] = self.families.get(family, 0) + 1
    def to_dict(self): return asdict(self)


def normalize(text):
    return re.sub(r"\s+", "", text).replace("麈灭", "鏖灭").replace("鏖天", "鏖灭").replace("塵灭", "鏖灭")


def signet_disabled(text, state, family=""):
    if family and family in state.disabled_families:
        return True
    # OCR 可能将间隔号读成其他符号或省略，名称比对不依赖间隔号。
    text = re.sub(r"[·•・.。]", "", normalize(text))
    return "鏖灭" in state.disabled_families and any(
        re.sub(r"[·•・.。]", "", marker) in text for marker in AOMIE_MARKERS
    )


def score_signet(text, state):
    if signet_disabled(text, state):
        return -10000
    text = normalize(text)
    profile = CHARACTER_PROFILES[state.role]["variants"][state.variant]
    required = profile["requires_signet"]
    if required in text:
        return -1000 if state.has(required) else 2100
    for i, pattern in enumerate(state.exclusive_priority):
        if re.search(pattern, text):
            return -1000 if state.has(normalize(text)) else 2050-i*10
    for i, name in enumerate(profile["signet_plan"]["exclusive"]):
        if name in text: return -1000 if state.has(name) else 2000-i*100
    for name in profile["signet_plan"]["cores"]:
        if name in text: return 1500
    if any(n in text for n in ("风致", "霆袭")): return -100
    if ("物理" in text and "元素" not in text) or "冰冻" in text or "火焰" in text: return -200
    if re.search("受到的.*伤害.*(低|降低|减少)", text) and "敌人" not in text and "造成" not in text:
        return 20
    if re.search("敌人.*(攻击|造成的).*伤害.*(降低|减少)", text) and "提高" not in text:
        return 20
    patterns = {
        "全伤": r"全伤害", "双伤": r"物理.*元素|元素.*物理",
        "易伤": r"敌人受到的.*伤害", "元素": r"元素伤害|雷电伤害",
        "物理": r"物理伤害", "生命上限": r"生命.*上限",
        "能量上限": r"能量.*上限", "双限提升": r"生命.*能量|能量.*生命",
        "回复能量": r"回复.*能量|恢复.*能量",
    }
    for i, category in enumerate(state.buff_priority):
        if category in patterns and re.search(patterns[category], text):
            return 1000-i*20
    penalties = 0
    if re.search("必杀技|极限闪避|星环爆发|星之环爆发", text): penalties = 150
    values = [("穿透", 450), ("敌人受到的.*(全|元素|雷电).*伤害", 400),
              ("武器.*(全|元素|雷电|伤害|冷却)", 350),
              ("全伤害", 300), ("元素伤害|雷电伤害", 290),
              ("能量上限", 240), ("生命.*上限", 230), ("回复.*生命", 180),
              ("回复.*能量", 150)]
    return max([value for pattern, value in values if re.search(pattern, text)] or [50]) - penalties


def gate_order(state):
    profile = CHARACTER_PROFILES[state.role]["variants"][state.variant]
    plan = profile["signet_plan"]
    order = list(plan["gates"])
    if all(state.has(s) for s in key_exclusives(profile)):
        order.remove("真我"); order.append("真我")
    # 拿到某体系的核心后把该体系降位：体系与核心名都从当前角色档案推导，
    # 不再写死某一角色的核心名。真我由上面的专属规则单独处理。
    for family in plan["gates"]:
        if family == "真我":
            continue
        core = next((name for name in plan.get("cores", []) if family in name), "")
        if core and state.has(core) and family in order:
            order.remove(family); order.insert(min(6, len(order)), family)
    if state.gate_priority:
        order = list(dict.fromkeys(state.gate_priority + order))
    return [name for name in dict.fromkeys(order + ["商店", "首领"])
            if name not in state.disabled_families]


def choose_gate(detections, state):
    order = gate_order(state)
    candidates = [r for r in detections if GATE_NAMES.get(r.get("cls_index")) in order and r.get("score", 0) >= .55]
    if not candidates: return None
    return min(candidates, key=lambda r: (order.index(GATE_NAMES[r["cls_index"]]), -r["score"]))


def choice_rows(items):
    rows = []
    for top, bottom in ((180, 323), (332, 477), (485, 636)):
        lines = [i for i in items if i["box"][0] >= 510 and top <= i["box"][1] < bottom]
        if lines:
            lines.sort(key=lambda r: (r["box"][1], r["box"][0]))
            # 卡片左侧徽记属于选中区域；正文中蓝色关键词会打开术语说明。
            rows.append({"text": " ".join(r["text"] for r in lines), "point": (580, (top+bottom)//2)})
    return rows


def signet_detail_open(items):
    """术语弹层的关闭 X 与左侧说明文本共同确认，底层刻印正文也可能被 OCR 读出。"""
    close = any(normalize(i['text']).upper() in ('X', '×') and
                i['box'][0] > 1180 and i['box'][1] < 85 for i in items)
    body = any(180 <= i['box'][0] < 400 and 270 <= i['box'][1] < 500 for i in items)
    return close and body


def read_floor(items):
    text = "".join(normalize(i["text"]) for i in items if i["box"][0] < 310 and i["box"][1] < 75)
    match = re.search(r"(\d{1,2})/(\d{1,2})", text)
    if match:
        floor, total = map(int, match.groups())
        if 1 <= total <= 22 and 1 <= floor <= total: return floor, total
    # 减负模式左上角只有「第N层」（没有 n/17 计数），用它兜底；总层数仍是 17。
    match = re.search(r"第(\d{1,2})层", text)
    if match:
        floor = int(match.group(1))
        if 1 <= floor <= 22: return floor, 17
    return None


def shop_rows(items):
    """商品的等级标签随列表一起滚动，用它划分行，避免固定四等分串行。"""
    labels=sorted([i for i in items if i['box'][0]>1100 and 80<i['box'][1]<620 and normalize(i['text']) in ('普通','增幅','核心')],key=lambda i:i['box'][1])
    rows=[]
    for j,label in enumerate(labels):
        top=label['box'][1]-15
        bottom=labels[j+1]['box'][1]-15 if j+1<len(labels) else 631
        lines=sorted([i for i in items if 350<=i['box'][0]<1100 and top<=i['box'][1]<bottom],key=lambda i:i['box'][1])
        prices=[int(normalize(i['text'])) for i in items if i['box'][0]>1100 and top<=i['box'][1]<bottom and normalize(i['text']).isdigit()]
        if lines and prices and abs(lines[0]['box'][1]-label['box'][1])<20:
            rows.append({'title':normalize(lines[0]['text']),'text':normalize(''.join(i['text'] for i in lines)), 'price':min(prices), 'y':lines[0]['box'][1]+25})
    return rows
