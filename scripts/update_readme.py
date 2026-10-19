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
    for key in ("youtube", "youtube-music"):
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
        "CorePatch-oriented Morphe builder for **YouTube**, **YouTube Music**.",
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
        "Each Morphe patches version has **one combined GitHub Release** (two APKs: YouTube and YouTube Music).",
        "When Morphe patches releases a new version, the workflow builds both Stable APKs and creates a new Release. Later Stable app updates replace only that app's APK within the matching Morphe Release; older releases are preserved.",
        "",
        "APK filenames use Vietnam build date in `DDMMYY` format, with no `NeedCorePatch` suffix:",
        "",
        "- `Youtube-<version>-morphe-<patch>-DDMMYY.apk`",
        "- `YoutubeMusic-<version>-morphe-<patch>-DDMMYY.apk`",
        "",
        "For example: `Youtube-21.16.256-morphe-1.46.0-091026.apk`.",
        "",
        "The workflow checks Morphe's supported Stable targets once per day (09:13 Vietnam time).",
        "A new Morphe patch version creates a release with both Stable APKs. A newer supported",
        "Stable app version updates only that app in the current release. Otherwise, it stops after the check.",
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
