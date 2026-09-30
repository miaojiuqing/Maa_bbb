"""通过 maafw 计算 interface.resource 的 hash，并写入各 resource.hash 字段。

maafw 的 resource.hash 只按 recursive_directory_iterator 遍历到的「文件大小」序列计算，
该顺序依赖文件系统枚举：CI 上 copytree 后的顺序与用户解压 zip 后的顺序经常不一致，
会导致 expected ≠ actual。

因此在计算前对每个 resource bundle 做一次「按路径排序打 zip → 再解压」稳定化，
使构建机上的枚举顺序与按路径排序打包/解压后的顺序对齐。

跨平台若换行符导致文件大小不同，仍须在目标平台上生成并写入对应安装包。
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import jsonc
from maa.resource import Resource

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMENT_BEGIN = "<!-- mfw-resource-hash"
COMMENT_END = "-->"


def stabilize_directory(dir_path: Path) -> None:
    """按相对路径排序写入 zip 再解压，重写目录内容以稳定枚举顺序。"""
    dir_path = dir_path.resolve()
    if not dir_path.is_dir():
        return

    files = sorted(
        (path for path in dir_path.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(dir_path).as_posix().casefold(),
    )
    if not files:
        return

    with tempfile.TemporaryDirectory(prefix="mfw-hash-stab-") as tmp:
        tmp_path = Path(tmp)
        zip_path = tmp_path / "bundle.zip"
        extract_path = tmp_path / "out"
        extract_path.mkdir()

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as handle:
            for file_path in files:
                handle.write(
                    file_path,
                    file_path.relative_to(dir_path).as_posix(),
                )

        with zipfile.ZipFile(zip_path, "r") as handle:
            handle.extractall(extract_path)

        for child in list(dir_path.iterdir()):
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        for child in extract_path.iterdir():
            shutil.move(str(child), str(dir_path / child.name))


def stabilize_resource_roots(root: Path, interface: dict) -> list[Path]:
    """稳定 interface.resource 中出现过的每个 bundle 目录（去重）。"""
    seen: set[Path] = set()
    stabilized: list[Path] = []
    for entry in interface.get("resource", []):
        if not isinstance(entry, dict):
            continue
        raw_paths = entry.get("path")
        if not isinstance(raw_paths, list):
            continue
        for raw_path in raw_paths:
            normalized = str(raw_path).removeprefix("./")
            bundle_path = (root / normalized).resolve()
            if bundle_path in seen or not bundle_path.is_dir():
                continue
            seen.add(bundle_path)
            stabilize_directory(bundle_path)
            stabilized.append(bundle_path)
    return stabilized


def compute_resource_hash(paths: list[str], root: Path) -> str:
    resource = Resource()
    for raw_path in paths:
        normalized = raw_path.removeprefix("./")
        bundle_path = (root / normalized).resolve()
        if not bundle_path.is_dir():
            raise FileNotFoundError(f"resource bundle not found: {bundle_path}")
        status = resource.post_bundle(bundle_path).wait()
        if not status.succeeded:
            raise RuntimeError(f"failed to load resource bundle: {bundle_path}")

    hash_value = resource.hash
    if callable(hash_value):
        hash_value = hash_value()
    result = str(hash_value or "").strip()
    if not result:
        raise RuntimeError("maafw returned empty resource hash")
    return result


def build_hash_comment(lines: list[tuple[str, str]]) -> str:
    body = "\n".join(f"{name}: {hash_value}" for name, hash_value in lines)
    return f"{COMMENT_BEGIN}\n{body}\n{COMMENT_END}"


def apply_resource_hashes(
    interface_path: Path,
    *,
    root: Path = REPO_ROOT,
    stabilize: bool = True,
) -> str:
    with open(interface_path, encoding="utf-8") as handle:
        interface = jsonc.load(handle)

    if stabilize:
        stabilized = stabilize_resource_roots(root, interface)
        print(
            f"stabilized {len(stabilized)} resource bundle(s) before hash",
            flush=True,
        )

    comment_lines: list[tuple[str, str]] = []
    for entry in interface.get("resource", []):
        if not isinstance(entry, dict):
            continue
        raw_paths = entry.get("path")
        if not isinstance(raw_paths, list) or not raw_paths:
            continue

        paths = [str(path) for path in raw_paths]
        hash_value = compute_resource_hash(paths, root)
        entry["hash"] = hash_value

        name = entry.get("name")
        comment_lines.append((str(name) if name else "resource", hash_value))

    with open(interface_path, "w", encoding="utf-8") as handle:
        jsonc.dump(interface, handle, ensure_ascii=False, indent=4)
        handle.write("\n")

    return build_hash_comment(comment_lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "interface",
        nargs="?",
        type=Path,
        default=REPO_ROOT / "assets" / "interface.json",
        help="interface.json 路径，默认 assets/interface.json",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="资源路径解析根目录，默认为 interface.json 所在目录",
    )
    parser.add_argument(
        "--no-stabilize",
        action="store_true",
        help="跳过资源目录稳定化（仅调试用）",
    )
    args = parser.parse_args()

    interface_path = args.interface.resolve()
    if not interface_path.is_file():
        print(f"interface.json not found: {interface_path}", file=sys.stderr)
        return 1

    root = (args.root or interface_path.parent).resolve()
    comment = apply_resource_hashes(
        interface_path,
        root=root,
        stabilize=not args.no_stabilize,
    )
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(comment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
