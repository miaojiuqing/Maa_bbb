# -*- coding: utf-8 -*-
"""
繁中适配助手  ——  给 Maa_bbb / MFW 用的简繁兼容管理工具

它能做的事：
  1. 一键 启用/停用 繁中兼容（改 interface.json，自动备份）
  2. 一键 重建 繁中覆盖包（扫 resource/base + resource_win32，自动补繁体）
  3. 维护「用词规则」：刷新→重置 这类【用词不同】的情况，字符转换修不到的，靠规则补
  4. 维护「节点补丁」：给某个节点强行追加期望文字 / 限制 max_hit 等
  5. 日志诊断：扫 maafw.log，把「OCR 明明读到了、但节点没匹配上」的文字挖出来，一键补进节点

运行：双击 繁中助手.bat
"""
import os, re, sys, json, shutil, datetime, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
# 工具可能放在两个位置：
#   1) 程序根目录（发布包里的用法）
#   2) resource/resource_tw/tools/（仓库里的用法）
# 所以从自身位置向上找，直到找到含 resource/base 或 interface.json 的目录。
def _find_app_root(start):
    cur = start
    for _ in range(6):
        if os.path.isdir(os.path.join(cur, "resource", "base")) or \
           os.path.isfile(os.path.join(cur, "interface.json")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return start

APP = _find_app_root(HERE)
# ⚠ 游戏目录自带 python312.dll 及 3.12 版 .pyd，会遮蔽标准库同名模块。
# 把脚本所在目录从 sys.path 剔除，避免 "python312.dll conflicts" 之类的启动失败。
sys.path[:] = [p for p in sys.path if os.path.abspath(p or os.getcwd()) != HERE]
RES = os.path.join(APP, "resource")
TW_DIR = os.path.join(RES, "resource_tw")
TW_PIPE = os.path.join(TW_DIR, "pipeline", "繁中兼容.json")
IFACE = os.path.join(APP, "interface.json")
CHARMAP = os.path.join(HERE, "繁中助手_字表.txt")
RULES = os.path.join(HERE, "繁中助手_规则.json")
LOG = os.path.join(APP, "debug", "maafw.log")
HOLD_MS_DEFAULT = 120

# 繁简同形、反查会得到罕用异体，必须不转
KEEP = set("出回征家和真核了假卷玩查表秘教具弦布制")
# 多候选字，按游戏 UI 语义定夺（None = 不转）
FIX = {"奖":"獎","获":"獲","历":"歷","当":"當","团":"團","个":"個","启":"啟","资":"資",
       "并":"並","复":"復","签":"簽","炼":"煉","锈":"鏽","发":"發","录":"錄","证":"證",
       "说":"說","专":"專","线":"線","坏":"壞","么":"麼","账":"帳","周":"週",
       "面":None,"升":None,"向":None}


# ---------------------------------------------------------------- 基础工具
def strip_jsonc(t):
    o, i, n, s = [], 0, len(t), False
    while i < n:
        c = t[i]
        if s:
            o.append(c)
            if c == '\\' and i + 1 < n:
                o.append(t[i+1]); i += 2; continue
            if c == '"': s = False
            i += 1; continue
        if c == '"': s = True; o.append(c); i += 1; continue
        if c == '/' and i + 1 < n and t[i+1] == '/':
            while i < n and t[i] not in '\r\n': i += 1
            continue
        if c == '/' and i + 1 < n and t[i+1] == '*':
            j = t.find('*/', i + 2); i = n if j < 0 else j + 2; continue
        o.append(c); i += 1
    return re.sub(r',(\s*[}\]])', r'\1', ''.join(o))


def load_jsonc(path):
    return json.loads(strip_jsonc(open(path, encoding='utf-8-sig').read()))


def now():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def backup(path):
    if os.path.exists(path):
        b = path + '.bak_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        shutil.copy2(path, b)
        return b
    return None


# ---------------------------------------------------------------- 规则存取
def load_rules():
    if os.path.exists(RULES):
        try:
            d = load_jsonc(RULES)
        except Exception:
            d = {}
    else:
        d = {}
    d.setdefault("用词", [])
    d.setdefault("节点补丁", {})
    d.setdefault("选项", {"按住时长": HOLD_MS_DEFAULT, "转按住时长": True})
    return d


def save_rules(d):
    backup(RULES)
    tmp = RULES + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(d, f, ensure_ascii=False, indent=4)
    os.replace(tmp, RULES)


# ---------------------------------------------------------------- 简繁字表
_S2T = None
def build_s2t():
    global _S2T
    if _S2T is not None:
        return _S2T
    if not os.path.exists(CHARMAP):
        raise FileNotFoundError("缺少字表文件：繁中助手_字表.txt")
    t2s = {}
    for line in open(CHARMAP, encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        p = line.split('\t')
        if len(p) == 2:
            t2s[p[0]] = p[1].split()
    cand = {}
    for t, ss in t2s.items():
        for s in ss:
            if len(s) == 1 and len(t) == 1:
                cand.setdefault(s, set()).add(t)
    m = {}
    for s, cs in cand.items():
        if s in KEEP:
            continue
        if s in FIX:
            if FIX[s]:
                m[s] = FIX[s]
            continue
        if s in cs:
            continue
        if len(cs) == 1:
            m[s] = next(iter(cs))
    for s, v in FIX.items():
        if v and s not in m:
            m[s] = v
    _S2T = m
    return m


def to_trad(s):
    m = build_s2t()
    out, changed = [], False
    for c in s:
        t = m.get(c)
        if t:
            out.append(t); changed = True
        else:
            out.append(c)
    return ''.join(out), changed


CJK = re.compile(r'[\u4e00-\u9fff]')


# ---------------------------------------------------------------- 读 pipeline
def bundle_files(bundle):
    d = os.path.join(RES, bundle, 'pipeline')
    if not os.path.isdir(d):
        return []
    out = []
    for dp, _, nms in os.walk(d):
        for nm in sorted(nms):
            if nm.lower().endswith(('.json', '.jsonc')):
                out.append(os.path.join(dp, nm))
    return out


def load_bundle(bundle):
    nodes = {}
    for f in bundle_files(bundle):
        try:
            d = load_jsonc(f)
        except Exception:
            continue
        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(v, dict) and not k.startswith('$'):
                    nodes[k] = v
    return nodes


def effective_nodes(bundles=("base", "resource_win32", "resource_win32_jp")):
    """字段级合并，模拟框架 parse_and_override 的继承语义"""
    eff = {}
    for b in bundles:
        for k, v in load_bundle(b).items():
            m = dict(eff.get(k, {}))
            m.update(v)
            eff[k] = m
    return eff


def reco_of(v):
    r = v.get('recognition')
    if isinstance(r, dict):
        return r.get('type', 'DirectHit'), r.get('param', r)
    if isinstance(r, str):
        return r, v
    return 'DirectHit', v


def action_type(v):
    a = v.get('action')
    if isinstance(a, dict):
        return a.get('type', 'Click')
    if isinstance(a, str):
        return a
    return 'DoNothing'


def expected_of(v):
    t, p = reco_of(v)
    if isinstance(p, dict) and isinstance(p.get('expected'), list):
        return p['expected']
    return None


# ---------------------------------------------------------------- 生成覆盖包
def to_tolerant(s):
    """把简繁有差异的字转成 [简繁] 字符类。

    为什么需要它：OCR 引擎（PPOCR）会把部分繁体字识别成简体，
    实测出现过 '順利完成所有答题' 这种**繁简混排**。
    纯简体、纯繁体候选都可能落空，用字符类才能三种情况全命中。
    只处理字符类之外的字符，绝不破坏原有正则。
    """
    out, depth, i, changed = [], 0, 0, False
    n = len(s)
    m = build_s2t()
    while i < n:
        c = s[i]
        if c == '\\' and i + 1 < n:
            out.append(s[i:i+2]); i += 2; continue
        if c == '[':
            depth += 1; out.append(c); i += 1; continue
        if c == ']':
            if depth > 0: depth -= 1
            out.append(c); i += 1; continue
        if depth == 0:
            t = m.get(c)
            if t and t != c:
                out.append('[' + c + t + ']'); changed = True; i += 1; continue
        out.append(c); i += 1
    return ''.join(out), changed


def _tolerant_ok(tol, *probes):
    """容错式必须仍然能匹配原来的串（以及繁体串），否则不许用"""
    for p in probes:
        if not p:
            continue
        try:
            if not re.search(tol, p):
                return False
        except re.error:
            return False
    return True


def generate_overlay(rules=None, log=print):
    rules = rules or load_rules()
    eff = effective_nodes()
    hold = int(rules.get('选项', {}).get('点击后停顿')
               or rules.get('选项', {}).get('按住时长')
               or HOLD_MS_DEFAULT)
    do_hold = bool(rules.get('选项', {}).get('转按住时长', True))
    keep_click = set(rules.get('选项', {}).get('保持直接点击', []) or [])
    word_rules = [(a, b) for a, b in rules.get('用词', []) if a and b]
    patches = rules.get('节点补丁', {}) or {}

    overlay, n_ocr, n_click, n_word, n_tol = {}, 0, 0, 0, 0
    for name, v in eff.items():
        upd = {}
        exp = expected_of(v)
        if exp:
            new = list(exp)
            added = 0
            for e in exp:
                if not isinstance(e, str):
                    continue
                if CJK.search(e):
                    tol, ch = to_tolerant(e)
                    tc, _ = to_trad(e)
                    # 优先用容错式（覆盖 简体/繁体/混排），校验不过才退回纯繁体
                    if ch and tol not in new and _tolerant_ok(tol, e, tc):
                        new.append(tol); added += 1; n_tol += 1
                    elif tc != e and tc not in new and _tolerant_ok(tc, tc):
                        new.append(tc); added += 1
                for a, b in word_rules:
                    if a in e and b not in new:
                        new.append(b); added += 1; n_word += 1
            if added:
                n_ocr += 1
                upd['expected'] = new

        # 实测：把普通点击改成长按会大量丢点击（同一按钮要重复 3~5 次），
        # 所以改成"普通点击 + 点击后停顿"，既不会点太快，也不会丢。
        if (do_hold and name not in keep_click and action_type(v) == 'Click'
                and not (v.get('pre_delay') == 0 and v.get('post_delay') == 0)):
            cur_post = int(v.get('post_delay') or 0)
            if cur_post < hold:
                upd['post_delay'] = hold
            n_click += 1

        if upd:
            overlay[name] = upd

    # 节点补丁最后覆盖（expected 追加；expected_replace 整体替换）
    for name, fields in patches.items():
        cur = overlay.setdefault(name, {})
        for k, val in fields.items():
            if k == 'expected':
                cur.setdefault('expected', [])
                for e in val:
                    if e not in cur['expected']:
                        cur['expected'].append(e)
            elif k == 'expected_replace':
                cur['expected'] = list(val)
            else:
                cur[k] = val

    log(f"扫描 {len(eff)} 个节点：容错式 {n_tol} 条，用词规则 {n_word} 次，"
        f"点击后停顿 {n_click} 个，最终覆盖 {len(overlay)} 个节点")
    return overlay


def write_overlay(overlay):
    os.makedirs(os.path.dirname(TW_PIPE), exist_ok=True)
    comments = [
        "本文件由「繁中助手」自动生成，请勿手改（改 繁中助手_规则.json 后重新「重建覆盖包」）",
        f"生成时间: {now()}",
        f"节点数: {len(overlay)}",
        "1) OCR 的 expected 追加繁体候选（追加而非替换，简体环境不受影响）",
        "2) UI 的 Click 改成 LongPress + duration（Click 没有 duration 字段，框架写死按住 50ms）",
        "回滚：删除本目录，并在「繁中助手」里点「停用繁中兼容」",
    ]
    body = json.dumps(overlay, ensure_ascii=False, indent=4)[1:-1].strip('\n')
    body = '\n'.join('    ' + ln for ln in body.split('\n'))
    parts = ['{']
    for c in comments:
        parts.append('    // ' + c)
    parts.append(body)
    parts.append('}')
    text = '\n'.join(parts) + '\n'
    tmp = TW_PIPE + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    os.replace(tmp, TW_PIPE)
    return TW_PIPE


# ---------------------------------------------------------------- 任务文件补丁
# 任务定义里的 pipeline_override 会在【运行时】用简体 expected 覆盖资源补丁，
# 所以必须连任务文件一起补繁体，否则资源补丁被顶掉。
# （万象虚境的 ".*第7层" 就是这样把覆盖包顶掉的）
TASKS_DIR = os.path.join(APP, 'tasks')
TASKS_BAK = os.path.join(APP, '繁中助手_任务备份')

_ARR = re.compile(r'"expected"\s*:\s*\[')


def _scan_array(text, start):
    """从 '[' 起扫描一个 JSON 数组，返回 ([(字面量起点, 终点, 值)], 数组结束下标)"""
    i, depth = start + 1, 1
    n = len(text)
    in_str = in_line = in_block = False
    lit_start = -1
    lits = []
    while i < n:
        c = text[i]
        if in_line:
            if c == '\n':
                in_line = False
            i += 1
            continue
        if in_block:
            if c == '*' and i + 1 < n and text[i+1] == '/':
                in_block = False
                i += 2
                continue
            i += 1
            continue
        if in_str:
            if c == '\\':
                i += 2
                continue
            if c == '"':
                lits.append((lit_start, i + 1, text[lit_start+1:i]))
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            lit_start = i
            i += 1
            continue
        if c == '/' and i + 1 < n and text[i+1] == '/':
            in_line = True
            i += 2
            continue
        if c == '/' and i + 1 < n and text[i+1] == '*':
            in_block = True
            i += 2
            continue
        if c == '[':
            depth += 1
        elif c == ']':
            depth -= 1
            if depth == 0:
                return lits, i
        i += 1
    return lits, -1


def patch_task_files(log=print, dry=False):
    """给 tasks/**/*.json 里所有 expected 数组追加繁体候选（幂等，自动备份）"""
    if not os.path.isdir(TASKS_DIR):
        log("找不到 tasks 目录")
        return {}
    stats = {}
    for dp, _, nms in os.walk(TASKS_DIR):
        for nm in sorted(nms):
            if not nm.endswith('.json'):
                continue
            path = os.path.join(dp, nm)
            try:
                text = open(path, encoding='utf-8-sig').read()
            except Exception:
                continue
            inserts, pos = [], 0
            while True:
                m = _ARR.search(text, pos)
                if not m:
                    break
                br = text.index('[', m.start())
                lits, end = _scan_array(text, br)
                if end < 0:
                    break
                existing = set(v for _, _, v in lits)
                for _s, e, val in lits:
                    if not CJK.search(val):
                        continue
                    # 跳过运行时占位符（如 {真我刻印自选优先级_1}），补容错版没有意义
                    if '{' in val or '}' in val:
                        continue
                    tc, _ = to_trad(val)
                    tol, ch = to_tolerant(val)
                    if ch:
                        if tol in existing:        # 已经有容错式，什么都不用做（幂等）
                            continue
                        if _tolerant_ok(tol, val, tc):
                            existing.add(tol)
                            inserts.append((e, ', ' + json.dumps(tol, ensure_ascii=False)))
                            continue
                    if tc != val and tc not in existing and _tolerant_ok(tc, tc):
                        existing.add(tc)
                        inserts.append((e, ', ' + json.dumps(tc, ensure_ascii=False)))
                pos = end + 1
            if not inserts:
                continue
            stats[os.path.relpath(path, TASKS_DIR)] = len(inserts)
            if dry:
                continue
            bak = os.path.join(TASKS_BAK, os.path.relpath(path, TASKS_DIR))
            if not os.path.exists(bak):
                os.makedirs(os.path.dirname(bak), exist_ok=True)
                shutil.copy2(path, bak)
            for at, s in sorted(inserts, key=lambda x: -x[0]):
                text = text[:at] + s + text[at:]
            tmp = path + '.tmp'
            with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
                f.write(text)
            os.replace(tmp, path)
    total = sum(stats.values())
    log(f"任务文件补丁：{len(stats)} 个文件，新增 {total} 条繁体期望" + ("（仅预览）" if dry else ""))
    for k, v in sorted(stats.items(), key=lambda x: -x[1])[:6]:
        log(f"    {v:4d} 条  {k}")
    return stats


def task_patch_status():
    """统计任务文件里已经补过多少条繁体期望"""
    files, items = 0, 0
    if not os.path.isdir(TASKS_DIR):
        return 0, 0
    for dp, _, nms in os.walk(TASKS_DIR):
        for nm in nms:
            if not nm.endswith('.json'):
                continue
            path = os.path.join(dp, nm)
            try:
                text = open(path, encoding='utf-8-sig').read()
            except Exception:
                continue
            pos, cnt = 0, 0
            while True:
                m = _ARR.search(text, pos)
                if not m:
                    break
                br = text.index('[', m.start())
                lits, end = _scan_array(text, br)
                if end < 0:
                    break
                vals = set(v for _, _, v in lits)
                for _, _, v in lits:
                    if not CJK.search(v):
                        continue
                    tol, _ = to_tolerant(v)
                    tc, _ = to_trad(v)
                    if tol in vals or (tc != v and tc in vals):
                        cnt += 1
                pos = end + 1
            if cnt:
                files += 1
                items += cnt
    return files, items


# ---------------------------------------------------------------- 软件内入口
# 在 mab.exe 的任务列表里放两个任务：打开助手 / 重建覆盖包。
# 软件更新后这些会被覆盖掉，所以每次重建都顺手补回来（幂等）。
HELPER_TASK_JSON = os.path.join(TASKS_DIR, "工具", "繁中助手.json")
HELPER_IMPORT = "tasks/工具/繁中助手.json"
HELPER_TASKS = [
    ("打开繁中适配助手", "繁中助手-打开界面", [],
     "在 mab.exe 里直接打开「繁中适配助手」：<br/>· 查看/切换繁中识别<br/>· 维护用词规则（刷新→重置 这类）<br/>"
     "· 日志诊断：找出 OCR 读到却没匹配上的文字，双击即可采纳<br/>· 一键重建覆盖包"),
    ("重建繁中覆盖包", "繁中助手-重建覆盖包", ["--rebuild"],
     "不打开窗口，后台重新生成繁中覆盖包并给任务文件补繁体。<br/>小助手更新之后点这个即可。<br/>"
     "结果写到 繁中助手_重建日志.txt"),
]


def _pythonw():
    p = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return p if os.path.exists(p) else "pythonw.exe"


def ensure_helper_entries(log=print):
    """把「打开助手 / 重建覆盖包」两个任务重新装回软件（幂等）"""
    tool = os.path.join(HERE, "tw_helper.py")   # 脚本实际所在目录（仓库里是 tools/）
    pyw = _pythonw()
    changed = []

    # 1) 任务定义文件
    if not os.path.exists(HELPER_TASK_JSON):
        os.makedirs(os.path.dirname(HELPER_TASK_JSON), exist_ok=True)
        tasks = []
        for name, entry, extra, desc in HELPER_TASKS:
            tasks.append({
                "name": name, "entry": entry, "group": ["单独运行工具"],
                "default_check": False, "description": desc,
                "pipeline_override": {entry: {
                    "action": "Command", "exec": pyw,
                    "args": [tool] + extra, "detach": True}},
            })
        with open(HELPER_TASK_JSON, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"task": tasks, "option": {}}, f, ensure_ascii=False, indent=4)
            f.write("\n")
        changed.append("任务定义文件")

    # 2) interface.json 的 import
    try:
        iface = load_jsonc(IFACE)
        imp = iface.get("import")
        if isinstance(imp, list) and HELPER_IMPORT not in imp:
            imp.insert(0, HELPER_IMPORT)
            iface["import"] = imp
            backup(IFACE)
            with open(IFACE, "w", encoding="utf-8", newline="\n") as f:
                json.dump(iface, f, ensure_ascii=False, indent=4)
                f.write("\n")
            changed.append("interface.json import")
    except Exception as e:
        log("  ⚠ 更新 interface.json 失败：" + str(e))

    # 3) 各配置的任务列表
    import uuid as _uuid
    for f in _conf_files():
        try:
            d = load_jsonc(f)
        except Exception:
            continue
        tasks = d.get("tasks")
        if not isinstance(tasks, list):
            continue
        names = {t.get("name") for t in tasks if isinstance(t, dict)}
        idx = next((i for i, t in enumerate(tasks)
                    if isinstance(t, dict) and t.get("name") == "Resource"), len(tasks) - 1)
        added = 0
        for name, _e, _x, _d in HELPER_TASKS:
            if name in names:
                continue
            idx += 1
            tasks.insert(idx, {"name": name, "item_id": "t_" + _uuid.uuid4().hex,
                               "is_checked": False, "task_option": {}})
            added += 1
        if added:
            d["tasks"] = tasks
            backup(f)
            with open(f, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(d, fh, ensure_ascii=False, indent=4)
                fh.write("\n")
            changed.append(f"{os.path.basename(f)}+{added}")

    if changed:
        log("已装回软件内入口：" + "、".join(changed) + "（重启软件可见）")
    else:
        log("软件内入口已存在，无需处理")
    return changed


# ---------------------------------------------------------------- 繁中开关
# 开关就是【软件左上角「资源」下拉框里选的条目】：
#   「键鼠操作」         = 原版（只认简体）
#   「键鼠操作（繁中）」 = 额外加载 resource_tw（简繁双语都能认）
# 软件把选择结果存在 config/configs/<id>.json 的 "resource" 字段里，
# 所以这里改的也是那个字段 —— 工具按钮和软件下拉框操作的是同一个状态。
TW_SUFFIX = "（繁中）"
CONF_DIR = os.path.join(APP, "config", "configs")
MULTI_CONF = os.path.join(APP, "config", "multi_config.json")


def _conf_files():
    import glob as _glob
    return sorted(_glob.glob(os.path.join(CONF_DIR, "*.json")))


def current_config_path():
    try:
        m = load_jsonc(MULTI_CONF)
        cid = m.get("curr_config_id")
        if cid:
            p = os.path.join(CONF_DIR, cid + ".json")
            if os.path.exists(p):
                return p
    except Exception:
        pass
    fs = _conf_files()
    return fs[0] if fs else None


def _tw_name(name, on):
    base = name[:-len(TW_SUFFIX)] if name.endswith(TW_SUFFIX) else name
    return base + TW_SUFFIX if on else base


def _res_option(d):
    """配置里的资源选择藏在 tasks[] 中 name=='Resource' 那一条的 task_option.resource"""
    tasks = d.get("tasks")
    if not isinstance(tasks, list):
        return None
    for t in tasks:
        if isinstance(t, dict) and t.get("name") == "Resource":
            opt = t.get("task_option")
            if not isinstance(opt, dict):
                opt = {}
                t["task_option"] = opt
            return opt
    return None


def iface_is_enabled():
    p = current_config_path()
    if not p:
        return False
    try:
        opt = _res_option(load_jsonc(p))
        return bool(opt) and str(opt.get("resource", "")).endswith(TW_SUFFIX)
    except Exception:
        return False


def current_resource_name():
    p = current_config_path()
    if not p:
        return ""
    try:
        opt = _res_option(load_jsonc(p))
        return str((opt or {}).get("resource", ""))
    except Exception:
        return ""


def iface_available_names():
    """interface.json 里桌面端可选的资源名（用来确认（繁中）条目确实存在）"""
    try:
        data = load_jsonc(IFACE)
    except Exception:
        return []
    return [r.get("name") for r in data.get("resource", [])
            if "桌面端" in (r.get("controller") or [])]


def iface_set_enabled(on, log=print, all_profiles=False):
    names = set(iface_available_names())
    changed = 0
    # 默认只改当前配置，避免切换资源时把其它已保存配置一起改掉
    targets = _conf_files() if all_profiles else [x for x in [current_config_path()] if x]
    for f in targets:
        try:
            d = load_jsonc(f)
        except Exception:
            continue
        opt = _res_option(d)
        if not opt:
            continue
        r = opt.get("resource")
        if not isinstance(r, str) or not r:
            continue
        new = _tw_name(r, on)
        if new == r:
            continue
        if new not in names:
            log(f"  ⚠ interface.json 里没有资源「{new}」，跳过 {os.path.basename(f)}")
            continue
        opt["resource"] = new
        backup(f)
        tmp = f + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(d, fh, ensure_ascii=False, indent=4)
            fh.write("\n")
        os.replace(tmp, f)
        log(f"  {os.path.basename(f)}: 资源 {r} → {new}")
        changed += 1
    return changed > 0


# ---------------------------------------------------------------- 日志诊断
DEC = json.JSONDecoder()


def _details(line):
    i = line.find('[details=')
    if i < 0:
        return None
    j = line.find('{', i)
    if j < 0:
        return None
    try:
        return DEC.raw_decode(line[j:])[0]
    except Exception:
        return None


def analyze_log(min_score=0.85, limit=400, log=print):
    """
    找出：OCR 在某个节点的 ROI 里读到了高置信文字，但该节点的 expected 全都不匹配。
    这些就是「简繁/用词差异」的候选。
    """
    if not os.path.exists(LOG):
        log("找不到 debug/maafw.log")
        return []
    eff = effective_nodes()
    # 叠加当前覆盖包里的 expected（诊断的是"当前生效配置"）
    if os.path.exists(TW_PIPE):
        try:
            ov = load_jsonc(TW_PIPE)
            for k, v in ov.items():
                if k in eff and isinstance(v.get('expected'), list):
                    t, p = reco_of(eff[k])
                    if isinstance(p, dict):
                        p = dict(p); p['expected'] = v['expected']
                        eff[k] = dict(eff[k]); eff[k]['recognition'] = {'type': t, 'param': p}
        except Exception:
            pass

    def matches(text, exp):
        for e in exp:
            if not isinstance(e, str):
                continue
            try:
                if re.search(e, text):
                    return True
            except re.error:
                if e and e in text:
                    return True
        return False

    def roi_area(v):
        t, p = reco_of(v)
        roi = None
        if isinstance(p, dict):
            roi = p.get('roi')
        if roi is None:
            roi = v.get('roi')
        if isinstance(roi, list) and len(roi) == 4:
            return roi[2] * roi[3]
        return 1280 * 720          # 没写 roi = 全屏，噪声最大

    hits = {}
    scanned = 0
    skipped_wide = set()
    for line in open(LOG, encoding='utf-8', errors='ignore'):
        if 'msg=Node.Recognition.Failed' not in line:
            continue
        if '"algorithm":"OCR"' not in line:
            continue
        scanned += 1
        d = _details(line)
        if not d:
            continue
        rd = d.get('reco_details') or {}
        if rd.get('algorithm') != 'OCR':
            continue
        name = d.get('name')
        v = eff.get(name)
        if not v:
            continue
        exp = expected_of(v)
        if not exp:
            continue
        # 全屏 OCR 节点（如「点击空白位置关闭」）本来就会读到一堆无关文字，不参与诊断
        if roi_area(v) > 300000:
            skipped_wide.add(name)
            continue
        for x in ((rd.get('detail') or {}).get('all') or []):
            if not isinstance(x, dict):
                continue
            t = (x.get('text') or '').strip()
            sc = x.get('score') or 0
            if len(t) < 3 or sc < min_score:
                continue
            if not CJK.search(t):          # 过滤 ×1 / %off 这类噪声
                continue
            if matches(t, exp):
                continue
            key = (name, t)
            if key not in hits:
                hits[key] = {'count': 0, 'score': sc, 'expected': exp}
            hits[key]['count'] += 1

    rows = [{'node': k[0], 'text': k[1], **v} for k, v in hits.items()
            if v['count'] >= 3]                 # 只留反复出现的，过滤一次性噪声
    rows.sort(key=lambda r: -r['count'])

    # 每个节点只留前若干条，并去掉被更长候选包含的短串，避免同一 ROI 的碎词刷屏
    per = {}
    kept = []
    for r in rows:
        lst = per.setdefault(r['node'], [])
        if len(lst) >= 4:
            continue
        if any(r['text'] in o['text'] for o in lst):
            continue
        lst.append(r); kept.append(r)

    log(f"扫描 {scanned} 条 OCR 失败记录，找到 {len(kept)} 组「读到了但没匹配上」的文字（每个节点最多 4 条）")
    if skipped_wide:
        log(f"已跳过 {len(skipped_wide)} 个全屏 OCR 节点（噪声大）：" + "、".join(list(skipped_wide)[:5]))
    return kept[:limit]


VERDICT_RULES = [
    # (结论, 判定依据关键字，出现在该任务命中过的节点名/提示语里)
    ('正常跳过（没东西可做）', ('静默结束', '今日已买满', '已售罄', '已售空', '无可减负条件',
                          '不可领取', '无秘宝', '没货', '无可领取', '已领取', '已领取完毕',
                          '已完成', '已购空', '已满', '未开启', '未开放', '不需要', '无奖励')),
    ('正常收工', ('返回主页后强制结束任务', '领取奖励层-可领取')),
    ('资源不足：金币', ('金币不足',)),
    ('资源不足：休假券/票券/挑战书', ('休假卷', '休假券', '票券不足', '挑战书', '挑战卷', '为0')),
    ('资源不足：次数/体力', ('次数不足', '体力不足', '次数已用完', '资源不足')),
    ('条件不满足：地图/关卡未解锁', ('未開啟', '未啟動', '未解锁', '未通关')),
    ('需要看一下', ()),
]


def classify_runs(log=print):
    """把最近一次运行的每个任务归类：完成 / 正常跳过 / 资源不足 / 需要处理。

    说明：框架的「任務執行失敗」只是说"流程没能自然走完"，并不代表程序出错。
    真正的原因常常是没钱、没券、没次数、地图没解锁这类"没得做"。
    """
    lg = os.path.join(APP, 'debug', 'maafw.log')
    if not os.path.exists(lg):
        log('找不到 maafw.log，跳过结果分类')
        return []
    dec = json.JSONDecoder()

    def details(line):
        i = line.find('[details=')
        j = line.find('{', i)
        if i < 0 or j < 0:
            return None
        try:
            return dec.raw_decode(line[j:])[0]
        except Exception:
            return None

    runs, cur = [], None
    for line in open(lg, encoding='utf-8', errors='ignore'):
        m = re.search(r'task start:.*"entry":"([^"]+)"', line)
        if m:
            cur = {'entry': m.group(1), 'events': [], 't': '', 'acts': 0}
            runs.append(cur)
            continue
        if cur is None or '[msg=Node.' not in line:
            continue
        tm = re.match(r'^\[(\d{4}-\d\d-\d\d) (\d\d:\d\d:\d\d)', line)
        if tm:
            cur['t'] = tm.group(2)
            cur['ts'] = tm.group(1) + ' ' + tm.group(2)
        d = details(line)
        if not d:
            continue
        # 统计真实动作次数：用来抓"日志没报错、但其实什么都没做"的情况
        if '[msg=Node.Action.Succeeded]' in line:
            ad = d.get('action_details') or {}
            if ad.get('action') not in (None, 'DoNothing'):
                cur['acts'] = cur.get('acts', 0) + 1
            continue
        if '[msg=Node.Recognition.Succeeded]' not in line:
            continue
        cur['events'].append((d.get('name') or '', d.get('focus') or {}))

    out = []
    # 失败记录（**带时间**）。只按名字匹配会把"今天早些时候失败过"的任务永远算成失败，
    # 所以必须和任务的时间窗口比对。
    fails = []
    gl = os.path.join(APP, 'debug', 'gui.log')
    if os.path.exists(gl):
        for line in open(gl, encoding='utf-8', errors='ignore'):
            mm = re.search(r'任務執行失敗[：:]\s*(\S+)', line)
            if not mm:
                continue
            tm = re.search(r'\[(\d{4}-\d\d-\d\d )?(\d\d:\d\d:\d\d)', line)
            if tm:
                stamp = ((tm.group(1) or '') + tm.group(2)).strip()
                fails.append((stamp, mm.group(1)))

    # 给每段任务补结束时间（下一段的开始时间）
    for a, b in zip(runs, runs[1:]):
        a['t1'] = b['t']
        a['ts1'] = b.get('ts') or b['t']
    if runs:
        runs[-1]['t1'] = runs[-1].get('t1') or runs[-1]['t']
        runs[-1]['ts1'] = runs[-1].get('ts1') or runs[-1].get('ts') or ''

    def was_failed(r):
        t0 = r.get('ts') or ''
        if not t0:
            return False
        t1 = r.get('ts1') or t0
        for ft, fe in fails:
            if fe != r['entry']:
                continue
            if len(ft) > 8:          # 失败记录带日期：按完整时间戳比较（可跨午夜）
                if t0 <= ft <= t1:
                    return True
            else:                    # 只有时分秒：退回按时间比较
                if t0[11:] <= ft <= t1[11:]:
                    return True
        return False

    for r in runs[-14:]:
        blob = ' '.join(n for n, _ in r['events']) + ' ' + ' '.join(
            str(v) for _, f in r['events'] if isinstance(f, dict) for v in f.values())
        if not was_failed(r):
            verdict = '正常完成'
        else:
            verdict = '需要看一下'
            for name, kws in VERDICT_RULES:
                if kws and any(k in blob for k in kws):
                    verdict = name
                    break
        # 没报错但一个动作都没做 —— 日志漏判，必须人工看
        if verdict == '正常完成' and r.get('acts', 0) == 0:
            verdict = '可疑：没做任何动作'
        skip = ('识别水晶', '成功进入游戏主菜单', '点击返回主菜单')
        meaningful = [n for n, _ in r['events'] if n and n not in skip]
        last = meaningful[-1] if meaningful else '（无节点命中）'
        out.append({'entry': r['entry'], 'time': r['t'], 'verdict': verdict,
                    'last': last, 'acts': r.get('acts', 0)})

    from collections import Counter
    cnt = Counter(o['verdict'] for o in out)
    log('—— 最近这些任务的实际结果 ——')
    for o in out:
        log(f"  {o['time']}  {o['verdict']:<18s} {o['entry']}   "
            f"(动作 {o['acts']} 次，最后停在：{o['last']})")
    log('—— 汇总 ——')
    for k, v in cnt.most_common():
        log(f"  {k}：{v} 个")
    bad = sum(v for k, v in cnt.items() if k in ('需要看一下',))
    helpn = sum(v for k, v in cnt.items() if k.startswith('资源不足') or k.startswith('条件不满足'))
    log(f"说明：框架的「任務執行失敗」只表示流程没自然走完。"
        f"本次 {bad} 个待查、{helpn} 个属于资源/条件不足（正常现象）、"
        f"{cnt.get('正常完成', 0) + cnt.get('正常跳过（没东西可做）', 0) + cnt.get('正常收工', 0)} 个正常。")
    return out


def overlay_stats():
    st = {'exists': os.path.exists(TW_PIPE), 'nodes': 0, 'size': 0, 'mtime': None}
    if st['exists']:
        try:
            st['nodes'] = len(load_jsonc(TW_PIPE))
        except Exception:
            pass
        st['size'] = os.path.getsize(TW_PIPE)
        st['mtime'] = datetime.datetime.fromtimestamp(os.path.getmtime(TW_PIPE)).strftime('%Y-%m-%d %H:%M:%S')
    return st


# ---------------------------------------------------------------- GUI
def main():
    import tkinter as tk
    from tkinter import ttk, messagebox, simpledialog

    root = tk.Tk()
    root.title("繁中适配助手  ·  Maa_bbb")
    root.geometry("980x680")
    root.minsize(880, 600)

    try:
        style = ttk.Style()
        style.theme_use('vista')
    except Exception:
        pass

    out = tk.Text(root, height=9, wrap='word', font=('Consolas', 9))
    out.pack(side='bottom', fill='x', padx=8, pady=(0, 8))
    out.configure(state='disabled')

    def log(msg):
        out.configure(state='normal')
        out.insert('end', msg + '\n')
        out.see('end')
        out.configure(state='disabled')
        root.update_idletasks()

    nb = ttk.Notebook(root)
    nb.pack(fill='both', expand=True, padx=8, pady=8)
    state = {}

    # ---------------- Tab 1: 概览 ----------------
    t1 = ttk.Frame(nb); nb.add(t1, text='  概览 / 开关  ')
    info = tk.Text(t1, height=12, wrap='word', font=('Microsoft YaHei UI', 10))
    info.pack(fill='both', expand=True, padx=10, pady=10)
    info.configure(state='disabled')

    def refresh():
        st = overlay_stats()
        try:
            en = iface_is_enabled()
        except Exception as e:
            en = f"读取失败 {e}"
        cur_name = ""
        try:
            cp = current_config_path()
            if cp:
                cfg = load_jsonc(cp)
            _opt = _res_option(cfg) or {}
            cur_name = str(_opt.get("resource", "") or "")
        except Exception:
            pass
        lines = []
        lines.append(f"游戏目录：{APP}")
        lines.append(f"当前资源（软件左上角下拉框）：{cur_name or '(未知)'}")
        lines.append(f"繁中识别：{'✅ 已开启' if en is True else '⬜ 已关闭' if en is False else en}")
        lines.append("  ↑ 想切换：直接在软件左上角「资源」里选「键鼠操作（繁中）」或「键鼠操作」，")
        lines.append("     点下面的按钮也会改同一个设置（两边等价）。改完重启任务生效。")
        lines.append(f"覆盖包：{'存在' if st['exists'] else '不存在'}   节点数 {st['nodes']}   大小 {st['size']/1024:.0f} KB")
        if st['mtime']:
            lines.append(f"覆盖包生成时间：{st['mtime']}")
        try:
            eff = effective_nodes()
            ocr = sum(1 for v in eff.values() if reco_of(v)[0] == 'OCR')
            lines.append(f"基础节点 {len(eff)} 个，其中 OCR 节点 {ocr} 个")
        except Exception as e:
            lines.append(f"节点统计失败：{e}")
        r = load_rules()
        lines.append(f"用词规则 {len(r['用词'])} 条，节点补丁 {len(r['节点补丁'])} 个，按住时长 {r['选项'].get('按住时长')} ms")
        try:
            tf, ti = task_patch_status()
            lines.append(f"任务文件补丁：{tf} 个文件 / {ti} 条（运行时覆盖会用这些，必须补）")
        except Exception as e:
            lines.append(f"任务文件补丁统计失败：{e}")
        lines.append("")
        lines.append("提示：改完规则要点「重建覆盖包」，然后重启小助手才生效。")
        info.configure(state='normal'); info.delete('1.0', 'end')
        info.insert('1.0', '\n'.join(lines)); info.configure(state='disabled')

    bar = ttk.Frame(t1); bar.pack(fill='x', padx=10, pady=(0, 10))

    def do_enable(on):
        try:
            if iface_set_enabled(on, log):
                log("已切换资源。重启小助手（或重新开始任务）后生效。")
            else:
                log("无需改动（状态已一致）。")
            refresh()
        except Exception as e:
            log("失败：" + str(e))
            messagebox.showerror("失败", str(e))

    ttk.Button(bar, text='切换到 繁中 资源', command=lambda: do_enable(True)).pack(side='left')
    ttk.Button(bar, text='切换回 原版 资源', command=lambda: do_enable(False)).pack(side='left', padx=6)

    def do_build():
        try:
            ov = generate_overlay(log=log)
            p = write_overlay(ov)
            log(f"已写入 {p}")
            # 任务定义里的 expected 会在运行时覆盖资源补丁，必须一起补
            patch_task_files(log=log)
            ensure_helper_entries(log=log)
            if not iface_is_enabled():
                if messagebox.askyesno("还没切到繁中资源",
                                       "覆盖包已生成，但当前资源不是「（繁中）」那个。\n现在自动切过去吗？"):
                    iface_set_enabled(True, log)
            refresh()
            messagebox.showwarning(
                "重建完成 —— 必须重启小助手",
                "覆盖包已更新。\n\n"
                "⚠ 小助手只在【启动时】加载一次资源，之后改文件它不会再读。\n\n"
                "所以：请完全退出 mab.exe（不是点「停止」，要关掉整个窗口），\n"
                "再重新打开，改动才会生效。")
            log("⚠ 记住：要完全退出 mab.exe 再重新打开，改动才生效。")
        except Exception as e:
            log("重建失败：" + str(e))
            log(traceback.format_exc())
            messagebox.showerror("重建失败", str(e))

    ttk.Button(bar, text='重建覆盖包', command=do_build).pack(side='left', padx=6)
    ttk.Button(bar, text='刷新状态', command=refresh).pack(side='left')

    # ---------------- Tab 2: 用词规则 ----------------
    t2 = ttk.Frame(nb); nb.add(t2, text='  用词规则  ')
    ttk.Label(t2, text='有些地方繁中不是「字形不同」而是「用词不同」，比如 刷新→重置、倒计时→倒數計時。\n'
                       '字符转换修不到，在这里加一条即可：节点期望里出现「简体」时，会自动追加「繁体」。').pack(anchor='w', padx=10, pady=8)
    cols = ('simp', 'trad')
    tv2 = ttk.Treeview(t2, columns=cols, show='headings', height=14)
    tv2.heading('simp', text='简体（节点里写的）')
    tv2.heading('trad', text='繁中（游戏里显示的）')
    tv2.column('simp', width=380); tv2.column('trad', width=380)
    tv2.pack(fill='both', expand=True, padx=10, pady=(0, 8))

    def refresh_words():
        tv2.delete(*tv2.get_children())
        for a, b in load_rules()['用词']:
            tv2.insert('', 'end', values=(a, b))

    def add_word():
        a = simpledialog.askstring("添加用词规则", "简体文字（节点 expected 里出现的）：", parent=root)
        if not a:
            return
        b = simpledialog.askstring("添加用词规则", "繁中文字（游戏里实际显示的）：", parent=root)
        if not b:
            return
        r = load_rules(); r['用词'].append([a.strip(), b.strip()]); save_rules(r)
        refresh_words(); log(f"已添加用词规则：{a} → {b}"); refresh()

    def del_word():
        sel = tv2.selection()
        if not sel:
            return
        vals = tv2.item(sel[0], 'values')
        r = load_rules()
        r['用词'] = [x for x in r['用词'] if [x[0], x[1]] != [vals[0], vals[1]]]
        save_rules(r); refresh_words(); log(f"已删除用词规则：{vals[0]} → {vals[1]}"); refresh()

    b2 = ttk.Frame(t2); b2.pack(fill='x', padx=10, pady=(0, 10))
    ttk.Button(b2, text='添加', command=add_word).pack(side='left')
    ttk.Button(b2, text='删除选中', command=del_word).pack(side='left', padx=6)

    # ---------------- Tab 3: 节点补丁 ----------------
    t3 = ttk.Frame(nb); nb.add(t3, text='  节点补丁  ')
    ttk.Label(t3, text='给指定节点强行追加期望文字，或限制命中次数（防止连点跑飞）。\n'
                       '例：后勤终端-已进入后勤终端 追加「重置倒數計時」；模拟作战室-减负确认 限制 max_hit=2。').pack(anchor='w', padx=10, pady=8)
    tv3 = ttk.Treeview(t3, columns=('node', 'fields'), show='headings', height=12)
    tv3.heading('node', text='节点'); tv3.heading('fields', text='补丁内容')
    tv3.column('node', width=340); tv3.column('fields', width=560)
    tv3.pack(fill='both', expand=True, padx=10, pady=(0, 8))

    def refresh_patch():
        tv3.delete(*tv3.get_children())
        for k, v in sorted(load_rules()['节点补丁'].items()):
            tv3.insert('', 'end', values=(k, json.dumps(v, ensure_ascii=False)))

    def add_patch():
        names = sorted(effective_nodes().keys())
        win = tk.Toplevel(root); win.title("添加/修改节点补丁"); win.geometry("720x260")
        win.transient(root); win.grab_set()
        ttk.Label(win, text='节点名（可输入筛选）').grid(row=0, column=0, sticky='w', padx=8, pady=6)
        cb = ttk.Combobox(win, values=names, width=72)
        cb.grid(row=0, column=1, columnspan=3, sticky='we', padx=8, pady=6)
        ttk.Label(win, text='追加期望（逗号分隔，可空）').grid(row=1, column=0, sticky='w', padx=8, pady=6)
        e_exp = ttk.Entry(win, width=72)
        e_exp.grid(row=1, column=1, columnspan=3, sticky='we', padx=8, pady=6)
        ttk.Label(win, text='max_hit（整数，可空）').grid(row=2, column=0, sticky='w', padx=8, pady=6)
        e_hit = ttk.Entry(win, width=18)
        e_hit.grid(row=2, column=1, sticky='w', padx=8, pady=6)
        ttk.Label(win, text='enabled（留空=不改）').grid(row=2, column=2, sticky='e', padx=8)
        e_en = ttk.Combobox(win, values=['', 'true', 'false'], width=8)
        e_en.grid(row=2, column=3, sticky='w', padx=8)

        def ok():
            name = cb.get().strip()
            if not name:
                messagebox.showwarning("提示", "请选择节点", parent=win); return
            fields = {}
            ex = [x.strip() for x in e_exp.get().split(',') if x.strip()]
            if ex:
                fields['expected'] = ex
            hit = e_hit.get().strip()
            if hit:
                try:
                    fields['max_hit'] = int(hit)
                except ValueError:
                    messagebox.showwarning("提示", "max_hit 必须是整数", parent=win); return
            en = e_en.get().strip()
            if en:
                fields['enabled'] = (en == 'true')
            if not fields:
                messagebox.showwarning("提示", "至少填一项", parent=win); return
            r = load_rules()
            cur = r['节点补丁'].get(name, {})
            for k, v in fields.items():
                if k == 'expected':
                    cur.setdefault('expected', [])
                    for x in v:
                        if x not in cur['expected']:
                            cur['expected'].append(x)
                else:
                    cur[k] = v
            r['节点补丁'][name] = cur
            save_rules(r); refresh_patch(); refresh()
            log(f"已更新节点补丁：{name} -> {json.dumps(fields, ensure_ascii=False)}")
            win.destroy()

        ttk.Button(win, text='保存', command=ok).grid(row=3, column=2, sticky='e', padx=8, pady=12)
        ttk.Button(win, text='取消', command=win.destroy).grid(row=3, column=3, sticky='w', padx=8, pady=12)

    def del_patch():
        sel = tv3.selection()
        if not sel:
            return
        name = tv3.item(sel[0], 'values')[0]
        r = load_rules(); r['节点补丁'].pop(name, None)
        save_rules(r); refresh_patch(); refresh(); log(f"已删除节点补丁：{name}")

    b3 = ttk.Frame(t3); b3.pack(fill='x', padx=10, pady=(0, 10))
    ttk.Button(b3, text='添加/修改', command=add_patch).pack(side='left')
    ttk.Button(b3, text='删除选中', command=del_patch).pack(side='left', padx=6)

    # ---------------- Tab 4: 日志诊断 ----------------
    t4 = ttk.Frame(nb); nb.add(t4, text='  日志诊断  ')
    ttk.Label(t4, text='扫描 debug/maafw.log：把「OCR 明明读到了、但这个节点没匹配上」的文字挖出来。\n'
                       '双击某一行，直接把它加进该节点的期望补丁（然后回「概览」点重建）。').pack(anchor='w', padx=10, pady=8)
    tv4 = ttk.Treeview(t4, columns=('cnt', 'node', 'text', 'exp'), show='headings', height=13)
    for c, t, w in (('cnt', '次数', 60), ('node', '节点', 260), ('text', '实际读到', 300), ('exp', '当前期望(简)', 300)):
        tv4.heading(c, text=t); tv4.column(c, width=w)
    tv4.pack(fill='both', expand=True, padx=10, pady=(0, 8))
    state['rows'] = []

    def do_scan():
        try:
            classify_runs(log=log)
            rows = analyze_log(log=log)
            state['rows'] = rows
            tv4.delete(*tv4.get_children())
            for r in rows:
                tv4.insert('', 'end', values=(r['count'], r['node'], r['text'],
                                              json.dumps(r['expected'][:3], ensure_ascii=False)))
            log(f"共 {len(rows)} 行。双击可快速补进节点期望。")
        except Exception as e:
            log("诊断失败：" + str(e)); log(traceback.format_exc())

    def on_dbl(_e):
        sel = tv4.selection()
        if not sel:
            return
        cnt, node, text, _ = tv4.item(sel[0], 'values')
        r = load_rules()
        cur = r['节点补丁'].setdefault(node, {})
        cur.setdefault('expected', [])
        if text in cur['expected']:
            log(f"{node} 已有该期望：{text}")
            return
        cur['expected'].append(text)
        save_rules(r); refresh_patch(); refresh()
        log(f"✅ 已把 {node} 的期望追加：{text}  （记得回「概览」点重建覆盖包）")

    tv4.bind('<Double-1>', on_dbl)
    b4 = ttk.Frame(t4); b4.pack(fill='x', padx=10, pady=(0, 10))
    ttk.Button(b4, text='扫描日志', command=do_scan).pack(side='left')
    ttk.Label(b4, text='筛选：').pack(side='left', padx=(14, 4))
    e_filter = ttk.Entry(b4, width=28)
    e_filter.pack(side='left')

    def do_filter(*_):
        kw = e_filter.get().strip()
        tv4.delete(*tv4.get_children())
        for r in state['rows']:
            if kw and kw not in r['node'] and kw not in r['text']:
                continue
            tv4.insert('', 'end', values=(r['count'], r['node'], r['text'],
                                          json.dumps(r['expected'][:3], ensure_ascii=False)))

    e_filter.bind('<KeyRelease>', do_filter)
    ttk.Label(b4, text='（双击某行 = 加入该节点期望）').pack(side='left', padx=10)

    refresh(); refresh_words(); refresh_patch()
    log(f"就绪。{now()}")
    log("建议顺序：日志诊断 → 双击采纳 → 概览点「重建覆盖包」 → 重启小助手")
    root.mainloop()


def cli_rebuild():
    """无界面重建：供 mab.exe 任务列表里的「重建繁中覆盖包」调用"""
    lines = []

    def log(s):
        lines.append(str(s))

    ok = True
    try:
        ov = generate_overlay(log=log)
        p = write_overlay(ov)
        log(f"已写入覆盖包: {p}")
        patch_task_files(log=log)
        ensure_helper_entries(log=log)
        log("完成。")
        log("⚠ 必须【完全退出 mab.exe】再重新打开才生效（它只在启动时加载资源，点「停止」不算）。")
    except Exception:
        ok = False
        log("失败：\n" + traceback.format_exc())
    logpath = os.path.join(APP, "繁中助手_重建日志.txt")
    try:
        with open(logpath, "w", encoding="utf-8") as f:
            f.write(f"重建时间 {now()}  结果: {'成功' if ok else '失败'}\n")
            f.write("\n".join(lines) + "\n")
    except Exception:
        pass
    return 0 if ok else 1


if __name__ == '__main__':
    if '--rebuild' in sys.argv:
        sys.exit(cli_rebuild())
    if '--status' in sys.argv:
        print(json.dumps({
            "resource": current_resource_name(),
            "繁中": iface_is_enabled(),
            "覆盖包节点": overlay_stats()["nodes"],
        }, ensure_ascii=False))
        sys.exit(0)
    main()
