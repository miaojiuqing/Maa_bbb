"""用官方 Windows 运行包组装本地测试版；--sync-only 只同步源码和资源。"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "install"
RUNTIME_NAME = "Maa_bbb-win-x86_64-v1.13.6.zip"
RUNTIME_URL = (
    "https://github.com/miaojiuqing/Maa_bbb/releases/download/v1.13.6/"
    + RUNTIME_NAME
)
RUNTIME_SHA256 = "c9d2addb6c09d9e1ce51c0906213e2013d3ea9bbcffd3c38f0cf3ec6c9bbca36"
LOCAL_VERSION = "v1.13.6-local-elysian"


def require_stopped() -> None:
    environment = os.environ.copy()
    environment["MAA_LOCAL_TEST_EXE"] = str(INSTALL / "识宝小助手.exe")
    command = (
        "Get-Process -ErrorAction Stop | "
        "Where-Object { $_.Path -eq $env:MAA_LOCAL_TEST_EXE -or "
        "($_.Path -and $_.Path -eq ($env:MAA_LOCAL_TEST_EXE -replace '识宝小助手.exe$', 'MFW.exe')) } | "
        "Select-Object -ExpandProperty Id; exit 0"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", command],
        env=environment, capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("无法检查测试版进程，请确认它已退出后重试。")
    if result.stdout.strip():
        raise RuntimeError("本地测试版正在运行，请先停止任务并退出小助手，再同步。")


def configure_local_updates() -> None:
    path = INSTALL / "config/config.json"
    settings = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    settings.setdefault("Update", {})["auto_update"] = False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, ensure_ascii=False, indent=4), encoding="utf-8")


def prepare_runtime() -> None:
    archive = ROOT / "deps" / "local-runtime" / RUNTIME_NAME
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        print(f"下载官方运行包：{RUNTIME_NAME}", flush=True)
        partial = archive.with_suffix(".zip.part")
        with urllib.request.urlopen(RUNTIME_URL, timeout=60) as response:
            with partial.open("wb") as output:
                shutil.copyfileobj(response, output)
        partial.replace(archive)
    with archive.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    if digest != RUNTIME_SHA256:
        raise RuntimeError(f"运行包校验失败，请重新下载：{archive}")
    if not any((INSTALL / name).is_file() for name in ("MFW.exe", "识宝小助手.exe")):
        if INSTALL.exists() and any(INSTALL.iterdir()):
            raise RuntimeError("install 非空且缺少主程序，请先检查目录内容。")
        with zipfile.ZipFile(archive) as package:
            for entry in package.infolist():
                target = (INSTALL / entry.filename).resolve()
                if not target.is_relative_to(INSTALL.resolve()):
                    raise RuntimeError("运行包包含越界路径。")
            package.extractall(INSTALL)


def framework_version() -> str:
    library = ctypes.CDLL(str(INSTALL / "runtimes/win-x64/MaaFramework.dll"))
    library.MaaVersion.restype = ctypes.c_char_p
    return library.MaaVersion().decode().removeprefix("v")


def align_frontend_framework() -> None:
    """前端优先加载maafw目录，不能只更新agent/runtimes里的库。"""
    runtime = INSTALL / "runtimes/win-x64"
    frontend = INSTALL / "maafw"
    if frontend.is_symlink() or not frontend.resolve().is_relative_to(INSTALL.resolve()):
        raise RuntimeError("maafw 必须位于本地测试目录内。")
    source_library = runtime / "MaaFramework.dll"
    frontend_library = frontend / "MaaFramework.dll"
    if not source_library.is_file() or not frontend_library.is_file():
        raise RuntimeError("本地运行包缺少 MaaFramework 库。")

    def digest(path):
        with path.open("rb") as handle:
            return hashlib.file_digest(handle, "sha256").hexdigest()

    if digest(source_library) == digest(frontend_library):
        return
    backup = ROOT / "deps/local-runtime" / ("frontend-framework-" + digest(frontend_library)[:12])
    if not backup.exists():
        shutil.copytree(frontend, backup)
    # 同步配套DLL，包括OCR/推理依赖和插件，避免仅替换主库造成版本混用。
    for source in runtime.rglob("*.dll"):
        target = frontend / source.relative_to(runtime)
        if target.is_symlink() or not target.resolve().is_relative_to(frontend.resolve()):
            raise RuntimeError(f"拒绝覆盖测试目录外的运行库：{target.name}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    print("已对齐前端与agent的MaaFramework运行库，原前端库已备份。", flush=True)


def replace_generated_tree(name: str) -> None:
    target = INSTALL / name
    resolved = target.resolve()
    if target.is_symlink() or not resolved.is_relative_to(INSTALL.resolve()):
        raise RuntimeError(f"拒绝覆盖指向测试目录外的路径：{name}")
    if target.exists():
        shutil.rmtree(target)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sync-only", action="store_true", help="保留运行环境，只同步修改")
    args = parser.parse_args()
    if platform.system() != "Windows" or platform.machine().lower() not in ("amd64", "x86_64"):
        raise RuntimeError("此本地脚本面向 Windows x64。")
    if INSTALL.is_symlink() or INSTALL.resolve() != ROOT.resolve() / "install":
        raise RuntimeError("install 必须是当前仓库内的真实目录。")
    require_stopped()
    python_exe = INSTALL / "python/python.exe"
    if args.sync_only:
        if not python_exe.is_file():
            raise RuntimeError("请先不带 --sync-only 执行一次，准备运行环境。")
    else:
        prepare_runtime()
    align_frontend_framework()
    if not args.sync_only:
        if not python_exe.is_file():
            subprocess.run(
                [sys.executable, str(ROOT / "tools/install_python.py"), str(python_exe.parent)],
                cwd=ROOT,
                check=True,
            )
        subprocess.run(
            [str(python_exe), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt"),
             f"MaaFw=={framework_version()}"],
            cwd=ROOT,
            check=True,
        )

    # 复用上游打包函数；运行库由官方包提供，本机配置和日志不参与同步。
    sys.argv = ["install.py", LOCAL_VERSION, "win", "x64"]
    import install as installer
    from rename_main_executable import rename_main_executable, sync_file_list

    for name in ("agent", "resource", "tasks", "characters", "docs"):
        replace_generated_tree(name)
    installer.install_resource()
    installer.install_chores()
    installer.install_agent()
    shutil.copytree(ROOT / "docs", INSTALL / "docs")
    import jsonc

    interface_path = INSTALL / "interface.json"
    interface = jsonc.loads(interface_path.read_text(encoding="utf-8"))
    interface["title"] = f"识宝小助手 | 本地乐土测试版 | {LOCAL_VERSION}"
    interface_path.write_text(jsonc.dumps(interface, ensure_ascii=False, indent=4), encoding="utf-8")
    configure_local_updates()
    result = rename_main_executable("win")
    if result:
        sync_file_list(*result)

    # 使用与主程序同版本的 MaaFramework 生成资源校验值。
    subprocess.run(
        [str(python_exe), "-X", "utf8", str(ROOT / "tools/ci/gen_resource_hash.py"),
         str(interface_path), "--root", str(INSTALL)],
        cwd=ROOT,
        check=True,
    )
    print(f"本地测试版已同步：{INSTALL / '识宝小助手.exe'}", flush=True)


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    main()
