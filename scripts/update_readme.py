#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def stable_target(app: dict):
    versions = app.get("versions") or []
    stable = [v for v in versions if not v.get("experimental")]
    return stable[0] if stable else (versions[0] if versions else None)


def build_readme(data: dict) -> str:
    patches_tag = data.get("patchesTag", "unknown")
    release_url = data.get("releaseUrl", "https://github.com/MorpheApp/morphe-patches/releases")
    apps = data.get("apps") or {}

    rows = []
    for key in ("youtube", "youtube-music", "reddit"):
        app = apps.get(key) or {}
        target = stable_target(app)
        if not target:
            continue
        rows.append(
            f"| {app.get('appName', key)} | **{target.get('version', '-')}** | "
            f"{target.get('minSdk') if target.get('minSdk') is not None else '-'} | "
            f"{target.get('defaultPatches', 0)}/{app.get('defaultPatches', 0)} |"
        )

    lines = [
        "# Morphe Patched",
        "",
        "CorePatch-oriented Morphe builder for **YouTube**, **YouTube Music**, and **Reddit**.",
        "",
        "## Current stable targets",
        "",
        f"- Morphe patches: **{patches_tag}**",
        "",
        "| App | Stable / recommended | minSdk | Default patches |",
        "|---|---:|---:|---:|",
        *rows,
        "",
        "See **[SUPPORTED.md](SUPPORTED.md)** for the complete stable + experimental compatibility matrix.",
        "",
        "## Build behavior",
        "",
        "- Original package name is preserved.",
        "- Original signing certificate identity is preserved for CorePatch ROMs.",
        "- Original launcher icon is preserved.",
        "- GmsCore support is disabled.",
        "- Clone app is disabled.",
        "- Spoof signature is disabled.",
        "- Custom branding and app icon patches are disabled.",
        "",
        "For YouTube and YouTube Music, this keeps the stock Google Play Services sign-in path instead of redirecting to GmsCore.",
        "",
        "## Release output",
        "",
        "Each GitHub Release contains **one APK only** and uses the `NeedCorePatch` naming convention:",
        "",
        "- `Youtube-<version>-morphe-<patch>-NeedCorePatch.apk`",
        "- `YoutubeMusic-<version>-morphe-<patch>-NeedCorePatch.apk`",
        "- `Reddit-<version>-morphe-<patch>-NeedCorePatch.apk`",
        "",
        "The scheduled workflow checks the latest Morphe stable/recommended targets and publishes missing releases automatically.",
        "",
        "## Status legend",
        "",
        "- 🟢 **Stable** — recommended target.",
        "- 🧪 **Experimental** — supported upstream, but not the recommended stable target.",
        "",
        f"[Morphe patches release]({release_url}) · [GitHub Releases](../../releases)",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--output", default="README.md")
    args = ap.parse_args()

    data = json.loads(Path(args.json).read_text(encoding="utf-8"))
    Path(args.output).write_text(build_readme(data), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
