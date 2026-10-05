#!/usr/bin/env python3
"""Compare APK Signing Block bytes without verifying the APK digest.

This is intentional for CorePatch-targeted builds: the patched APK keeps the
original Google signing block, while modifications make the cryptographic APK
digest invalid. CorePatch is expected to bypass that integrity mismatch.
"""
from __future__ import annotations

import argparse
import hashlib
import struct
from pathlib import Path

EOCD = b"PK\x05\x06"
MAGIC = b"APK Sig Block 42"


def signing_block(path: Path) -> bytes:
    data = path.read_bytes()
    tail_start = max(0, len(data) - (65535 + 22 + 4096))
    eocd = data.rfind(EOCD, tail_start)
    if eocd < 0:
        raise ValueError(f"{path}: ZIP EOCD not found")
    if eocd + 22 > len(data):
        raise ValueError(f"{path}: truncated EOCD")

    cd_offset = struct.unpack_from("<I", data, eocd + 16)[0]
    if cd_offset < 24 or cd_offset > len(data):
        raise ValueError(f"{path}: invalid central-directory offset {cd_offset}")

    footer = data[cd_offset - 24 : cd_offset]
    size_footer = struct.unpack_from("<Q", footer, 0)[0]
    if footer[8:] != MAGIC:
        raise ValueError(f"{path}: APK Signing Block magic not found")

    block_start = cd_offset - (size_footer + 8)
    if block_start < 0:
        raise ValueError(f"{path}: invalid APK Signing Block size")
    size_header = struct.unpack_from("<Q", data, block_start)[0]
    if size_header != size_footer:
        raise ValueError(f"{path}: signing-block header/footer sizes differ")

    return data[block_start:cd_offset]


def digest(block: bytes) -> str:
    return hashlib.sha256(block).hexdigest()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("source", type=Path)
    p.add_argument("patched", type=Path)
    p.add_argument("--print-only", action="store_true")
    args = p.parse_args()

    src = signing_block(args.source)
    out = signing_block(args.patched)
    src_sha = digest(src)
    out_sha = digest(out)
    print(f"source_signing_block_sha256={src_sha}")
    print(f"patched_signing_block_sha256={out_sha}")
    print(f"source_signing_block_size={len(src)}")
    print(f"patched_signing_block_size={len(out)}")

    if args.print_only:
        return 0
    if src != out:
        print("ERROR: patched APK did not preserve the original signing block", flush=True)
        return 2
    print("OK: original signing block preserved byte-for-byte")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
