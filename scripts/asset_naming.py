#!/usr/bin/env python3
"""Naming and matching of Stable release APK assets.

The build date is a display suffix, *not* an update signal. Matching ignores
DDMMYY and requires the exact app, Stable version and Morphe patches version.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

PREFIXES = {
    "youtube": "Youtube",
    "youtube-music": "YoutubeMusic",
    "reddit": "Reddit",
}


def asset_name(app: str, version: str, patches_version: str, ddmmyy: str) -> str:
    if not re.fullmatch(r"\d{6}", ddmmyy):
        raise ValueError("Date must use DDMMYY (six digits)")
    return f"{PREFIXES[app]}-{version}-morphe-{patches_version}-{ddmmyy}.apk"


def current_asset(name: str, app: str, version: str, patches_version: str) -> bool:
    prefix = f"{PREFIXES[app]}-{version}-morphe-{patches_version}-"
    return name.startswith(prefix) and bool(re.fullmatch(r"\d{6}\.apk", name[len(prefix):]))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", choices=PREFIXES, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--patches-version", required=True)
    parser.add_argument("--assets-file", required=True)
    args = parser.parse_args()

    with open(args.assets_file, encoding="utf-8") as f:
        names = json.load(f)
    if not isinstance(names, list) or not all(isinstance(x, str) for x in names):
        raise ValueError("Expected JSON array of release asset names")

    matches = sorted(x for x in names if current_asset(x, args.app, args.version, args.patches_version))
    if matches:
        print(f"Current Stable APK already published: {matches[-1]}")
        return 0
    print(f"No current dated APK for {args.app} {args.version} / Morphe {args.patches_version}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
