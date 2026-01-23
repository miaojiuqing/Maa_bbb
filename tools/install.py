from pathlib import Path

import os
import shutil
import sys
import json
import jsonc

from configure import configure_ocr_model


working_dir = Path(__file__).parent.parent
install_path = working_dir / Path("install")
version = len(sys.argv) > 1 and sys.argv[1] or "v0.0.1"


def install_deps():
    if not (working_dir / "deps" / "bin").exists():
        print('Please download the MaaFramework to "deps" first.')
        print('请先下载 MaaFramework 到 "deps"。')
        sys.exit(1)

    shutil.copytree(
        working_dir / "deps" / "bin",
        install_path,
        ignore=shutil.ignore_patterns(
            "*MaaDbgControlUnit*",
            "*MaaThriftControlUnit*",
            "*MaaRpc*",
            "*MaaHttp*",
        ),
        dirs_exist_ok=True,
    )
    shutil.copytree(
        working_dir / "deps" / "share" / "MaaAgentBinary",
        install_path / "MaaAgentBinary",
        dirs_exist_ok=True,
    )


def install_resource():

    configure_ocr_model()

    shutil.copytree(
        working_dir / "assets" / "resource",
        install_path / "resource",
        dirs_exist_ok=True,
    )

    shutil.copy2(
        working_dir / "assets" / "interface.json",
        install_path,
    )

    with open(install_path / "interface.json", "r", encoding="utf-8") as f:
        interface = jsonc.load(f)

    interface["version"] = version

    with open(install_path / "interface.json", "w", encoding="utf-8") as f:
        jsonc.dump(interface, f, ensure_ascii=False, indent=4)


def install_chores():
    for file in ["README.md", "LICENSE", "logo.png"]:
        shutil.copy2(
            working_dir / file,
            install_path / file,
        )


def install_agent():
    shutil.copytree(
        working_dir / "agent",
        install_path / "agent",
        dirs_exist_ok=True,
    )

    with open(install_path / "interface.json", "r", encoding="utf-8") as f:
        interface = jsonc.load(f)

    # 根据 CI 传入的 OS 环境变量来设置 child_exec
    target_os = os.getenv("TARGET_OS", "").lower()

    # OS 到 child_exec 的映射
    os_exec_map = {
        "win": r"./python/python.exe",
        "macos": r"./python/bin/python3",
        "linux": r"python3",
    }

    match target_os:
        case "android":
            # Android 不使用嵌入式 Python
            interface.pop("agent", None)
        case os_name if os_name in os_exec_map:
            interface["agent"]["child_exec"] = os_exec_map[os_name]
            interface["agent"]["child_args"] = ["-u", r"./agent/main.py"]
            interface["agent"]["embedded"] = True
        case _:
            raise ValueError(f"Unknown OS: {target_os}")

    with open(install_path / "interface.json", "w", encoding="utf-8") as f:
        json.dump(interface, f, ensure_ascii=False, indent=4)

    shutil.copy2(
        working_dir / "requirements.txt",
        install_path / "requirements.txt",
    )


# ✅ 新增：安装 Open.bat
def install_open_bat():
    src = working_dir / "Open.bat"
    dst = install_path / "Open.bat"
    if src.exists():
        print("Copying Open.bat to install directory...")
        shutil.copy2(src, dst)
    else:
        print("Warning: Open.bat not found in project root. Skipping.")


if __name__ == "__main__":
    install_deps()
    install_resource()
    install_chores()
    install_agent()
    install_open_bat()  # ✅ 新增这一行

    print(f"Install to {install_path} successfully.")
