"""将 MFWCFA 解压目录中的文件复制到 install/（供 CI Install 步骤调用）。"""
from pathlib import Path
import shutil

src, dst = Path("MFWCFA"), Path("install")
if not src.is_dir():
    raise SystemExit(0)
dst.mkdir(parents=True, exist_ok=True)
for p in src.rglob("*"):
    if not p.is_file():
        continue
    rel = p.relative_to(src)
    t = dst / rel
    t.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, t)
