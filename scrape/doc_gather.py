#!/usr/bin/env python3
"""Gather legacy .doc (WW8/OLE2) test files from open-source test suites.

Sources:
  - Apache POI HWPF test data (Apache-2.0)
  - LibreOffice WW8 import test data (MPL-2.0)
"""

import json
import sys
import time
from pathlib import Path

import requests

# Allow running as `python scrape/doc_gather.py` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import (
    MAGIC_OLE2,
    check_file_size,
    download_file,
    rate_limit,
    sanitize_filename,
    validate_file_format,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "documents" / "doc"
ATTRIBUTION_PATH = REPO_ROOT / "ATTRIBUTION.json"

SESSION = requests.Session()
SESSION.headers["User-Agent"] = (
    "DocSpec-Corpus-Scraper/1.0 (https://github.com/docspec/documents)"
)
# GitHub token if available (for higher rate limits)
import os

_gh_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
if _gh_token:
    SESSION.headers["Authorization"] = f"token {_gh_token}"


# ── GitHub helpers ────────────────────────────────────────────────────────────


def github_list_files(api_url: str, extension: str = ".doc") -> list[dict]:
    """List files from a GitHub contents API endpoint. Returns list of {name, download_url}."""
    rate_limit(1.5)
    try:
        resp = SESSION.get(api_url, timeout=30)
        if resp.status_code == 403:
            remaining = resp.headers.get("X-RateLimit-Remaining", "?")
            print(f"  GitHub API rate limited (remaining={remaining}), waiting 60s…")
            time.sleep(60)
            resp = SESSION.get(api_url, timeout=30)
        resp.raise_for_status()
        items = resp.json()
        if not isinstance(items, list):
            print(f"  Unexpected response from {api_url}: not a list")
            return []
        return [
            {"name": item["name"], "download_url": item["download_url"]}
            for item in items
            if item.get("name", "").lower().endswith(extension)
            and item.get("type") == "file"
            and item.get("download_url")
        ]
    except Exception as e:
        print(f"  Error listing {api_url}: {e}")
        return []


def download_and_validate(url: str, dest: Path, min_bytes: int = 512) -> bool:
    """Download a file and validate it's genuine OLE2 format."""
    if dest.exists():
        if validate_file_format(dest, MAGIC_OLE2) and check_file_size(dest, min_bytes):
            print(f"  ✓ Already exists: {dest.name}")
            return True

    ok = download_file(url, dest, delay=1.0, session=SESSION)
    if not ok:
        print(f"  ✗ Download failed: {dest.name}")
        return False

    if not validate_file_format(dest, MAGIC_OLE2):
        print(f"  ✗ Not OLE2 format: {dest.name} — removing")
        dest.unlink(missing_ok=True)
        return False

    if not check_file_size(dest, min_bytes):
        print(f"  ✗ Too small (<{min_bytes}B): {dest.name} — removing")
        dest.unlink(missing_ok=True)
        return False

    print(f"  ✓ Downloaded: {dest.name}")
    return True


# ── Source: Apache POI ────────────────────────────────────────────────────────


def gather_apache_poi() -> int:
    """Download .doc files from Apache POI test data."""
    group_dir = DOCS_DIR / "apache-poi"
    group_dir.mkdir(parents=True, exist_ok=True)

    print("\n📦 Apache POI HWPF test data")
    print("=" * 50)

    # Try multiple known paths in the POI repo
    api_urls = [
        "https://api.github.com/repos/apache/poi/contents/test-data/document",
        "https://api.github.com/repos/apache/poi/contents/poi-scratchpad/src/test/resources/org/apache/poi/hwpf/data",
    ]

    all_files: list[dict] = []
    seen_names: set[str] = set()

    for api_url in api_urls:
        print(f"\n  Trying: {api_url}")
        files = github_list_files(api_url, ".doc")
        for f in files:
            if f["name"].lower() not in seen_names:
                seen_names.add(f["name"].lower())
                all_files.append(f)
        print(f"  Found {len(files)} .doc files")

    count = 0
    for finfo in all_files:
        safe_name = sanitize_filename(finfo["name"])
        dest = group_dir / safe_name
        if download_and_validate(finfo["download_url"], dest):
            count += 1

    print(f"\n  Total Apache POI: {count} valid .doc files")
    return count


