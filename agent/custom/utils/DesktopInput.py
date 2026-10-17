"""桌面端输入修饰：鼠标拖动前按住 Alt。

安卓端只有触摸，没有修饰键。桌面端（键鼠/纯键盘）必须先把 Alt 按住，
鼠标拖拽才会变成拖动视角——见 真寻路处理逻辑.json:23 的「键鼠按住ALT后滑动视角」。

这两个节点只定义在 resource_win32 系列资源包里，安卓端 context.get_node_data
探测不到 → 整段跳过，行为与原来完全一致。

注意顺序：必须先松开摇杆/结束滑动，再松开 Alt。反过来会让鼠标停在拖动状态，
所以调用方用 try/finally 显式配对，这里不做上下文管理器。
"""

HOLD_NODE = "桌面-按住Alt"
RELEASE_NODE = "桌面-松开Alt"


def _node(context, name):
    try:
        return context.get_node_data(name)
    except Exception:
        return None


def available(context):
    """只有桌面端资源包才注册这两个节点；安卓端返回 False。"""
    return bool(_node(context, HOLD_NODE) and _node(context, RELEASE_NODE))


def hold(context):
    """按住 Alt，返回是否真的按下了（安卓端恒为 False）。"""
    if not available(context):
        return False
    try:
        result = context.run_action(HOLD_NODE)
    except Exception as exc:
        print(f"DesktopInput: 按住 Alt 失败：{exc}", flush=True)
        return False
    return bool(result and getattr(result, "success", True))


def release(context, held):
    """松开 Alt；held 为假时什么都不做。"""
    if not held:
        return
    try:
        context.run_action(RELEASE_NODE)
    except Exception as exc:
        print(f"DesktopInput: 松开 Alt 失败：{exc}", flush=True)
