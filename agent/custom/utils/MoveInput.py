"""桌面端移动输入：用 WASD 键代替屏幕摇杆。

安卓端只有屏幕摇杆（post_touch_down/move/up），桌面端没有摇杆，只能按 WASD。
这些键位节点只定义在 resource_win32 系列资源包里，安卓端探测不到 →
MoveInput.walk 返回 False，调用方继续走原来的摇杆逻辑，安卓行为与现在完全一致。

和 DesktopInput 一样按"节点是否存在"判定平台，不看 controller.type，
这样用户自建的资源包只要提供同名节点即可生效。

注意顺序：必须先松开方向键再结束这一小步，否则角色会一直走下去。
"""
import time

HOLD_NODE = "桌面-按住{key}"
RELEASE_NODE = "桌面-松开{key}"
# 摇杆行程 dx/dy（像素）折算成 WASD 的判定死区，避免微小偏移被当成移动。
DEAD_ZONE = 18
# 桌面端按键是全速，时长按摇杆比例折减，避免一步跨过头导致来回修正。
DURATION_SCALE = 0.20
MIN_DURATION = 0.06
MAX_DURATION = 0.14
ARROWS = ("W", "A", "S", "D")


def _node(context, name):
    try:
        return context.get_node_data(name)
    except Exception:
        return None


def available(context):
    """只有桌面端资源包才注册 WASD 节点；安卓端返回 False。"""
    return all(_node(context, HOLD_NODE.format(key=key)) for key in ARROWS)


def keys_for(dx, dy):
    """只按一个键：前进/后退走 W/S，纯横移才走 A/D。

    摇杆的 dx 只是"边走边微调"，换成键盘后会变成整速斜走（W+D 就是 45°），
    实测偏移过大且需要反复重寻路，所以这里放弃斜向，方向差异交给转视角修正。
    """
    if dy < -DEAD_ZONE:
        return ["W"]
    if dy > DEAD_ZONE:
        return ["S"]
    if dx > DEAD_ZONE:
        return ["D"]
    if dx < -DEAD_ZONE:
        return ["A"]
    return []


def _hold(context, key):
    try:
        result = context.run_action(HOLD_NODE.format(key=key))
    except Exception as exc:
        print(f"MoveInput: 按下 {key} 失败：{exc}", flush=True)
        return False
    return bool(result and getattr(result, "success", True))


def _release(context, key):
    try:
        context.run_action(RELEASE_NODE.format(key=key))
    except Exception as exc:
        print(f"MoveInput: 松开 {key} 失败：{exc}", flush=True)


def release_all(context):
    """兜底：异常/停止时把四个方向键都松开，避免角色一直走。"""
    for key in ARROWS:
        _release(context, key)


def walk(context, dx=0, duration=.6, dy=-76, stop_event=None):
    """按 WASD 走一小步；返回 False 表示当前不是桌面端，调用方应走摇杆逻辑。"""
    if not available(context):
        return False
    keys = keys_for(int(dx), int(dy))
    if not keys:
        return True                 # 死区内：本步不动，但不能回退去拖摇杆
    step = min(MAX_DURATION, max(MIN_DURATION, float(duration) * DURATION_SCALE))
    pressed = []
    try:
        # 先松开四个方向键：极端情况下（上一步异常退出）残留的按下会让这一步变成双键斜走。
        for key in ARROWS:
            if key not in keys:
                _release(context, key)
        for key in keys:
            if _hold(context, key):
                pressed.append(key)
        end = time.monotonic() + step
        while time.monotonic() < end:
            if stop_event is not None and stop_event.is_set():
                break
            time.sleep(.02)
        return True
    finally:
        for key in pressed:
            _release(context, key)
