# Morphe Patched

CorePatch-oriented Morphe builder for:

- YouTube
- YouTube Music
- Reddit

## Build behavior

The workflow keeps the original app identity needed by stock sign-in flows:

- Original package name is preserved.
- Original signing certificate identity is preserved for CorePatch ROMs.
- Original launcher icon is preserved.
- GmsCore support is disabled.
- Clone app is disabled.
- Spoof signature is disabled.
- Custom branding and Reddit App icon patches are disabled.

For YouTube and YouTube Music this keeps the stock Google Play Services sign-in path instead of redirecting the app to GmsCore.

## Supported versions

See **[SUPPORTED.md](SUPPORTED.md)** for the current versions supported by the latest Morphe patches.

The list is generated automatically from Morphe's latest `patches-list.json` and marks each target as:

- 🟢 **Stable**
- 🧪 **Experimental**

Current support data is synced automatically from:

https://github.com/MorpheApp/morphe-patches/releases/
