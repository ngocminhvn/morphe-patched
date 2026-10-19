#!/usr/bin/env python3
"""Regression tests for native libraries required at YouTube Music startup."""
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_native_libs import verify  # noqa: E402


class NativeLibrariesTests(unittest.TestCase):
    def apk(self, root: Path, name: str, libs: list[str]) -> Path:
        path = root / name
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("AndroidManifest.xml", "manifest")
            for lib in libs:
                zf.writestr(f"lib/arm64-v8a/{lib}", b"ELF")
        return path

    def test_valid(self):
        with tempfile.TemporaryDirectory() as temp:
            p = self.apk(Path(temp), "music.apk", ["libelements.so", "libgoogle3.so"])
            self.assertEqual(verify(p), 2)

    def test_missing_elements(self):
        with tempfile.TemporaryDirectory() as temp:
            p = self.apk(Path(temp), "broken.apk", ["libgoogle3.so"])
            with self.assertRaisesRegex(ValueError, "libelements.so"):
                verify(p)

    def test_stripped_library(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = self.apk(root, "source.apk", ["libelements.so", "libgoogle3.so"])
            patched = self.apk(root, "patched.apk", ["libelements.so"])
            with self.assertRaisesRegex(ValueError, "libgoogle3.so"):
                verify(patched, original)

    def test_reject_apkm(self):
        with tempfile.TemporaryDirectory() as temp:
            p = self.apk(Path(temp), "music.apkm", ["libelements.so"])
            with self.assertRaisesRegex(ValueError, "standalone APK"):
                verify(p)


if __name__ == "__main__":
    unittest.main()
