import sys
import jsonc

from typing import List
from pathlib import Path

from maa.resource import Resource
from maa.tasker import Tasker, LoggingLevelEnum


def check(dirs: List[Path]) -> bool:
    resource = Resource()

    print(f"Checking {len(dirs)} directories...")

    for dir in dirs:
        print(f"Checking {dir}...")
        status = resource.post_bundle(dir).wait().status
        if not status.succeeded:
            print(f"Failed to check {dir}.")
            return False

    print("All directories checked.")
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python configure.py <interface.json path>")
        sys.exit(1)

    Tasker.set_stdout_level(LoggingLevelEnum.All)

    # 读取 interface.json 文件
    interface_json_path = Path(sys.argv[1])
    if not interface_json_path.exists():
        print(f"Error: {interface_json_path} does not exist.")
        sys.exit(1)

    with open(interface_json_path, "r", encoding="utf-8") as f:
        interface_data = jsonc.load(f)

    # 获取 interface.json 所在目录，用于解析相对路径
    interface_dir = interface_json_path.parent

    # 提取 resource 数组中每个对象的 path 数组
    dirs: List[List[Path]] = []
    if "resource" in interface_data:
        for resource_obj in interface_data["resource"]:
            if "path" in resource_obj:
                # 将相对路径转换为绝对路径（相对于 interface.json 所在目录）
                path_list = [interface_dir / Path(p) for p in resource_obj["path"]]
                dirs.append(path_list)

    # 检查每个 resource 配置的路径列表
    for i, path_list in enumerate(dirs):
        print(f"Checking resource configuration {i + 1} with {len(path_list)} paths...")
        if not check(path_list):
            sys.exit(1)


if __name__ == "__main__":
    main()
