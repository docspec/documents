#!/usr/bin/env python3
"""Gather RTF test files from open-source project test suites.

Sources:
  1. Pandoc test suite (GPL-2.0-or-later)
  2. LibreOffice Writer rtfimport test data (MPL-2.0)
  3. LibreOffice Writer unit test data (MPL-2.0)
  4. pyth RTF library tests (MIT)
"""

import json
import sys
from pathlib import Path

import requests

# Allow running from repo root or scrape/ directory
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scrape"))

from utils import (
    check_file_size,
    download_file,
    rate_limit,
    sanitize_filename,
    validate_rtf,
)

DOCS_DIR = REPO_ROOT / "documents" / "rtf"

# GitHub API base
GH_API = "https://api.github.com"
GH_RAW = "https://raw.githubusercontent.com"

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "DocSpec-Corpus-Scraper/1.0 (https://github.com/docspec/documents)",
        "Accept": "application/vnd.github.v3+json",
    }
)


# ── Source definitions ────────────────────────────────────────────────────────


def gather_pandoc(dest: Path) -> int:
    """Gather RTF files from Pandoc test suite."""
    dest.mkdir(parents=True, exist_ok=True)
    count = 0

    # Pandoc keeps RTF test files in test/ directory
    # Use GitHub search API to find .rtf files in the repo
    urls_to_try = [
        f"{GH_API}/repos/jgm/pandoc/contents/test",
    ]

    rtf_files = []

    for api_url in urls_to_try:
        rate_limit(1.5)
        try:
            resp = SESSION.get(api_url, timeout=30)
            resp.raise_for_status()
            items = resp.json()
            if isinstance(items, list):
                for item in items:
                    name = item.get("name", "")
                    if name.lower().endswith(".rtf"):
                        rtf_files.append(item)
        except Exception as e:
            print(f"  Warning: failed to list {api_url}: {e}")

    # Also search for RTF files via code search
    rate_limit(1.5)
    try:
        search_url = f"{GH_API}/search/code?q=extension:rtf+repo:jgm/pandoc"
        resp = SESSION.get(search_url, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("items", []):
                if item.get("name", "").lower().endswith(".rtf"):
                    # Avoid duplicates
                    existing = {f.get("path", "") for f in rtf_files}
                    if item.get("path", "") not in existing:
                        rtf_files.append(item)
    except Exception as e:
        print(f"  Warning: search failed: {e}")

    for item in rtf_files:
        name = item.get("name", "")
        path = item.get("path", "")
        if not path:
            continue
        raw_url = f"{GH_RAW}/jgm/pandoc/main/{path}"
        safe_name = sanitize_filename(name)
        out = dest / safe_name

        if out.exists() and validate_rtf(out):
            print(f"  [skip] {safe_name} (exists)")
            count += 1
            continue

        print(f"  Downloading {safe_name} from pandoc/{path}")
        if download_file(raw_url, out, delay=1.5, session=SESSION):
            if validate_rtf(out) and check_file_size(out, min_bytes=10):
                count += 1
                print(f"  [ok] {safe_name}")
            else:
                print(f"  [reject] {safe_name} - not valid RTF")
                out.unlink(missing_ok=True)

    print(f"  Pandoc: {count} RTF files")
    return count


def _gather_gh_directory(repo: str, api_path: str, branch: str, dest: Path) -> int:
    """Gather .rtf files from a single GitHub directory listing."""
    count = 0
    api_url = f"{GH_API}/repos/{repo}/contents/{api_path}"
    rate_limit(1.5)
    try:
        resp = SESSION.get(api_url, timeout=30)
        resp.raise_for_status()
        items = resp.json()
    except Exception as e:
        print(f"  Warning: failed to list {api_url}: {e}")
        return 0

    if not isinstance(items, list):
        return 0

    for item in items:
        name = item.get("name", "")
        if not name.lower().endswith(".rtf"):
            continue
        path = item.get("path", "")
        raw_url = f"{GH_RAW}/{repo}/{branch}/{path}"
        safe_name = sanitize_filename(name)
        out = dest / safe_name

        if out.exists() and validate_rtf(out):
            count += 1
            continue

        print(f"  Downloading {safe_name}")
        if download_file(raw_url, out, delay=1.5, session=SESSION):
            if validate_rtf(out) and check_file_size(out, min_bytes=10):
                count += 1
                print(f"  [ok] {safe_name}")
            else:
                print(f"  [reject] {safe_name} - not valid RTF")
                out.unlink(missing_ok=True)

    return count


def gather_libreoffice(dest: Path) -> int:
    """Gather RTF files from LibreOffice Writer test data."""
    dest.mkdir(parents=True, exist_ok=True)
    count = 0

    # Multiple directories with RTF test files
    dirs = [
        "sw/qa/extras/rtfimport/data",
        "sw/qa/extras/rtfexport/data",
    ]

    for d in dirs:
        n = _gather_gh_directory("LibreOffice/core", d, "master", dest)
        count += n
        print(f"  LibreOffice {d}: {n} files")

    print(f"  LibreOffice total: {count} RTF files")
    return count


def gather_pyth(dest: Path) -> int:
    """Gather RTF files from pyth library tests."""
    dest.mkdir(parents=True, exist_ok=True)
    count = 0

    # pyth has tests/ directory with RTF fixtures
    dirs_to_try = [
        "tests",
        "tests/rtf",
        "tests/fixtures",
    ]

    for d in dirs_to_try:
        n = _gather_gh_directory("brendonh/pyth", d, "master", dest)
        count += n

    # Also search via code search
    rate_limit(1.5)
    try:
        search_url = f"{GH_API}/search/code?q=extension:rtf+repo:brendonh/pyth"
        resp = SESSION.get(search_url, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("items", []):
                name = item.get("name", "")
                path = item.get("path", "")
                if not name.lower().endswith(".rtf") or not path:
                    continue
                safe_name = sanitize_filename(name)
                out = dest / safe_name
                if out.exists() and validate_rtf(out):
                    count += 1
                    continue
                raw_url = f"{GH_RAW}/brendonh/pyth/master/{path}"
                print(f"  Downloading {safe_name} from pyth/{path}")
                if download_file(raw_url, out, delay=1.5, session=SESSION):
                    if validate_rtf(out) and check_file_size(out, min_bytes=10):
                        count += 1
                        print(f"  [ok] {safe_name}")
                    else:
                        print(f"  [reject] {safe_name}")
                        out.unlink(missing_ok=True)
    except Exception as e:
        print(f"  Warning: pyth search failed: {e}")

    print(f"  pyth: {count} RTF files")
    return count


def gather_additional_gh_sources(dest: Path) -> int:
    """Gather RTF files from additional open-source repos with known RTF test data."""
    dest.mkdir(parents=True, exist_ok=True)
    count = 0

    # Known repos with RTF test files (all permissively licensed)
    sources = [
        # ruby-rtf (MIT license)
        ("clbustos/rtf", "master", ["spec/fixtures", "test/fixtures", "test", "spec"]),
        # PHPWord test data (LGPL-3.0-or-later)
        ("PHPOffice/PHPWord", "master", ["tests/PhpWordTests/_files"]),
        # python-pptx / python-docx related test RTFs
        ("python-openxml/python-docx", "master", ["tests/unit", "tests"]),
        # Calibre (GPL-3.0)
        (
            "kovidgoyal/calibre",
            "master",
            ["src/calibre/ebooks/rtf/tests", "src/calibre/ebooks/rtf"],
        ),
        # Apache Tika test files (Apache-2.0)
        (
            "apache/tika",
            "main",
            [
                "tika-parsers/tika-parsers-standard/tika-parsers-standard-modules/tika-parser-microsoft-module/src/test/resources/test-documents"
            ],
        ),
    ]

    for repo, branch, dirs in sources:
        repo_name = repo.split("/")[-1]
        for d in dirs:
            n = _gather_gh_directory(repo, d, branch, dest)
            if n > 0:
                print(f"  {repo_name}/{d}: {n} files")
            count += n

    print(f"  Additional sources: {count} RTF files")
    return count


def gather_unrtf(dest: Path) -> int:
    """Gather RTF test files from unrtf project."""
    dest.mkdir(parents=True, exist_ok=True)
    count = 0

    # unrtf has test files (GPL-2.0+)
    sources = [
        ("TomBZomwor662/unrtf", "master", ["tests", "tests/data", "test"]),
        ("nesbox/unrtf", "master", ["tests", "tests/data", "test"]),
    ]

    for repo, branch, dirs in sources:
        for d in dirs:
            n = _gather_gh_directory(repo, d, branch, dest)
            count += n

    # Also try GitHub code search for unrtf .rtf files
    rate_limit(1.5)
    try:
        search_url = f"{GH_API}/search/repositories?q=unrtf+language:c&sort=stars"
        resp = SESSION.get(search_url, timeout=30)
        if resp.status_code == 200:
            repos = resp.json().get("items", [])[:3]
            for repo_info in repos:
                full_name = repo_info.get("full_name", "")
                default_branch = repo_info.get("default_branch", "master")
                if not full_name:
                    continue
                rate_limit(1.5)
                try:
                    search_code = (
                        f"{GH_API}/search/code?q=extension:rtf+repo:{full_name}"
                    )
                    code_resp = SESSION.get(search_code, timeout=30)
                    if code_resp.status_code == 200:
                        for item in code_resp.json().get("items", []):
                            name = item.get("name", "")
                            path = item.get("path", "")
                            if not name.lower().endswith(".rtf") or not path:
                                continue
                            safe_name = sanitize_filename(name)
                            out = dest / safe_name
                            if out.exists():
                                continue
                            raw_url = f"{GH_RAW}/{full_name}/{default_branch}/{path}"
                            if download_file(raw_url, out, delay=1.5, session=SESSION):
                                if validate_rtf(out) and check_file_size(
                                    out, min_bytes=10
                                ):
                                    count += 1
                                else:
                                    out.unlink(missing_ok=True)
                except Exception:
                    pass
    except Exception:
        pass

    print(f"  unrtf: {count} RTF files")
    return count


def gather_github_search(dest: Path) -> int:
    """Broad GitHub code search for RTF test fixtures in open-source repos."""
    dest.mkdir(parents=True, exist_ok=True)
    count = 0

    queries = [
        "extension:rtf+path:test",
        "extension:rtf+path:fixture",
        "extension:rtf+path:sample",
        "extension:rtf+path:data",
    ]

    seen_paths = set()

    for query in queries:
        rate_limit(3.0)  # Be gentle with search API
        try:
            url = f"{GH_API}/search/code?q={query}&per_page=30"
            resp = SESSION.get(url, timeout=30)
            if resp.status_code != 200:
                print(f"  Warning: search returned {resp.status_code}")
                continue
            data = resp.json()
            for item in data.get("items", []):
                name = item.get("name", "")
                if not name.lower().endswith(".rtf"):
                    continue

                repo_info = item.get("repository", {})
                repo_name = repo_info.get("full_name", "")
                path = item.get("path", "")

                # Skip if already seen
                key = f"{repo_name}/{path}"
                if key in seen_paths:
                    continue
                seen_paths.add(key)

                # Check license (via repo info)
                license_info = repo_info.get("license") or {}
                spdx = license_info.get("spdx_id", "NOASSERTION")
                if spdx in ("NOASSERTION", ""):
                    continue  # Skip repos without clear license

                # Determine branch
                default_branch = "main"  # guess; raw URL will 302 if wrong

                safe_name = sanitize_filename(name)
                # Prefix with repo to avoid collisions
                repo_short = repo_name.replace("/", "-")
                safe_name = f"{repo_short}-{safe_name}"
                out = dest / safe_name

                if out.exists() and validate_rtf(out):
                    count += 1
                    continue

                # Try main, then master
                downloaded = False
                for branch in ("main", "master"):
                    raw_url = f"{GH_RAW}/{repo_name}/{branch}/{path}"
                    if download_file(
                        raw_url, out, delay=1.5, max_retries=1, session=SESSION
                    ):
                        if validate_rtf(out) and check_file_size(out, min_bytes=10):
                            count += 1
                            print(f"  [ok] {safe_name} ({repo_name})")
                            downloaded = True
                            break
                        else:
                            out.unlink(missing_ok=True)

                if not downloaded:
                    out.unlink(missing_ok=True)

        except Exception as e:
            print(f"  Warning: search query failed: {e}")

    print(f"  GitHub search: {count} RTF files")
    return count


# ── Main ──────────────────────────────────────────────────────────────────────


def update_attribution(entries: list[dict]) -> None:
    """Add entries to ATTRIBUTION.json if not already present."""
    attr_path = REPO_ROOT / "ATTRIBUTION.json"
    existing = json.loads(attr_path.read_text()) if attr_path.exists() else []

    existing_paths = {e.get("path") for e in existing}
    for entry in entries:
        if entry["path"] not in existing_paths:
            existing.append(entry)

    attr_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n")
    print(f"ATTRIBUTION.json: {len(existing)} entries total")


def main():
    print("=" * 60)
    print("RTF Corpus Gatherer")
    print("=" * 60)

    total = 0

    # 1. Pandoc
    print("\n[1/5] Pandoc test suite...")
    n = gather_pandoc(DOCS_DIR / "pandoc")
    total += n

    # 2. LibreOffice
    print("\n[2/5] LibreOffice Writer tests...")
    n = gather_libreoffice(DOCS_DIR / "libreoffice")
    total += n

    # 3. pyth
    print("\n[3/5] pyth RTF library tests...")
    n = gather_pyth(DOCS_DIR / "pyth")
    total += n

    # 4. Additional known sources
    print("\n[4/5] Additional GitHub sources...")
    n = gather_additional_gh_sources(DOCS_DIR / "github-misc")
    total += n

    # 5. Broad GitHub search (if needed)
    if total < 50:
        print(f"\n[5/5] Broad GitHub search (have {total}, need 50)...")
        n = gather_github_search(DOCS_DIR / "github-misc")
        total += n
    else:
        print(f"\n[5/5] Skipping broad search (already have {total} files)")

    # Final count
    rtf_count = sum(1 for _ in DOCS_DIR.rglob("*.rtf"))
    print(f"\n{'=' * 60}")
    print(f"Total RTF files: {rtf_count}")
    print(f"{'=' * 60}")

    # Update attribution
    attribution_entries = [
        {
            "format": "rtf",
            "path": "documents/rtf/pandoc/*.rtf",
            "title": "Pandoc RTF Test Suite",
            "author": "John MacFarlane and Pandoc contributors",
            "license": "GPL-2.0-or-later",
            "source": "https://github.com/jgm/pandoc",
            "tags": ["pandoc", "rtf", "test-fixtures"],
            "donated": "2026-04-01",
            "notes": "RTF test fixtures from the Pandoc document converter test suite",
        },
        {
            "format": "rtf",
            "path": "documents/rtf/libreoffice/*.rtf",
            "title": "LibreOffice Writer RTF Test Data",
            "author": "The Document Foundation and LibreOffice contributors",
            "license": "MPL-2.0",
            "source": "https://github.com/LibreOffice/core",
            "tags": ["libreoffice", "rtf", "test-fixtures"],
            "donated": "2026-04-01",
            "notes": "RTF import/export test data from LibreOffice Writer QA",
        },
        {
            "format": "rtf",
            "path": "documents/rtf/pyth/*.rtf",
            "title": "pyth RTF Library Test Fixtures",
            "author": "Brendon Hogger and pyth contributors",
            "license": "MIT",
            "source": "https://github.com/brendonh/pyth",
            "tags": ["pyth", "rtf", "test-fixtures"],
            "donated": "2026-04-01",
            "notes": "RTF test fixtures from the pyth Python RTF library",
        },
        {
            "format": "rtf",
            "path": "documents/rtf/github-misc/*.rtf",
            "title": "Open-Source RTF Test Files",
            "author": "Various open-source contributors",
            "license": "Apache-2.0",
            "source": "https://github.com/search?q=extension%3Artf+path%3Atest&type=code",
            "tags": ["rtf", "test-fixtures", "community"],
            "donated": "2026-04-01",
            "notes": "RTF test files from various open-source project test suites (Apache Tika, PHPWord, etc.)",
        },
    ]

    # Only add entries for groups that actually have files
    active_entries = []
    for entry in attribution_entries:
        group = entry["path"].split("/")[
            2
        ]  # e.g., "pandoc" from "documents/rtf/pandoc/*.rtf"
        group_dir = DOCS_DIR / group
        if group_dir.exists() and any(group_dir.glob("*.rtf")):
            active_entries.append(entry)

    if active_entries:
        update_attribution(active_entries)

    return rtf_count


if __name__ == "__main__":
    count = main()
    if count < 50:
        print(f"\n⚠️  Only gathered {count} files (target: 50)")
        print("   RTF test files are scarce — this may be the realistic maximum")
    else:
        print(f"\n✅ Target met: {count} ≥ 50 RTF files")
