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

Each Morphe patches version has **one combined GitHub Release** (three APKs: YouTube, YouTube Music and Reddit).
When Morphe patches releases a new version, the workflow builds all three Stable APKs and creates a new Release. Later Stable app updates replace only that app's APK within the matching Morphe Release; older releases are preserved.

APK filenames use Vietnam build date in `DDMMYY` format, with no `NeedCorePatch` suffix:

- `Youtube-<version>-morphe-<patch>-DDMMYY.apk`
- `YoutubeMusic-<version>-morphe-<patch>-DDMMYY.apk`
- `Reddit-<version>-morphe-<patch>-DDMMYY.apk`

For example: `Youtube-21.16.256-morphe-1.46.0-091026.apk`.

The scheduled workflow checks the latest Morphe Stable/recommended targets every 6 hours.
It builds a new APK only when the Stable app version or Morphe patch version changes,
or when a dated-format APK is still missing. Changing the date alone does not trigger a build.

## Status legend

- 🟢 **Stable** — recommended target.
- 🧪 **Experimental** — supported upstream, but not the recommended stable target.

[Morphe patches release](https://github.com/MorpheApp/morphe-patches/releases/tag/v1.46.0) · [GitHub Releases](../../releases)
