#!/usr/bin/env python3
"""
Scrape standalone HTML files from openly-licensed repositories for the
DocSpec test corpus.

Sources:
  1. MDN Learning Area       — CC-BY-SA-2.5   (github.com/mdn/learning-area)
  2. W3C Web Platform Tests  — W3C-20150513   (github.com/web-platform-tests/wpt)
  3. HTML5 Boilerplate       — MIT            (github.com/h5bp/html5-boilerplate)

Strategy: sparse-clone via git (bypasses GitHub API rate limits), then copy
and validate the HTML files into documents/html/<group>/.

Usage:
    scrape/venv/bin/python scrape/html_open_sources.py
"""

import shutil
import subprocess
import sys
import time
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).parent))
from utils import sanitize_filename, rate_limit  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
DOCUMENTS_DIR = REPO_ROOT / "documents" / "html"
CLONE_ROOT = Path("/tmp/docspec-html-clones")
MIN_HTML_BYTES = 200

SESSION = requests.Session()
SESSION.headers["User-Agent"] = (
    "DocSpec-Corpus-Scraper/1.0 (https://github.com/docspec/documents)"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def is_valid_html(content: bytes) -> bool:
    text = content[:512].decode("utf-8", errors="replace").lstrip()
    lower = text.lower()
    return lower.startswith("<!doctype") or lower.startswith("<html")


def git_sparse_clone(url: str, dest: Path, subdirs: list[str]) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if (dest / ".git").exists():
        print(f"  Already cloned: {dest}")
        return True
    print(f"  git clone {url} → {dest}")
    r = subprocess.run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--filter=blob:none",
            "--sparse",
            url,
            str(dest),
        ],
        capture_output=True,
        timeout=120,
        env={
            **__import__("os").environ,
            "GIT_TERMINAL_PROMPT": "0",
            "GCM_INTERACTIVE": "never",
        },
    )
    if r.returncode != 0:
        print(f"  Clone failed: {r.stderr.decode()[:200]}")
        return False
    r = subprocess.run(
        ["git", "sparse-checkout", "add", *subdirs],
        capture_output=True,
        timeout=120,
        cwd=dest,
        env={
            **__import__("os").environ,
            "GIT_TERMINAL_PROMPT": "0",
            "GCM_INTERACTIVE": "never",
        },
    )
    if r.returncode != 0:
        print(f"  Sparse-checkout failed: {r.stderr.decode()[:200]}")
        return False
    return True


def unique_dest(out_dir: Path, rel_path: str, seen: set[str]) -> Path:
    parts = [p for p in rel_path.replace("\\", "/").split("/") if p]
    base = (
        sanitize_filename("-".join(parts[-2:]))
        if len(parts) >= 2
        else sanitize_filename(parts[-1])
    )
    stem, _, ext = base.rpartition(".")
    ext = ext or "html"
    candidate = f"{stem}.{ext}"
    n = 0
    while candidate in seen:
        n += 1
        candidate = f"{stem}-{n}.{ext}"
    seen.add(candidate)
    return out_dir / candidate


