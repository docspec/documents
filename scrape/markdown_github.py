#!/usr/bin/env python3
"""
Markdown corpus scraper for DocSpec test documents.

Sources:
  - CommonMark spec sections (CC-BY-SA-4.0)
      https://github.com/commonmark/commonmark-spec
  - The Rust Programming Language book chapters (CC-BY-4.0)
      https://github.com/rust-lang/book
  - Docusaurus website docs (MIT)
      https://github.com/facebook/docusaurus

Run from repo root:
  scrape/venv/bin/python scrape/markdown_github.py
"""

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scrape.utils import sanitize_filename, download_file, check_file_size, rate_limit

import requests

DEST = Path("documents/markdown")
RAW = "https://raw.githubusercontent.com"
SESSION = requests.Session()
SESSION.headers["User-Agent"] = (
    "DocSpec-Corpus-Scraper/1.0 (https://github.com/docspec/documents)"
)

RUST_BOOK_FILES = [
    "title-page.md",
    "foreword.md",
    "ch00-00-introduction.md",
    "ch01-00-getting-started.md",
    "ch01-01-installation.md",
    "ch01-02-hello-world.md",
    "ch01-03-hello-cargo.md",
    "ch02-00-guessing-game-tutorial.md",
    "ch03-00-common-programming-concepts.md",
    "ch03-01-variables-and-mutability.md",
    "ch03-02-data-types.md",
    "ch03-03-how-functions-work.md",
    "ch03-04-comments.md",
    "ch03-05-control-flow.md",
    "ch04-00-understanding-ownership.md",
    "ch04-01-what-is-ownership.md",
    "ch04-02-references-and-borrowing.md",
    "ch04-03-slices.md",
    "ch05-00-structs.md",
    "ch05-01-defining-structs.md",
    "ch05-02-example-structs.md",
    "ch05-03-method-syntax.md",
    "ch06-00-enums.md",
    "ch06-01-defining-an-enum.md",
    "ch06-02-match.md",
    "ch06-03-if-let.md",
    "ch07-00-managing-growing-projects-with-packages-crates-and-modules.md",
    "ch07-01-packages-and-crates.md",
    "ch07-02-defining-modules-to-control-scope-and-privacy.md",
    "ch07-03-paths-for-referring-to-an-item-in-the-module-tree.md",
    "ch07-04-bringing-paths-into-scope-with-the-use-keyword.md",
    "ch07-05-separating-modules-into-different-files.md",
    "ch08-00-common-collections.md",
    "ch08-01-vectors.md",
    "ch08-02-strings.md",
    "ch08-03-hash-maps.md",
    "ch09-00-error-handling.md",
    "ch09-01-unrecoverable-errors-with-panic.md",
    "ch09-02-recoverable-errors-with-result.md",
    "ch09-03-to-panic-or-not-to-panic.md",
    "ch10-00-generics.md",
    "ch10-01-syntax.md",
    "ch10-02-traits.md",
    "ch10-03-lifetime-syntax.md",
    "ch11-00-testing.md",
    "ch11-01-writing-tests.md",
    "ch11-02-running-tests.md",
    "ch11-03-test-organization.md",
    "ch12-00-an-io-project.md",
    "ch12-01-accepting-command-line-arguments.md",
    "ch12-02-reading-a-file.md",
    "ch12-03-improving-error-handling-and-modularity.md",
    "ch12-04-testing-the-librarys-functionality.md",
    "ch12-05-working-with-environment-variables.md",
    "ch12-06-writing-to-stderr-instead-of-stdout.md",
    "ch13-00-functional-features.md",
    "ch13-01-closures.md",
    "ch13-02-iterators.md",
    "ch13-03-improving-our-io-project.md",
    "ch13-04-performance.md",
    "ch14-00-more-about-cargo.md",
    "ch14-01-release-profiles.md",
    "ch14-02-publishing-to-crates-io.md",
    "ch14-03-cargo-workspaces.md",
    "ch14-04-installing-binaries.md",
    "ch14-05-extending-cargo.md",
    "ch15-00-smart-pointers.md",
    "ch15-01-box.md",
    "ch15-02-deref.md",
    "ch15-03-drop.md",
    "ch15-04-rc.md",
    "ch15-05-interior-mutability.md",
    "ch15-06-reference-cycles.md",
    "ch16-00-concurrency.md",
    "ch16-01-threads.md",
    "ch16-02-message-passing.md",
    "ch16-03-shared-state.md",
    "ch16-04-extensible-concurrency-sync-and-send.md",
    "ch17-00-async-await.md",
    "ch17-01-futures-and-syntax.md",
    "ch17-02-concurrency-with-async.md",
    "ch17-03-more-futures.md",
    "ch17-04-streams.md",
    "ch17-05-traits-for-async.md",
    "ch17-06-futures-tasks-threads.md",
    "ch18-00-oop.md",
    "ch18-01-what-is-oo.md",
    "ch18-02-trait-objects.md",
    "ch18-03-oo-design-patterns.md",
    "ch19-00-patterns.md",
    "ch19-01-all-the-places-for-patterns.md",
    "ch19-02-refutability.md",
    "ch19-03-pattern-syntax.md",
    "ch20-00-advanced-features.md",
    "ch20-01-unsafe-rust.md",
    "ch20-02-advanced-traits.md",
    "ch20-03-advanced-types.md",
    "ch20-04-advanced-functions-and-closures.md",
    "ch20-05-macros.md",
    "ch21-00-final-project-a-web-server.md",
    "ch21-01-single-threaded.md",
    "ch21-02-multithreaded.md",
    "ch21-03-graceful-shutdown-and-cleanup.md",
    "appendix-00.md",
    "appendix-01-keywords.md",
    "appendix-02-operators.md",
    "appendix-03-derivable-traits.md",
    "appendix-04-useful-development-tools.md",
    "appendix-05-editions.md",
    "appendix-06-translation.md",
    "appendix-07-nightly-rust.md",
]

