"""将 MFWCFA 解压目录中的文件复制到 install/（供 CI Install 步骤调用）。

对齐 MAA_Punish：先写好资源并生成 resource.hash，再叠 MFW。
MFW 包若带有示例 resource / interface.json，不得覆盖项目侧已哈希的文件。
"""
from pathlib import Path
import shutil

src, dst = Path("MFWCFA"), Path("install")
if not src.is_dir():
    raise SystemExit(0)

# 项目产物（含已写入的 resource.hash），禁止被 MFW 包覆盖
_SKIP_TOP_LEVEL = frozenset(
    {
        "resource",
        "agent",
        "tasks",
        "interface.json",
        "runtimes",
        "requirements.txt",
    }
)

dst.mkdir(parents=True, exist_ok=True)
for p in src.rglob("*"):
    if not p.is_file():
        continue
    rel = p.relative_to(src)
    if rel.parts and rel.parts[0] in _SKIP_TOP_LEVEL:
        continue
    t = dst / rel
    t.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, t)