# ── Source: LibreOffice ───────────────────────────────────────────────────────


def gather_libreoffice() -> int:
    """Download .doc files from LibreOffice WW8 test data."""
    group_dir = DOCS_DIR / "libreoffice"
    group_dir.mkdir(parents=True, exist_ok=True)

    print("\n📦 LibreOffice WW8 test data")
    print("=" * 50)

    # Multiple directories with WW8 test docs
    api_urls = [
        "https://api.github.com/repos/LibreOffice/core/contents/sw/qa/extras/ww8import/data",
        "https://api.github.com/repos/LibreOffice/core/contents/sw/qa/extras/ww8export/data",
        "https://api.github.com/repos/LibreOffice/core/contents/sw/qa/core/doc/data",
    ]

    all_files: list[dict] = []
    seen_names: set[str] = set()

    for api_url in api_urls:
        print(f"\n  Trying: {api_url}")
        files = github_list_files(api_url, ".doc")
        for f in files:
            if f["name"].lower() not in seen_names:
                seen_names.add(f["name"].lower())
                all_files.append(f)
        print(f"  Found {len(files)} .doc files (cumulative unique: {len(all_files)})")

    count = 0
    for finfo in all_files:
        safe_name = sanitize_filename(finfo["name"])
        dest = group_dir / safe_name
        if download_and_validate(finfo["download_url"], dest):
            count += 1

    print(f"\n  Total LibreOffice: {count} valid .doc files")
    return count


# ── ATTRIBUTION.json update ───────────────────────────────────────────────────

ATTRIBUTION_ENTRIES = [
    {
        "format": "doc",
        "path": "documents/doc/apache-poi/*.doc",
        "title": "Apache POI HWPF Test Documents",
        "author": "Apache POI contributors",
        "license": "Apache-2.0",
        "source": "https://github.com/apache/poi",
        "tags": ["apache-poi", "hwpf", "test-fixtures"],
        "donated": "2026-04-01",
        "notes": "Test fixtures for the Apache POI HWPF Word processor module",
    },
    {
        "format": "doc",
        "path": "documents/doc/libreoffice/*.doc",
        "title": "LibreOffice WW8 Import/Export Test Documents",
        "author": "LibreOffice contributors",
        "license": "MPL-2.0",
        "source": "https://github.com/LibreOffice/core",
        "tags": ["libreoffice", "ww8", "test-fixtures"],
        "donated": "2026-04-01",
        "notes": "Test fixtures for the LibreOffice WW8 import/export filters",
    },
]


def update_attribution() -> None:
    """Add doc entries to ATTRIBUTION.json if not already present."""
    print("\n📝 Updating ATTRIBUTION.json")

    # Re-read fresh (other tasks may have modified it)
    data = json.loads(ATTRIBUTION_PATH.read_text())

    existing_paths = {entry["path"] for entry in data}
    added = 0
    for entry in ATTRIBUTION_ENTRIES:
        if entry["path"] not in existing_paths:
            data.append(entry)
            added += 1
            print(f"  + Added: {entry['path']}")
        else:
            print(f"  ≡ Already present: {entry['path']}")

    if added:
        ATTRIBUTION_PATH.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        )
        print(f"  Wrote {added} new entries")
    else:
        print("  No changes needed")


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    print("🔧 DocSpec .doc (WW8) corpus gatherer")
    print("=" * 60)

    total = 0
    total += gather_apache_poi()
    total += gather_libreoffice()

    print(f"\n{'=' * 60}")
    print(f"📊 Total valid .doc files: {total}")

    if total < 50:
        print(f"⚠️  Only {total} files — below target of 50")
        print("   Consider running with GITHUB_TOKEN for higher API limits")
    else:
        print(f"✅ Target met: {total} ≥ 50")

    update_attribution()

    # Summary
    print(f"\n{'=' * 60}")
    doc_files = list(DOCS_DIR.rglob("*.doc"))
    print(f"Files on disk: {len(doc_files)}")
    for group_dir in sorted(DOCS_DIR.iterdir()):
        if group_dir.is_dir():
            count = len(list(group_dir.glob("*.doc")))
            print(f"  {group_dir.name}: {count}")


if __name__ == "__main__":
    main()