def copy_html_files(
    src_dir: Path, rel_prefix: str, out_dir: Path, seen: set[str], limit: int
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    search_dir = src_dir / rel_prefix if rel_prefix else src_dir
    if not search_dir.exists():
        print(f"  Source dir not found: {search_dir}")
        return 0
    count = 0
    for src in sorted(search_dir.rglob("*.html")):
        if count >= limit:
            break
        content = src.read_bytes()
        if len(content) < MIN_HTML_BYTES or not is_valid_html(content):
            continue
        rel = str(src.relative_to(src_dir))
        dest = unique_dest(out_dir, rel, seen)
        shutil.copy2(src, dest)
        count += 1
    return count


# ---------------------------------------------------------------------------
# Source 1 — MDN Learning Area (CC-BY-SA-2.5)
# ---------------------------------------------------------------------------

MDN_HTML_SUBDIRS = [
    "html/introduction-to-html",
    "html/multimedia-and-embedding",
    "html/tables",
    "html/advanced-text-formatting",
    "html/forms",
    "html/css-and-js",
]


def scrape_mdn(target: int = 80) -> int:
    print("\n── MDN Learning Area (CC-BY-SA-2.5) ──────────────────────────────")
    clone_dir = CLONE_ROOT / "mdn-learning-area"
    if not git_sparse_clone(
        "https://github.com/mdn/learning-area.git",
        clone_dir,
        MDN_HTML_SUBDIRS,
    ):
        return 0

    out_dir = DOCUMENTS_DIR / "mdn-learning-area"
    out_dir.mkdir(parents=True, exist_ok=True)
    seen: set[str] = {p.name for p in out_dir.glob("*.html")}

    count = 0
    for subdir in MDN_HTML_SUBDIRS:
        if count >= target:
            break
        n = copy_html_files(clone_dir, subdir, out_dir, seen, limit=target - count)
        print(f"  {subdir}: {n} files")
        count += n

    print(f"  MDN total: {count}")
    return count


# ---------------------------------------------------------------------------
# Source 2 — W3C Web Platform Tests (W3C-20150513)
# ---------------------------------------------------------------------------

WPT_HTML_SUBDIRS = [
    "html/semantics/text-level-semantics",
    "html/semantics/grouping-content",
    "html/semantics/sections",
]


def scrape_wpt(target: int = 30) -> int:
    print("\n── W3C Web Platform Tests (W3C-20150513) ─────────────────────────")
    clone_dir = CLONE_ROOT / "wpt"
    if not git_sparse_clone(
        "https://github.com/web-platform-tests/wpt.git",
        clone_dir,
        WPT_HTML_SUBDIRS,
    ):
        return 0

    out_dir = DOCUMENTS_DIR / "wpt"
    out_dir.mkdir(parents=True, exist_ok=True)
    seen: set[str] = {p.name for p in out_dir.glob("*.html")}

    count = 0
    for subdir in WPT_HTML_SUBDIRS:
        if count >= target:
            break
        n = copy_html_files(clone_dir, subdir, out_dir, seen, limit=target - count)
        print(f"  {subdir}: {n} files")
        count += n

    print(f"  WPT total: {count}")
    return count


# ---------------------------------------------------------------------------
# Source 3 — HTML5 Boilerplate (MIT) — direct raw downloads
# ---------------------------------------------------------------------------

H5BP_URLS: list[tuple[str, str]] = [
    (
        "https://raw.githubusercontent.com/h5bp/html5-boilerplate/main/src/index.html",
        "h5bp-main-index.html",
    ),
    (
        "https://raw.githubusercontent.com/h5bp/html5-boilerplate/v7.3.0/dist/index.html",
        "h5bp-v7-index.html",
    ),
    (
        "https://raw.githubusercontent.com/h5bp/html5-boilerplate/v6.1.0/dist/index.html",
        "h5bp-v6-index.html",
    ),
]


def scrape_h5bp() -> int:
    print("\n── HTML5 Boilerplate (MIT) ────────────────────────────────────────")
    out_dir = DOCUMENTS_DIR / "html5-boilerplate"
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for raw_url, filename in H5BP_URLS:
        dest = out_dir / filename
        if dest.exists():
            count += 1
            continue
        print(f"  GET {filename}")
        try:
            rate_limit(2.0)
            resp = SESSION.get(raw_url, timeout=30)
            resp.raise_for_status()
            content = resp.content
            if len(content) >= MIN_HTML_BYTES and is_valid_html(content):
                dest.write_bytes(content)
                count += 1
            else:
                print(f"  Rejected: {filename}")
        except requests.RequestException as exc:
            print(f"  Error: {exc}")
    print(f"  H5BP total: {count}")
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def count_html() -> int:
    return len(list(DOCUMENTS_DIR.rglob("*.html")))


def main() -> None:
    print("=" * 65)
    print("  DocSpec HTML Corpus Scraper")
    print("=" * 65)
    CLONE_ROOT.mkdir(parents=True, exist_ok=True)

    scrape_mdn(target=80)
    scrape_wpt(target=30)
    scrape_h5bp()

    on_disk = count_html()
    print(f"\n{'=' * 65}")
    print(f"Total HTML files: {on_disk}")
    if on_disk < 100:
        print(f"⚠️  Only {on_disk} files — check network connectivity and retry")
        sys.exit(1)
    print(f"✅ {on_disk} ≥ 100 files")


if __name__ == "__main__":
    main()
