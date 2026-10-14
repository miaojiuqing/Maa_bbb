"""验证本地打包将前端加载的库与agent运行库对齐，并保存可恢复副本。"""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "prepare_local", Path(__file__).resolve().parents[1] / "tools/prepare_local.py")
PREPARE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREPARE)


class LocalFrameworkTests(unittest.TestCase):
    def test_frontend_and_companion_dlls_are_aligned_with_recoverable_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            install = root / "install"
            runtime = install / "runtimes/win-x64"
            frontend = install / "maafw"
            runtime.mkdir(parents=True)
            frontend.mkdir()
            (runtime / "MaaFramework.dll").write_bytes(b"new-framework")
            (runtime / "MaaAdbControlUnit.dll").write_bytes(b"new-touch-controller")
            (runtime / "onnxruntime_maa.dll").write_bytes(b"new-ocr-dependency")
            (runtime / "MaaPiCli.exe").write_bytes(b"unused-cli")
            (frontend / "MaaFramework.dll").write_bytes(b"old-framework")
            (frontend / "MaaAdbControlUnit.dll").write_bytes(b"old-touch-controller")
            config = install / "config"
            config.mkdir()
            (config / "config.json").write_bytes(b"user-config")
            with patch.object(PREPARE, "ROOT", root), patch.object(PREPARE, "INSTALL", install):
                PREPARE.align_frontend_framework()
                PREPARE.align_frontend_framework()
            self.assertEqual((frontend / "MaaFramework.dll").read_bytes(), b"new-framework")
            self.assertEqual((frontend / "MaaAdbControlUnit.dll").read_bytes(), b"new-touch-controller")
            self.assertEqual((frontend / "onnxruntime_maa.dll").read_bytes(), b"new-ocr-dependency")
            self.assertFalse((frontend / "MaaPiCli.exe").exists())
            self.assertEqual((config / "config.json").read_bytes(), b"user-config")
            backups = list((root / "deps/local-runtime").glob("frontend-framework-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual((backups[0] / "MaaFramework.dll").read_bytes(), b"old-framework")


if __name__ == "__main__":
    unittest.main()
