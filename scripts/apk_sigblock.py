#!/usr/bin/env python3
"""Verify the Google YouTube signing identity without verifying APK content digests.

CorePatch-targeted builds intentionally modify the APK while preserving Google's
signing identity. For split bundles Morphe may rebuild the signing block layout,
so certificate identity is compared instead of requiring byte-for-byte equality.
"""
from __future__ import annotations

import argparse
import hashlib
import struct
import zipfile
from pathlib import Path

EOCD = b"PK\x05\x06"
MAGIC = b"APK Sig Block 42"

SCHEME_IDS = {
    0x7109871A: "v2",
    0xF05368C0: "v3",
    0x1B93AD61: "v3.1",
}

# Google YouTube certificates accepted by Morphe v1.45.0.
GOOGLE_YOUTUBE_CERTS = {
    "3d7a1223019aa39d9ea0e3436ab7c0896bfb4fb679f4de5fe7c23f326c8f994a",
    "5aad2bee6db95d17e05a08d7d1e64c10a1511879154483916b6ae6c7fd9cb0c6",
}


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def u64(data: bytes, offset: int) -> int:
    return struct.unpack_from("<Q", data, offset)[0]


def lp(data: bytes, offset: int) -> tuple[bytes, int]:
    if offset + 4 > len(data):
        raise ValueError("truncated length-prefixed field")
    size = u32(data, offset)
    start = offset + 4
    end = start + size
    if end > len(data):
        raise ValueError("length-prefixed field exceeds buffer")
    return data[start:end], end


def signing_block(data: bytes) -> bytes:
    tail_start = max(0, len(data) - (65535 + 22 + 4096))
    eocd = data.rfind(EOCD, tail_start)
    if eocd < 0 or eocd + 22 > len(data):
        raise ValueError("ZIP EOCD not found")

    cd_offset = u32(data, eocd + 16)
    if cd_offset < 24 or cd_offset > len(data):
        raise ValueError("invalid central-directory offset")

    footer = data[cd_offset - 24 : cd_offset]
    if len(footer) != 24 or footer[8:] != MAGIC:
        raise ValueError("APK Signing Block magic not found")

    size_footer = u64(footer, 0)
    start = cd_offset - (size_footer + 8)
    if start < 0 or u64(data, start) != size_footer:
        raise ValueError("invalid APK Signing Block size")

    return data[start:cd_offset]


def scheme_pairs(block: bytes):
    offset = 8
    end = len(block) - 24
    while offset < end:
        if offset + 8 > end:
            raise ValueError("truncated signing pair")
        size = u64(block, offset)
        offset += 8
        pair_end = offset + size
        if size < 4 or pair_end > end:
            raise ValueError("invalid signing pair size")
        scheme_id = u32(block, offset)
        yield scheme_id, block[offset + 4 : pair_end]
        offset = pair_end


def certificates_from_scheme(value: bytes):
    signers, _ = lp(value, 0)
    offset = 0
    while offset < len(signers):
        signer, offset = lp(signers, offset)
        signed_data, _ = lp(signer, 0)

        # signed-data begins with digests, then certificates for v2/v3/v3.1.
        _, p = lp(signed_data, 0)
        certs, _ = lp(signed_data, p)

        cert_offset = 0
        while cert_offset < len(certs):
            cert, cert_offset = lp(certs, cert_offset)
            yield cert


def certificate_hashes(data: bytes) -> set[str]:
    result: set[str] = set()
    block = signing_block(data)

    for scheme_id, value in scheme_pairs(block):
        if scheme_id not in SCHEME_IDS:
            continue
        for cert in certificates_from_scheme(value):
            result.add(hashlib.sha256(cert).hexdigest())

    return result


def source_apk_bytes(path: Path) -> tuple[bytes, str, bool]:
    suffix = path.suffix.lower()
    if suffix == ".apk":
        return path.read_bytes(), path.name, False

    if suffix not in {".apkm", ".apks", ".xapk"}:
        raise ValueError("unsupported source format")

    with zipfile.ZipFile(path) as zf:
        apk_names = [name for name in zf.namelist() if name.lower().endswith(".apk")]
        if not apk_names:
            raise ValueError("bundle contains no APK entries")

        preferred = next(
            (name for name in apk_names if Path(name).name.lower() == "base.apk"),
            apk_names[0],
        )
        return zf.read(preferred), preferred, True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("patched", type=Path)
    parser.add_argument("--print-only", action="store_true")
    args = parser.parse_args()

    source_data, source_entry, source_is_bundle = source_apk_bytes(args.source)
    patched_data = args.patched.read_bytes()

    source_block = signing_block(source_data)
    patched_block = signing_block(patched_data)
    source_certs = certificate_hashes(source_data)
    patched_certs = certificate_hashes(patched_data)

    print(f"source_entry={source_entry}")
    print(f"source_signing_block_sha256={hashlib.sha256(source_block).hexdigest()}")
    print(f"patched_signing_block_sha256={hashlib.sha256(patched_block).hexdigest()}")
    print("source_cert_sha256=" + ",".join(sorted(source_certs)))
    print("patched_cert_sha256=" + ",".join(sorted(patched_certs)))

    if args.print_only:
        return 0

    if not source_certs or not (source_certs & GOOGLE_YOUTUBE_CERTS):
        print("ERROR: source is not signed with a recognized Google YouTube certificate")
        return 2

    if source_certs != patched_certs:
        print("ERROR: patched APK certificate set differs from source")
        return 3

    # A direct APK should retain the entire original block. A split bundle can
    # legitimately get a differently laid-out merged block while keeping certs.
    if not source_is_bundle and source_block != patched_block:
        print("ERROR: direct-APK signing block changed")
        return 4

    print("OK: Google YouTube signing identity preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
