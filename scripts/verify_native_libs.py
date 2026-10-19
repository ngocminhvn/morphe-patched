#!/usr/bin/env python3
"""Reject YouTube Music APKs missing arm64 native libraries at build/publish time."""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

ARM64 = "lib/arm64-v8a/"
STARTUP_LIBRARY = ARM64 + "libelements.so"


def libraries(apk: Path) -> set[str]:
    if apk.suffix.lower() != ".apk":
        raise ValueError(f"{apk}: expected standalone APK (not APKM/split bundle)")
    if not zipfile.is_zipfile(apk):
        raise ValueError(f"{apk}: invalid APK/ZIP")
    with zipfile.ZipFile(apk) as zf:
        return {
            item.filename for item in zf.infolist()
            if item.filename.startswith(ARM64)
            and item.filename.endswith(".so")
            and not item.is_dir() and item.file_size > 0
        }


def verify(apk: Path, baseline: Path | None = None) -> int:
    present = libraries(apk)
    if STARTUP_LIBRARY not in present:
        raise ValueError(
            f"{apk}: missing {STARTUP_LIBRARY}; runtime would crash with "
            "java.lang.UnsatisfiedLinkError"
        )
    if baseline:
        removed = sorted(libraries(baseline) - present)
        if removed:
            raise ValueError(f"{apk}: stripped source native libraries: {', '.join(removed)}")
    print(f"native_arm64_ok={len(present)} libelements.so=present path={apk}")
    return len(present)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("apk", type=Path)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    try:
        verify(args.apk, args.baseline)
    except (ValueError, OSError, zipfile.BadZipFile) as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
