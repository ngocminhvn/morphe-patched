# Morphe Patched

CorePatch-oriented Morphe builder for **YouTube**, **YouTube Music**.

## Current stable targets

- Morphe patches: **v1.47.0**

| App | Stable / recommended | minSdk | Default patches |
|---|---:|---:|---:|
| YouTube | **21.20.405** | 28 | 96/96 |
| YouTube Music | **9.20.53** | 26 | 47/47 |

See **[SUPPORTED.md](SUPPORTED.md)** for the complete stable + experimental compatibility matrix.

## Build behavior

- Original package name is preserved.
- Original signing certificate identity is preserved for CorePatch ROMs.
- Original launcher icon is preserved.
- GmsCore support is disabled.
- Clone app is disabled.
- Spoof signature is disabled.
- Custom branding and app icon patches are disabled.
- **Disable Play Store updates** is explicitly enabled for both apps.
- The APK manifest `versionCode` is set to `2147483647`; Morphe patches app-side `PackageInfo` version reads to use the original code.
- Build validation fails if the update-blocking patch is not present in Morphe's applied-patches report.

For YouTube and YouTube Music, this keeps the stock Google Play Services sign-in path instead of redirecting to GmsCore.
The Play Store update-blocking patch is not effective when the app is installed using root mounting; it can also cause app-specific issues. Existing release APKs are unchanged until rebuilt.

## Release output

Each Morphe patches version has **one combined GitHub Release** (two APKs: YouTube and YouTube Music).
When Morphe patches releases a new version, the workflow builds both Stable APKs and creates a new Release. Later Stable app updates replace only that app's APK within the matching Morphe Release; older releases are preserved.

APK filenames use Vietnam build date in `DDMMYY` format, with no `NeedCorePatch` suffix:

- `Youtube-<version>-morphe-<patch>-DDMMYY.apk`
- `YoutubeMusic-<version>-morphe-<patch>-DDMMYY.apk`

For example: `Youtube-21.16.256-morphe-1.46.0-091026.apk`.

The workflow checks Morphe's supported Stable targets once per day (09:13 Vietnam time).
A new Morphe patch version creates a release with both Stable APKs. A newer supported
Stable app version updates only that app in the current release. Otherwise, it stops after the check.

## Status legend

- 🟢 **Stable** — recommended target.
- 🧪 **Experimental** — supported upstream, but not the recommended stable target.

[Morphe patches release](https://github.com/MorpheApp/morphe-patches/releases/tag/v1.47.0) · [GitHub Releases](../../releases)
