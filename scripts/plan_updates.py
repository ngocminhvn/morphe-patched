#!/usr/bin/env python3
"""Decide daily Stable APK changes: new Morphe release vs changed app versions."""
import argparse
import json
from pathlib import Path
from asset_naming import current_asset

APPS = (("youtube", "YouTube"), ("youtube-music", "YouTube Music"))


def plan_updates(metadata: dict, release: dict) -> dict:
    tag = metadata.get("patchesTag")
    if not isinstance(tag, str) or not tag.startswith("v") or not tag[1:]:
        raise ValueError("Invalid or missing Morphe patches tag")
    patch = tag[1:]
    release_tag = f"morphe-{patch}"
    targets = {}
    for key, label in APPS:
        versions = metadata.get("apps", {}).get(key, {}).get("versions", [])
        stable = next((v.get("version") for v in versions
                       if v.get("experimental") is False and v.get("version")), None)
        if not stable:
            raise ValueError(f"No supported Stable target for {label}")
        targets[key] = stable
    new_release = not release or not release.get("tag_name")
    if not new_release and release["tag_name"] != release_tag:
        raise ValueError("Release tag mismatch; refusing a wrong publication")
    assets = {a.get("name", "") for a in release.get("assets", [])} if not new_release else set()
    changed = [
        key for key, _ in APPS
        if new_release or not any(
            current_asset(name, key, targets[key], patch) for name in assets
        )
    ]
    mode = "new_release" if new_release else ("update_existing" if changed else "none")
    return {
        "should_build": bool(changed),
        "mode": mode,
        "apps": changed,
        "targets": targets,
        "patches_tag": tag,
        "release_tag": release_tag,
    }


def summary(p: dict) -> str:
    status = {
        "new_release": "Morphe mới: build cả hai APK Stable và tạo Release mới.",
        "update_existing": "Stable app mới/thiếu: chỉ build ứng dụng cần cập nhật trong Release hiện tại.",
        "none": "KHÔNG CÓ CẬP NHẬT: dừng sau metadata check. Không tải APK, build hay publish.",
    }[p["mode"]]
    lines = ["## Daily Morphe Stable check", "", f"**{status}**", "",
             f"- Morphe patches: {p['patches_tag']}",
             f"- Release tag: {p['release_tag']}", "",
             "| App | Latest supported Stable | Decision |", "|---|---|---|"]
    for key, label in APPS:
        state = "Build + publish" if key in p["apps"] else "Keep existing APK"
        lines.append(f"| {label} | {p['targets'][key]} | {state} |")
    lines += ["", "Experimental is excluded; build date alone does not trigger an update.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    p = plan_updates(
        json.loads(args.metadata.read_text(encoding="utf-8")),
        json.loads(args.release.read_text(encoding="utf-8")),
    )
    with args.output.open("a", encoding="utf-8") as output:
        for key, value in p.items():
            val = str(value).lower() if isinstance(value, bool) else (
                json.dumps(value, separators=(",", ":")) if isinstance(value, (dict, list)) else value
            )
            output.write(f"{key}={val}\n")
    msg = summary(p)
    with args.summary.open("a", encoding="utf-8") as out:
        out.write(msg)
    print(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
