# Morphe Patched

CorePatch-oriented Morphe builder for **YouTube**, **YouTube Music**, and **Reddit**.

## Current stable targets

- Morphe patches: **v1.46.0**

| App | Stable / recommended | minSdk | Default patches |
|---|---:|---:|---:|
| YouTube | **21.16.256** | 28 | 92/92 |
| YouTube Music | **9.20.53** | 26 | 47/47 |
| Reddit | **2026.24.0** | 29 | 18/18 |

See **[SUPPORTED.md](SUPPORTED.md)** for the complete stable + experimental compatibility matrix.

## Build behavior

- Original package name is preserved.
- Original signing certificate identity is preserved for CorePatch ROMs.
- Original launcher icon is preserved.
- GmsCore support is disabled.
- Clone app is disabled.
- Spoof signature is disabled.
- Custom branding and app icon patches are disabled.

For YouTube and YouTube Music, this keeps the stock Google Play Services sign-in path instead of redirecting to GmsCore.

## Release output

Each GitHub Release contains **one APK only** and uses the `NeedCorePatch` naming convention:

- `Youtube-<version>-morphe-<patch>-NeedCorePatch.apk`
- `YoutubeMusic-<version>-morphe-<patch>-NeedCorePatch.apk`
- `Reddit-<version>-morphe-<patch>-NeedCorePatch.apk`

The scheduled workflow checks the latest Morphe stable/recommended targets and publishes missing releases automatically.

## Status legend

- 🟢 **Stable** — recommended target.
- 🧪 **Experimental** — supported upstream, but not the recommended stable target.

[Morphe patches release](https://github.com/MorpheApp/morphe-patches/releases/tag/v1.46.0) · [GitHub Releases](../../releases)
