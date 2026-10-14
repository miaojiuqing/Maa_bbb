import subprocess
import json
import ipaddress
from pathlib import Path


def _online(adb_path):
    out = subprocess.check_output([str(adb_path), 'devices'], text=True,
                                  encoding='utf-8', errors='ignore', timeout=5)
    return [parts[0] for line in out.splitlines()
            if len(parts := line.split()) == 2 and parts[1] == 'device']


def _configured_guest(adb_path, configured):
    """只读取当前 MuMu 安装中与配置端口匹配的实例，不扫描局域网。"""
    try:
        port = int(configured.rsplit(':', 1)[1])
    except (ValueError, IndexError):
        return None
    configs = Path(adb_path).resolve().parent.parent / 'vms'
    candidates = []
    guests = []
    for path in configs.glob('*/configs/vm_config.json'):
        try:
            data = json.loads(path.read_text(encoding='utf-8-sig'))
            entry = data['vm']['nat']['port_forward']['adb']
            addr = ipaddress.ip_address(entry['guest_ip'])
            if addr.is_private:
                guests.append(f'{addr}:5555')
            if int(entry['host_port']) == port and addr.is_private:
                candidates.append(f'{addr}:5555')
        except (OSError, ValueError, KeyError, TypeError):
            continue
    if len(candidates) == 1:
        return candidates[0]
    # 原助手可能保存的是上一次的内部地址。只有单实例安装才允许回退。
    try:
        previous = ipaddress.ip_address(configured.rsplit(':', 1)[0])
        if port == 5555 and previous.is_private and not previous.is_loopback and len(guests) == 1:
            return guests[0]
    except ValueError:
        pass
    return None

def resolve_adb_address(adb_path, configured):
    """恢复 MuMu 重启后变化的内部地址；多个在线设备不能任取第一台。"""
    try:
        online = _online(adb_path)
        if configured in online:return configured
        guest = _configured_guest(adb_path, configured)
        if guest:
            if guest not in online:
                subprocess.run([str(adb_path), 'connect', guest], capture_output=True, timeout=6)
                online = _online(adb_path)
            if guest in online:return guest
        if len(online) == 1:return online[0]
        if len(online) > 1:
            raise RuntimeError('检测到多台在线设备，但无法确认配置对应的 MuMu 实例')
    except RuntimeError:
        raise
    except Exception:
        pass
    return configured
