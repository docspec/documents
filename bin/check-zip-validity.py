#!/usr/bin/env python3
"""Check if ODT/EPUB/DOCX files are valid ZIP archives.

SPDX-License-Identifier: MIT
"""

import sys
import zipfile
from pathlib import Path

EXTENSIONS = {".odt", ".docx", ".epub"}


def main() -> int:
    root = Path("documents")
    if not root.is_dir():
        print("Error: documents/ directory not found", file=sys.stderr)
        return 1

    files = sorted(
        p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS
    )

    print("Checking if ODT/EPUB/DOCX files are valid ZIP archives...")
    print()

    invalid = 0
    for path in files:
        try:
            with zipfile.ZipFile(path) as zf:
                bad = zf.testzip()
            if bad is not None:
                print(f"❌ Invalid (corrupt entry {bad}): {path}")
                invalid += 1
            else:
                print(f"✓ Valid: {path}")
        except (zipfile.BadZipFile, Exception) as exc:
            print(f"❌ Invalid ({exc}): {path}")
            invalid += 1

    print()
    print(f"Checked {len(files)} files")

    if invalid == 0:
        print("✅ All files are valid ZIP archives")
        return 0
    else:
        print(f"❌ Found {invalid} invalid ZIP file(s)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