DOCUSAURUS_DOCS = [
    "installation.mdx",
    "configuration.mdx",
    "deployment.mdx",
    "guides/creating-pages.mdx",
    "guides/markdown-features/markdown-features-intro.mdx",
    "guides/markdown-features/markdown-features-react.mdx",
    "guides/markdown-features/markdown-features-tabs.mdx",
    "guides/markdown-features/markdown-features-code-blocks.mdx",
    "guides/markdown-features/markdown-features-admonitions.mdx",
    "guides/markdown-features/markdown-features-headings.mdx",
    "guides/markdown-features/markdown-features-assets.mdx",
    "guides/markdown-features/markdown-features-links.mdx",
    "guides/blog.mdx",
    "guides/docs/docs-introduction.mdx",
    "guides/docs/docs-create-doc.mdx",
    "guides/docs/docs-markdown-features.mdx",
]


def fetch_commonmark_spec() -> int:
    """Extract ## sections from the CommonMark spec as individual .md files.

    License: CC-BY-SA-4.0
    """
    dest_dir = DEST / "commonmark"
    dest_dir.mkdir(parents=True, exist_ok=True)

    existing = list(dest_dir.glob("*.md"))
    if existing:
        print(f"[commonmark] Using {len(existing)} cached sections")
        return len(existing)

    url = f"{RAW}/commonmark/commonmark-spec/master/spec.txt"
    print(f"[commonmark] Downloading spec from {url}")

    rate_limit(2.0)
    resp = SESSION.get(url, timeout=60)
    resp.raise_for_status()
    spec_text = resp.text

    # re.split with a capturing group keeps delimiters in the list:
    #   [preamble, heading1, body1, heading2, body2, ...]
    parts = re.split(r"^(## .+)$", spec_text, flags=re.MULTILINE)

    count = 0
    for i in range(1, len(parts) - 1, 2):
        heading = parts[i].strip()
        body = parts[i + 1] if (i + 1) < len(parts) else ""
        section_text = heading + "\n" + body

        if len(section_text.encode("utf-8")) < 100:
            continue

        title = heading.lstrip("#").strip()
        filename = sanitize_filename(title + ".md")
        filepath = dest_dir / filename

        filepath.write_text(section_text, encoding="utf-8")
        if check_file_size(filepath):
            count += 1
        else:
            filepath.unlink(missing_ok=True)

    print(f"[commonmark] Extracted {count} sections")
    return count


def fetch_rust_book() -> int:
    """Download chapter .md files from The Rust Programming Language book.

    License: CC-BY-4.0
    """
    dest_dir = DEST / "rust-book"
    dest_dir.mkdir(parents=True, exist_ok=True)

    base = f"{RAW}/rust-lang/book/main/src"
    count = 0
    for name in RUST_BOOK_FILES:
        filename = sanitize_filename(name)
        filepath = dest_dir / filename

        if filepath.exists() and check_file_size(filepath):
            count += 1
            continue

        url = f"{base}/{name}"
        print(f"[rust-book] Downloading {name}")
        if download_file(url, filepath, delay=1.0, max_retries=2, session=SESSION):
            if check_file_size(filepath):
                count += 1
            else:
                print(f"[rust-book] Removing {filename} (< 100 bytes)")
                filepath.unlink(missing_ok=True)
        else:
            filepath.unlink(missing_ok=True)

    print(f"[rust-book] Got {count} files")
    return count


def fetch_docusaurus_docs() -> int:
    """Download .mdx doc files from Docusaurus website/docs/, saved as .md.

    License: MIT
    """
    dest_dir = DEST / "docusaurus"
    dest_dir.mkdir(parents=True, exist_ok=True)

    base = f"{RAW}/facebook/docusaurus/main/website/docs"
    count = 0
    for path in DOCUSAURUS_DOCS:
        name = Path(path).name.replace(".mdx", ".md")
        filename = sanitize_filename(name)
        filepath = dest_dir / filename

        if filepath.exists() and check_file_size(filepath):
            count += 1
            continue

        url = f"{base}/{path}"
        print(f"[docusaurus] Downloading {path}")
        if download_file(url, filepath, delay=1.0, max_retries=2, session=SESSION):
            if check_file_size(filepath):
                count += 1
            else:
                print(f"[docusaurus] Removing {filename} (< 100 bytes)")
                filepath.unlink(missing_ok=True)
        else:
            filepath.unlink(missing_ok=True)

    print(f"[docusaurus] Got {count} files")
    return count


def main() -> int:
    print("=== Markdown Corpus Scraper ===\n")
    DEST.mkdir(parents=True, exist_ok=True)

    totals: dict[str, int] = {}
    totals["commonmark"] = fetch_commonmark_spec()
    totals["rust-book"] = fetch_rust_book()
    totals["docusaurus"] = fetch_docusaurus_docs()

    total = sum(totals.values())
    print("\n=== Summary ===")
    for source, n in totals.items():
        print(f"  {source}: {n}")
    print(f"  TOTAL: {total}")

    all_md = list(DEST.rglob("*.md"))
    print(f"\nFiles on disk in {DEST}/: {len(all_md)}")

    if len(all_md) < 100:
        print(f"\nWARNING: only {len(all_md)} files \u2014 need \u2265 100")
        return 1

    print("\n\u2705 Corpus target met")
    return 0


if __name__ == "__main__":
    sys.exit(main())
