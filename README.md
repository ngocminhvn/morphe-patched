# Morphe Patched — YouTube CorePatch Builder

Build **Morphe-patched YouTube with the original package and original YouTube icon** for ROMs that already provide CorePatch / signature-verification bypass.

## What this builder guarantees

- package stays `com.google.android.youtube`;
- `GmsCore support` is always disabled;
- `Spoof signature` is always disabled;
- `Custom branding` is always disabled, so the launcher/app-list icon and app name stay stock YouTube;
- Morphe runs with `--unsigned` — the APK is not re-signed with the Morphe key;
- the output must retain the same Google YouTube signing certificates as the source;
- any failed Morphe patch/rebuild makes the build fail;
- output defaults to `arm64-v8a`.

> The resulting APK is intentionally for a ROM with compatible CorePatch/signature bypass. Stock Android normally rejects a modified APK whose original Google signature no longer matches the modified contents.

## Repository tree

```
.
├── .github/
│   └── workflows/
│       └── build.yml
├── config/
│   └── defaults.env
├── scripts/
│   ├── apk_sigblock.py
│   └── build.sh
├── .gitignore
├── LICENSE
└── README.md
```

## Build with GitHub Actions

Open **Actions → Build YouTube Morphe CorePatch → Run workflow**.

Required input:

- `source_url`: direct public URL to an original YouTube `.apk`, `.apkm`, `.apks`, or `.xapk`.
- `source_format`: matching file format.

Optional:

- `expected_sha256`: strongly recommended when you know the source hash.
- Morphe Desktop / patch versions.
- extra patch names to enable or disable.

The protected patches **cannot be re-enabled** through `extra_enable`:

- `GmsCore support`
- `Spoof signature`
- `Custom branding`

This is intentional. The last one is what keeps the output icon identical to normal YouTube instead of Morphe's default black branding icon.

## Known-good defaults

- Morphe Desktop: `v1.18.0`
- Morphe patches: `v1.45.0`
- ABI: `arm64-v8a`

The default tool assets are SHA-256 pinned in `config/defaults.env`.

## Output

A successful run uploads an artifact containing:

- patched APK;
- Morphe result JSON;
- build log;
- APK SHA-256;
- build metadata.

The result JSON is checked to ensure:

- package is still `com.google.android.youtube`;
- no failed patch exists;
- patching/rebuilding succeeded;
- there is no Morphe signing step;
- GmsCore support / Spoof signature / Custom branding were not applied.

The signing verifier then parses APK Signature Scheme v2/v3/v3.1 blocks directly and checks that the source and output expose the same Google YouTube certificate set. For split bundles, this is more reliable than comparing the whole signing block byte-for-byte because Morphe merges the splits before patching.

## Local build

Requirements: Java 21, curl, jq, Python 3, sha256sum.

```bash
export SOURCE_FILE=/path/to/youtube.apkm
bash scripts/build.sh
```

Optional:

```bash
export MORPHE_PATCHES_VERSION=v1.45.0
export MORPHE_DESKTOP_VERSION=v1.18.0
export KEEP_ARCHS=arm64-v8a
export EXPECTED_SHA256=<source sha256>
export EXTRA_DISABLE='Patch one,Patch two'
export EXTRA_ENABLE='Patch three'
```

Build results are written to `dist/`.

## Source APKs

This repository does not redistribute YouTube APKs. Supply the original source yourself.

YouTube is owned by Google. Morphe Desktop and Morphe patches remain subject to their upstream licenses.
