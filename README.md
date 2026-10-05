# Morphe Patched — YouTube CorePatch Builder

Build Morphe-patched YouTube with the **original package + original YouTube icon** for ROMs that already provide CorePatch/signature-verification bypass.

## Build

Open **Actions → Build YouTube Morphe → Run workflow**.

There is only **one input**:

`source_url`

Paste either:

- a direct public APK/APKM/APKS/XAPK URL; or
- a YouTube page on **APKMirror.com**.

The builder automatically resolves APKMirror download pages and detects whether the source is APK or split APK bundle.

## Everything else is automatic

Every build fetches:

- the **latest Morphe patches release** from [MorpheApp/morphe-patches](https://github.com/MorpheApp/morphe-patches/releases);
- the latest Morphe Desktop release required to run the patcher.

The protected configuration is fixed:

- package stays `com.google.android.youtube`;
- `GmsCore support` = OFF;
- `Spoof signature` = OFF;
- `Custom branding` = OFF;
- stock YouTube icon/name are kept;
- Morphe uses `--unsigned`;
- Google YouTube signing identity must be preserved;
- CorePatch/signature-verification bypass is required.

## Supported YouTube versions

See **[SUPPORTED.md](SUPPORTED.md)**.

That file is generated from the latest Morphe `patches-list.json` and is synced automatically every day when Morphe changes its supported targets.

The table clearly marks:

- 🟢 **Stable** targets;
- 🧪 **Experimental** targets.

If a source version is not present in the current Morphe support list, the build is rejected instead of forcing patches onto an unsupported APK.

## Releases

A successful build is uploaded twice:

1. as a short-lived GitHub Actions artifact;
2. as a permanent **GitHub Release**.

Release tags use:

`youtube-<YouTube version>-morphe-<Morphe patches version>`

Example:

`youtube-21.39.522-morphe-1.45.0`

If the same YouTube + Morphe combination is built again, the existing Release is updated and its assets are replaced instead of creating duplicates.

Experimental YouTube targets are published as GitHub **pre-releases**.

## Output identity

The build validates that:

- the result package is `com.google.android.youtube`;
- Morphe did not sign the result with its own key;
- GmsCore support, Spoof signature and Custom branding were not applied;
- the source and output contain the same recognized Google YouTube certificate identity.

## Repository tree

```
.
├── .github/workflows/
│   ├── build.yml
│   └── sync-supported.yml
├── config/defaults.env
├── scripts/
│   ├── apk_sigblock.py
│   ├── build.sh
│   ├── fetch_source.py
│   └── update_supported.py
├── .gitignore
├── LICENSE
├── README.md
└── SUPPORTED.md
```

This repository does not store original YouTube APKs. YouTube is owned by Google; Morphe components remain subject to their upstream licenses.
