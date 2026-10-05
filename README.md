# YouTube Morphe CorePatch Builder

GitHub Actions builder for **stock-package YouTube + Morphe patches** on ROMs that already provide **CorePatch / signature-verification bypass**.

This repository intentionally follows the build model that worked on HyperMOS:

- keeps package `com.google.android.youtube`;
- disables **GmsCore support**;
- disables Morphe **Spoof signature**;
- builds with Morphe `--unsigned`;
- preserves the **original Google APK Signing Block byte-for-byte**;
- accepts the resulting digest mismatch because the target ROM's CorePatch handles signature verification;
- never signs the output with the Morphe key.

> This output is for a ROM with a compatible CorePatch/signature bypass. A normal stock Android ROM is expected to reject it.

## Quick use

1. Open **Actions → Build YouTube CorePatch → Run workflow**.
2. Paste a **direct public download URL** for an original YouTube `.apk`, `.apkm`, `.apks`, or `.xapk`.
3. Choose the matching `source_format`.
4. If possible, provide the source SHA-256.
5. Run the workflow and download the `YouTube-Morphe-CorePatch` artifact.

Known-good defaults are pinned to:

- Morphe Desktop `v1.18.0`
- Morphe patches `v1.45.0`
- ABI `arm64-v8a`

You can change these inputs per build. Use `latest` only after you are ready to test a newer patch/toolchain combination.

## Why `--unsigned`?

Signing the modified YouTube APK with a new Morphe/debug key changes the identity seen by components outside YouTube, including Google Play Services. On the tested CorePatch ROM, the reliable setup was to keep the original Google signing block in the modified APK and let CorePatch bypass the now-invalid APK digest.

The build fails if the final APK does **not** preserve the signing block from the original/merged source byte-for-byte.

## Fail-fast checks

A build is rejected when any of these is true:

- Morphe reports a failed patch or failed rebuild step;
- output package is not `com.google.android.youtube`;
- `GmsCore support` was accidentally applied;
- `Spoof signature` was accidentally applied;
- original APK Signing Block is missing or changes in the patched output;
- optional source SHA-256 does not match.

## Experimental YouTube versions

Morphe can mark newer supported targets as experimental. That is separate from the CorePatch signing mechanism. Prefer a Morphe target not marked experimental when stability matters.

Do not use `--force` by default: if Morphe says a YouTube version is incompatible, use a supported source version instead.

## Local build

Requirements: Java 21, curl, jq, Python 3, sha256sum.

```bash
export SOURCE_FILE=/path/to/youtube.apkm
./scripts/build.sh
```

Optional environment variables:

```bash
export MORPHE_PATCHES_VERSION=v1.45.0
export MORPHE_DESKTOP_VERSION=v1.18.0
export KEEP_ARCHS=arm64-v8a
export EXPECTED_SHA256=<source sha256>
export EXTRA_DISABLE='Patch one,Patch two'
export EXTRA_ENABLE='Patch three'
```

Outputs are written to `dist/` with an APK, Morphe JSON report, build log, SHA-256 file, and build metadata.

## Source APKs

This repo does **not** redistribute YouTube APKs. Provide an original source file/URL yourself. This keeps the builder reproducible without committing Google binaries into Git.

## Licensing

This repository contains only builder scripts/configuration. Morphe Desktop and Morphe patches are downloaded from their upstream releases and remain under their respective upstream licenses. YouTube is owned by Google and is not included in this repository.
