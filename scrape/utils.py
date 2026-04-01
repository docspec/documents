"""Shared utilities for DocSpec document corpus scrapers."""

import re
import time
import unicodedata
import urllib.robotparser
from pathlib import Path
from typing import Optional

import requests

# ── Rate limiting ─────────────────────────────────────────────────────────────

_last_request_time: float = 0.0


def rate_limit(delay: float = 2.0) -> None:
    """Block until at least `delay` seconds have passed since the last call."""
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < delay:
        time.sleep(delay - elapsed)
    _last_request_time = time.monotonic()


# ── Robots.txt compliance ─────────────────────────────────────────────────────

_robots_cache: dict = {}


def check_robots_txt(url: str, user_agent: str = "*") -> bool:
    """Return True if scraping `url` is allowed by robots.txt."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    if base not in _robots_cache:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"{base}/robots.txt")
        try:
            rp.read()
        except Exception:
            _robots_cache[base] = None
            return True
        _robots_cache[base] = rp
    rp = _robots_cache[base]
    if rp is None:
        return True
    return rp.can_fetch(user_agent, url)


# ── License validation ────────────────────────────────────────────────────────

# CC-BY-ND defeats the purpose of conversion testing — reject it
_REJECTED_PATTERNS = ["-ND-", "-ND"]


def validate_license(license_id: str) -> bool:
    """Return True if license is allowed (not CC-BY-ND, not empty)."""
    if not license_id or not license_id.strip():
        return False
    for pattern in _REJECTED_PATTERNS:
        if pattern in license_id:
            return False
    return True


# ── Filename sanitization ─────────────────────────────────────────────────────


def sanitize_filename(name: str) -> str:
    """Convert a filename to an ASCII-safe lowercase slug, preserving extension.

    Examples:
        "Hello World (2024) — Draft.doc"  ->  "hello-world-2024-draft.doc"
        "Über-Dokument.rtf"               ->  "uber-dokument.rtf"
    """
    stem, _, ext = name.rpartition(".")
    if not stem:
        stem, ext = ext, ""

    # Normalize unicode (é -> e, ü -> u, em-dash -> nothing, etc.)
    stem = unicodedata.normalize("NFKD", stem)
    stem = stem.encode("ascii", "ignore").decode("ascii")

    stem = stem.lower()
    stem = re.sub(r"[^a-z0-9]+", "-", stem)
    stem = re.sub(r"-+", "-", stem).strip("-")

    return f"{stem}.{ext.lower()}" if ext else stem


# ── File format validation ────────────────────────────────────────────────────

# Magic bytes constants
MAGIC_OLE2 = b"\xd0\xcf\x11\xe0"  # .doc WW8 (OLE2 compound binary)
MAGIC_EPUB = b"PK\x03\x04"  # .epub (ZIP-based)


def validate_file_format(filepath, expected_magic: bytes) -> bool:
    """Return True if the file starts with expected_magic bytes."""
    p = Path(filepath)
    if not p.exists():
        return False
    with open(p, "rb") as f:
        return f.read(len(expected_magic)) == expected_magic


def validate_rtf(filepath) -> bool:
    """Return True if the file starts with {\\rtf (RTF magic prefix)."""
    p = Path(filepath)
    if not p.exists():
        return False
    with open(p, "rb") as f:
        return f.read(5).startswith(b"{\\rtf")


# ── File size check ───────────────────────────────────────────────────────────


def check_file_size(filepath, min_bytes: int = 100) -> bool:
    """Return True if the file exists and is at least min_bytes in size."""
    p = Path(filepath)
    return p.exists() and p.stat().st_size >= min_bytes


# ── Download with retry ───────────────────────────────────────────────────────


def download_file(
    url: str,
    dest,
    delay: float = 2.0,
    max_retries: int = 3,
    timeout: int = 30,
    session: Optional[requests.Session] = None,
) -> bool:
    """Download url to dest with rate limiting and exponential backoff on 429.

    Returns True on success, False on failure.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    sess = session or requests.Session()
    sess.headers.setdefault(
        "User-Agent",
        "DocSpec-Corpus-Scraper/1.0 (https://github.com/docspec/documents)",
    )

    for attempt in range(max_retries):
        rate_limit(delay)
        try:
            resp = sess.get(url, timeout=timeout, stream=True)
            if resp.status_code == 429:
                wait = 2**attempt * delay
                print(f"  Rate limited (429), waiting {wait:.1f}s…")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except requests.RequestException as e:
            print(f"  Download failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2**attempt)
    return False
