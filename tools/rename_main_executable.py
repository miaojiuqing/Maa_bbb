"""把发布包内的 MFW 主程序重命名为本项目显示名（Windows: 识宝小助手.exe）。

MFW 主程序通过 ``sys.executable`` / ``sys.argv[0]`` 定位自身
（app/utils/install_paths.py 的 ``resolve_install_anchor``），其外置更新器
（MFW-Updater）也专门提供 ``--startup-executable-name``（帮助文本：
「触发更新时的主程序文件名（用于更新后恢复原名称）」），因此发布时自定义
主程序文件名属于官方支持的用法。

用法::

    python tools/rename_main_executable.py [os]

``os`` 取 win / linux / macos，省略时按当前平台推断。
Windows 得到 `install/识宝小助手.exe`，Linux 得到 `install/识宝小助手`；
macOS 主程序是 `MFW.app`（改名要同步 Info.plist 的 CFBundleExecutable 与
ad-hoc 签名），默认保持原样。
"""

from __future__ import annotations

import platform
import sys
from pathlib import Path

# GitHub Actions 的 Windows runner 上 sys.stdout 默认编码是 cp1252，打印中文会抛
# UnicodeEncodeError 让整个 CI 步骤失败，这里强制用 UTF-8 输出。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

working_dir = Path(__file__).resolve().parent.parent
install_path = working_dir / "install"

# 显示名（不含扩展名）
APP_DISPLAY_NAME = "识宝小助手"

_SYSTEM_ALIASES = {
    "windows": "win",
    "win32": "win",
    "win64": "win",
    "win": "win",
    "linux": "linux",
    "darwin": "macos",
    "macos": "macos",
    "osx": "macos",
    "mac": "macos",
}


def current_system(argv: list[str] | None = None) -> str:
    """CI 传 matrix.os；本地按 platform 推断。"""
    source = list(sys.argv[1:] if argv is None else argv)
    raw = source[0].strip() if source and source[0].strip() else platform.system()
    return _SYSTEM_ALIASES.get(raw.lower(), raw.lower())


def rename_main_executable(os_name: str | None = None) -> tuple[str, str] | None:
    """按平台重命名主程序，返回 (原名, 新名)；无需改名时返回 None。"""
    system = (os_name or current_system()).lower()
    if system == "win":
        old_name, new_name = "MFW.exe", f"{APP_DISPLAY_NAME}.exe"
    elif system == "linux":
        old_name, new_name = "MFW", APP_DISPLAY_NAME
    else:
        print(f"[skip] {system}: 主程序是 MFW.app，改名需同步 Info.plist 与签名，保持原样")
        return None

    old_path = install_path / old_name
    new_path = install_path / new_name

    if not old_path.exists():
        if new_path.exists():
            print(f"[info] 主程序已是 {new_name}")
            return old_name, new_name
        print(f"[warn] {old_path} 不存在，跳过改名")
        return None
    if new_path.exists():
        raise SystemExit(f"[ERROR] {old_path} 与 {new_path} 同时存在，请先清理 install/")

    old_path.rename(new_path)
    print(f"[info] 主程序已重命名: {old_name} -> {new_name}")
    return old_name, new_name


def sync_file_list(old_name: str, new_name: str) -> None:
    """同步 MFW 官方生成的 file_list.txt 中的主程序条目（保持 LF 换行）。"""
    file_list = install_path / "file_list.txt"
    if not file_list.is_file():
        print(f"[info] 未找到 {file_list}，跳过 file_list.txt 同步")
        return

    old_entry, new_entry = f"./{old_name}", f"./{new_name}"
    lines = file_list.read_text(encoding="utf-8").splitlines()
    hits = 0
    updated: list[str] = []
    for line in lines:
        if line.strip() == old_entry:
            updated.append(new_entry)
            hits += 1
        else:
            updated.append(line)

    if hits:
        file_list.write_text("\n".join(updated) + "\n", encoding="utf-8")
    print(f"[info] file_list.txt: {old_entry} -> {new_entry}（{hits} 行）")


def main() -> int:
    if not install_path.is_dir():
        raise SystemExit(f"[ERROR] 未找到安装目录 {install_path}")
    result = rename_main_executable()
    if result is not None:
        sync_file_list(*result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
