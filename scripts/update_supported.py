#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import urllib.request
from pathlib import Path

API = "https://api.github.com/repos/MorpheApp/morphe-patches/releases/latest"
RAW = "https://raw.githubusercontent.com/MorpheApp/morphe-patches/{tag}/patches-list.json"
PACKAGE = "com.google.android.youtube"


def get_json(url: str):
    headers = {
        "User-Agent": "morphe-patched-support-sync",
        "Accept": "application/vnd.github+json",
    }
    token = os.environ.get("GH_TOKEN")
    if token and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def version_key(v: str):
    return tuple(int(x) for x in re.findall(r"\d+", v))


def collect(data: dict):
    versions = {}
    default_total = 0

    for patch in data.get("patches", []):
        pkg = next(
            (p for p in (patch.get("compatiblePackages") or []) if p.get("packageName") == PACKAGE),
            None,
        )
        if not pkg:
            continue

        if patch.get("default") is True:
            default_total += 1

        for target in pkg.get("targets") or []:
            version = target.get("version")
            if not version:
                continue
            item = versions.setdefault(
                version,
                {
                    "version": version,
                    "experimental": bool(target.get("isExperimental")),
                    "minSdk": target.get("minSdk"),
                    "defaultPatches": 0,
                    "patches": 0,
                },
            )
            item["experimental"] = item["experimental"] and bool(target.get("isExperimental"))
            if target.get("minSdk") is not None:
                if item["minSdk"] is None:
                    item["minSdk"] = target["minSdk"]
                else:
                    item["minSdk"] = min(item["minSdk"], target["minSdk"])
            item["patches"] += 1
            if patch.get("default") is True:
                item["defaultPatches"] += 1

    rows = sorted(versions.values(), key=lambda x: version_key(x["version"]), reverse=True)
    return rows, default_total


def markdown(tag: str, release_url: str, published_at: str | None, rows: list[dict], default_total: int):
    stable = [r for r in rows if not r["experimental"]]
    experimental = [r for r in rows if r["experimental"]]
    recommended = stable[0]["version"] if stable else (rows[0]["version"] if rows else "unknown")

    lines = [
        "# Supported YouTube versions",
        "",
        "This file is generated automatically from Morphe's latest `patches-list.json`.",
        "",
        f"- Morphe patches: **{tag}**",
        f"- Latest stable/recommended YouTube target: **{recommended}**",
        f"- Stable targets: **{len(stable)}**",
        f"- Experimental targets: **{len(experimental)}**",
    ]
    if published_at:
        lines.append(f"- Morphe release published: **{published_at}**")
    lines += [
        "",
        "| YouTube | Status | minSdk | Default patches supporting target |",
        "|---|---|---:|---:|",
    ]

    for r in rows:
        status = "🟢 Stable" if not r["experimental"] else "🧪 Experimental"
        lines.append(
            f"| `{r['version']}` | {status} | {r['minSdk'] if r['minSdk'] is not None else '-'} | "
            f"{r['defaultPatches']}/{default_total} |"
        )

    lines += [
        "",
        "> Experimental means Morphe supports patching the version but upstream does not consider it the recommended stable target yet.",
        "",
        f"[Morphe patches release]({release_url})",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="SUPPORTED.md")
    ap.add_argument("--json-output")
    ap.add_argument("--tag")
    args = ap.parse_args()

    if args.tag:
        tag = args.tag if args.tag.startswith("v") else f"v{args.tag}"
        release_url = f"https://github.com/MorpheApp/morphe-patches/releases/tag/{tag}"
        published = None
    else:
        latest = get_json(API)
        tag = latest["tag_name"]
        release_url = latest["html_url"]
        published = latest.get("published_at")

    data = get_json(RAW.format(tag=tag))
    rows, default_total = collect(data)

    output = Path(args.output)
    output.write_text(markdown(tag, release_url, published, rows, default_total), encoding="utf-8")

    payload = {
        "patchesTag": tag,
        "patchesVersion": data.get("version"),
        "releaseUrl": release_url,
        "publishedAt": published,
        "defaultYouTubePatches": default_total,
        "versions": rows,
    }
    if args.json_output:
        Path(args.json_output).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"patches_tag={tag}")
    print(f"supported_versions={','.join(r['version'] for r in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
