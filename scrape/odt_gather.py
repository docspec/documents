#!/usr/bin/env python3
"""Gather ODT (OpenDocument Text) test files from open-source test suites.

Sources:
  - LibreOffice Writer ODF import/export test data (MPL-2.0)
"""

import json
import os
import sys
import time
from pathlib import Path

import requests

# Allow running as `python scrape/odt_gather.py` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import (
    MAGIC_EPUB,  # ODT shares ZIP magic bytes (PK\x03\x04)
    check_file_size,
    download_file,
    rate_limit,
    sanitize_filename,
    validate_file_format,
)

MAGIC_ODT = MAGIC_EPUB  # Both are ZIP-based formats

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "documents" / "odt"
ATTRIBUTION_PATH = REPO_ROOT / "ATTRIBUTION.json"

SESSION = requests.Session()
SESSION.headers["User-Agent"] = (
    "DocSpec-Corpus-Scraper/1.0 (https://github.com/docspec/documents)"
)
_gh_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
if _gh_token:
    SESSION.headers["Authorization"] = f"token {_gh_token}"


# ── GitHub helpers ────────────────────────────────────────────────────────────


def github_list_files(api_url: str, extension: str = ".odt") -> list[dict]:
    """List files from a GitHub contents API endpoint."""
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


def download_and_validate(url: str, dest: Path, min_bytes: int = 200) -> bool:
    """Download a file and validate it's a genuine ZIP-based ODT."""
    if dest.exists():
        if validate_file_format(dest, MAGIC_ODT) and check_file_size(dest, min_bytes):
            return True

    ok = download_file(url, dest, delay=1.0, session=SESSION)
    if not ok:
        print(f"  ✗ Download failed: {dest.name}")
        return False

    if not validate_file_format(dest, MAGIC_ODT):
        print(f"  ✗ Not ZIP/ODT format: {dest.name} — removing")
        dest.unlink(missing_ok=True)
        return False

    if not check_file_size(dest, min_bytes):
        print(f"  ✗ Too small (<{min_bytes}B): {dest.name} — removing")
        dest.unlink(missing_ok=True)
        return False

    return True


# ── Source: LibreOffice ODF test data ─────────────────────────────────────────


def gather_libreoffice(dest: Path) -> int:
    """Download .odt files from LibreOffice ODF test data directories."""
    dest.mkdir(parents=True, exist_ok=True)

    print("\n📦 LibreOffice ODF test data")
    print("=" * 50)

    # All directories known to contain .odt test fixtures
    api_base = "https://api.github.com/repos/LibreOffice/core/contents"
    directories = [
        "sw/qa/extras/odfimport/data",
        "sw/qa/extras/odfexport/data",
        "sw/qa/extras/globalfilter/data",
        "sw/qa/extras/ww8export/data",
        "sw/qa/core/data/odt",
        "xmloff/qa/unit/data",
    ]

    all_files: list[dict] = []
    seen_names: set[str] = set()

    for directory in directories:
        api_url = f"{api_base}/{directory}"
        print(f"\n  Scanning: {directory}")
        files = github_list_files(api_url, ".odt")
        new = 0
        for f in files:
            key = f["name"].lower()
            if key not in seen_names:
                seen_names.add(key)
                all_files.append(f)
                new += 1
        print(f"  Found {len(files)} .odt files ({new} new unique)")

    print(f"\n  Total unique .odt files to download: {len(all_files)}")

    count = 0
    for i, finfo in enumerate(all_files, 1):
        safe_name = sanitize_filename(finfo["name"])
        file_dest = dest / safe_name
        if download_and_validate(finfo["download_url"], file_dest):
            count += 1
        if i % 50 == 0:
            print(f"  … processed {i}/{len(all_files)} ({count} valid)")

    print(f"\n  Total LibreOffice: {count} valid .odt files")
    return count


# ── ATTRIBUTION.json update ───────────────────────────────────────────────────

ATTRIBUTION_ENTRY = {
    "format": "odt",
    "path": "documents/odt/libreoffice/*.odt",
    "title": "LibreOffice Writer ODF Test Data",
    "author": "The Document Foundation and LibreOffice contributors",
    "license": "MPL-2.0",
    "source": "https://github.com/LibreOffice/core",
    "tags": ["libreoffice", "odt", "odf", "test-fixtures"],
    "donated": "2026-04-01",
    "notes": "ODF import/export test data from LibreOffice Writer QA (triple-licensed MPL-2.0/LGPL-3.0+/GPL-3.0+; redistributed under MPL-2.0)",
}


def update_attribution() -> None:
    """Add ODT entry to ATTRIBUTION.json if not already present."""
    print("\n📝 Updating ATTRIBUTION.json")

    data = json.loads(ATTRIBUTION_PATH.read_text())
    existing_paths = {entry["path"] for entry in data}

    if ATTRIBUTION_ENTRY["path"] not in existing_paths:
        data.append(ATTRIBUTION_ENTRY)
        ATTRIBUTION_PATH.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        )
        print(f"  + Added: {ATTRIBUTION_ENTRY['path']}")
    else:
        print(f"  ≡ Already present: {ATTRIBUTION_ENTRY['path']}")


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    print("🔧 DocSpec ODT corpus gatherer")
    print("=" * 60)

    count = gather_libreoffice(DOCS_DIR / "libreoffice")

    print(f"\n{'=' * 60}")
    print(f"📊 Total valid .odt files downloaded: {count}")

    if count < 50:
        print(f"⚠️  Only {count} files — below target of 50")
        print("   Consider running with GITHUB_TOKEN for higher API limits")
    else:
        print(f"✅ Target met: {count} ≥ 50")

    update_attribution()

    # Summary
    print(f"\n{'=' * 60}")
    odt_files = list(DOCS_DIR.rglob("*.odt"))
    print(f"Total ODT files on disk: {len(odt_files)}")
    for group_dir in sorted(DOCS_DIR.iterdir()):
        if group_dir.is_dir():
            n = len(list(group_dir.glob("*.odt")))
            print(f"  {group_dir.name}: {n}")


if __name__ == "__main__":
    main()
