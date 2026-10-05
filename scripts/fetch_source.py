#!/usr/bin/env python3
from __future__ import annotations

import argparse
import http.cookiejar
import os
import re
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from html.parser import HTMLParser
from pathlib import Path

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/152 Safari/537.36"
APK_EXTS = {".apk", ".apkm", ".apks", ".xapk"}


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.meta_refresh: list[str] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a" and d.get("href"):
            self._href = d["href"]
            self._text = []
        if tag == "meta" and d.get("http-equiv", "").lower() == "refresh":
            content = d.get("content", "")
            m = re.search(r"url\s*=\s*['\"]?([^'\"]+)", content, re.I)
            if m:
                self.meta_refresh.append(m.group(1))

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join(self._text).strip()))
            self._href = None
            self._text = []


def opener():
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def request(op, url: str, referer: str | None = None):
    headers = {
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if referer:
        headers["Referer"] = referer
    return op.open(urllib.request.Request(url, headers=headers), timeout=60)


def is_binary_response(resp, url: str) -> bool:
    ctype = (resp.headers.get("Content-Type") or "").lower()
    dispo = (resp.headers.get("Content-Disposition") or "").lower()
    path = urllib.parse.urlparse(url).path.lower()
    if any(path.endswith(ext) for ext in APK_EXTS):
        return True
    if "attachment" in dispo:
        return True
    return any(x in ctype for x in ("application/vnd.android.package-archive", "application/octet-stream", "application/zip"))


def is_release_overview(url: str) -> bool:
    path = urllib.parse.urlparse(url).path.rstrip("/").lower()
    return path.endswith("-release")


def link_context(html: str, href: str) -> str:
    """Return nearby row text for an APKMirror variant link."""
    needle = href.replace("&", "&amp;")
    pos = html.find(needle)
    if pos < 0:
        pos = html.find(href)
    if pos < 0:
        return ""

    row_start = html.rfind('<div class="table-row', 0, pos)
    if row_start < 0:
        row_start = max(0, pos - 1500)

    row_end = html.find('<div class="table-row', pos + 1)
    if row_end < 0:
        row_end = min(len(html), pos + 2500)

    chunk = html[row_start:row_end]
    chunk = re.sub(r"<[^>]+>", " ", chunk)
    chunk = chunk.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\\s+", " ", chunk).strip()


def score_link(base: str, href: str, text: str) -> int:
    u = urllib.parse.urljoin(base, href)
    p = urllib.parse.urlparse(u)
    path = p.path.lower()
    q = p.query.lower()
    txt = text.lower()

    if not u.startswith(("http://", "https://")):
        return -1
    if "premium" in u or "sign-in" in u:
        return -1
    if path.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg")):
        return -1

    if (
        p.hostname
        and p.hostname.startswith(("downloadr", "download"))
        and "apkmirror" in p.hostname
        and (
            any(path.endswith(ext) for ext in APK_EXTS)
            or "download" in path
            or "key=" in q
        )
    ):
        return 1000
    if "download.php" in path:
        return 950
    if "/download/" in path and "key=" in q:
        return 900
    if "download apk bundle" in txt or "download apk" in txt:
        return 850
    if "download" in txt and "apkmirror" in p.netloc:
        return 800
    if path.endswith("-android-apk-download/"):
        return 700
    if "android-apk-download" in path:
        return 650
    if any(path.endswith(ext) for ext in APK_EXTS):
        return 600
    return -1


def resolve_apkmirror(url: str, out_tmp: Path) -> tuple[Path, str]:
    op = opener()
    current = url
    referer = None
    seen = set()

    for _ in range(8):
        if current in seen:
            raise RuntimeError(f"APKMirror resolver looped at {current}")
        seen.add(current)

        with request(op, current, referer) as resp:
            final_url = resp.geturl()
            if is_binary_response(resp, final_url):
                with out_tmp.open("wb") as f:
                    shutil.copyfileobj(resp, f, length=1024 * 1024)
                return out_tmp, final_url

            data = resp.read(5 * 1024 * 1024)
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if b"PK\x03\x04" == data[:4] and "text/html" not in ctype:
                # The probe above is intentionally bounded. Re-open and stream
                # the whole binary so we never save a truncated APK/APKM.
                with request(op, final_url, referer) as binary_resp:
                    with out_tmp.open("wb") as f:
                        shutil.copyfileobj(binary_resp, f, length=1024 * 1024)
                return out_tmp, final_url

        html = data.decode("utf-8", "replace")
        parser = LinkParser()
        parser.feed(html)

        candidates = []
        release_page = is_release_overview(final_url)

        for href, text in parser.links:
            absolute = urllib.parse.urljoin(final_url, href)
            s = score_link(final_url, href, text)
            if s < 0:
                continue

            # On a version overview page APKMirror can list many variants.
            # Prefer the variant whose row says "universal". Direct variant,
            # keyed download and file URLs keep their existing behavior.
            if release_page and "android-apk-download" in urllib.parse.urlparse(absolute).path.lower():
                context = f"{text} {link_context(html, href)}".lower()
                if re.search(r"\\buniversal\\b", context):
                    s += 5000

            candidates.append((s, absolute))

        for refresh in parser.meta_refresh:
            absolute = urllib.parse.urljoin(final_url, refresh)
            candidates.append((925, absolute))

        if not candidates:
            raise RuntimeError(
                "Could not find an APKMirror download link. "
                "Use a YouTube release/variant/download page or a direct file URL."
            )

        candidates.sort(key=lambda x: x[0], reverse=True)
        referer = final_url
        current = candidates[0][1]

    raise RuntimeError("APKMirror resolver exceeded maximum redirect/page depth")


def download_direct(url: str, out_tmp: Path) -> tuple[Path, str]:
    op = opener()
    with request(op, url) as resp:
        final_url = resp.geturl()
        with out_tmp.open("wb") as f:
            shutil.copyfileobj(resp, f, length=1024 * 1024)
    return out_tmp, final_url


def detect_extension(path: Path, source_url: str) -> str:
    url_path = urllib.parse.urlparse(source_url).path.lower()
    for ext in APK_EXTS:
        if url_path.endswith(ext):
            return ext

    if not zipfile.is_zipfile(path):
        raise RuntimeError("Downloaded file is not an APK/ZIP bundle")

    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        nested_apks = [n for n in names if n.lower().endswith(".apk")]
        if nested_apks:
            return ".apkm"
        if "AndroidManifest.xml" in names:
            return ".apk"

    raise RuntimeError("Could not determine whether downloaded file is APK or APK bundle")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--output-dir", default="input")
    ap.add_argument("--name", default="youtube-original")
    args = ap.parse_args()

    parsed = urllib.parse.urlparse(args.url)
    if parsed.scheme not in {"http", "https"}:
        raise SystemExit("Only http/https URLs are supported")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="yt-source-") as td:
        tmp = Path(td) / "download.bin"
        host = (parsed.hostname or "").lower()

        if host == "apkmirror.com" or host.endswith(".apkmirror.com"):
            downloaded, final_url = resolve_apkmirror(args.url, tmp)
        else:
            downloaded, final_url = download_direct(args.url, tmp)

        if downloaded.stat().st_size < 1024 * 1024:
            raise RuntimeError(f"Downloaded file is unexpectedly small: {downloaded.stat().st_size} bytes")

        ext = detect_extension(downloaded, final_url)
        target = out_dir / f"{args.name}{ext}"
        shutil.copy2(downloaded, target)

    print(f"SOURCE_FILE={target.resolve()}")
    print(f"SOURCE_FORMAT={ext.lstrip('.')}")
    print(f"SOURCE_SIZE={target.stat().st_size}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
