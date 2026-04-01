#!/usr/bin/env python3
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scrape.utils import (
    sanitize_filename,
    download_file,
    validate_file_format,
    check_file_size,
    rate_limit,
    MAGIC_EPUB,
)
import requests

DEST = Path("documents/epub/standard-ebooks")
DEST.mkdir(parents=True, exist_ok=True)
TARGET = 110
BASE = "https://standardebooks.org"

session = requests.Session()
session.headers["User-Agent"] = (
    "DocSpec-Corpus-Scraper/1.0 (https://github.com/docspec/documents)"
)

ebook_paths: list[str] = []
page = 1
while len(ebook_paths) < TARGET:
    print(f"Fetching listing page {page}...")
    rate_limit(2.0)
    resp = session.get(f"{BASE}/ebooks?page={page}", timeout=30)
    if resp.status_code == 404:
        break
    resp.raise_for_status()
    found = sorted(set(re.findall(r'href="(/ebooks/[a-z0-9][^"]+)"', resp.text)))
    new = [
        p
        for p in found
        if not p.endswith("/") and "/downloads/" not in p and p.count("/") >= 2
    ]
    ebook_paths.extend(new)
    if not new:
        break
    page += 1

ebook_paths = list(dict.fromkeys(ebook_paths))
print(f"Found {len(ebook_paths)} unique ebook paths")

downloaded = 0
skipped = 0
failed = 0

for ebook_path in ebook_paths:
    if downloaded >= TARGET:
        break

    slug = ebook_path.removeprefix("/ebooks/")
    filename_stem = slug.replace("/", "_")
    fname = f"{filename_stem}.epub"
    dest = DEST / fname
    epub_url = f"{BASE}{ebook_path}/downloads/{filename_stem}.epub"

    if dest.exists():
        if validate_file_format(dest, MAGIC_EPUB) and check_file_size(dest, 1000):
            downloaded += 1
            skipped += 1
            print(f"  Already exists: {fname} ({downloaded}/{TARGET})")
            continue
        else:
            print(f"  Removing invalid file: {fname}")
            dest.unlink()

    print(f"Downloading: {fname}")
    ok = download_file(epub_url, dest, delay=2.0, session=session)
    if ok and validate_file_format(dest, MAGIC_EPUB) and check_file_size(dest, 1000):
        downloaded += 1
        print(f"  OK ({downloaded}/{TARGET})")
    else:
        failed += 1
        print(f"  FAILED or invalid")
        if dest.exists():
            dest.unlink()

print(f"\nSummary:")
print(f"  Downloaded: {downloaded} EPUBs")
print(f"  Already existed (skipped): {skipped}")
print(f"  Failed: {failed}")

total = len(list(DEST.glob("*.epub")))
print(f"  Total EPUBs in {DEST}: {total}")
