#!/bin/bash
# Check for duplicate files in the documents directory
# SPDX-License-Identifier: MIT

set -euo pipefail

echo "Checking for duplicate files in documents/..."
echo ""

TMPFILE=$(mktemp)
trap 'rm -f "$TMPFILE"' EXIT

find documents/ -type f \( -name "*.odt" -o -name "*.docx" -o -name "*.pdf" -o -name "*.epub" -o -name "*.md" \) -exec sha256sum {} \; | sort >"$TMPFILE"

DUPLICATES=$(awk '{print $1}' "$TMPFILE" | uniq -d)

if [ -z "$DUPLICATES" ]; then
  echo "✅ No duplicate files found"
  exit 0
fi

echo "❌ Duplicate files detected:"
echo ""

FOUND_DUPLICATES=0
for CHECKSUM in $DUPLICATES; do
  echo "Checksum: $CHECKSUM"
  grep "^$CHECKSUM" "$TMPFILE" | awk '{print "  - " $2}'
  echo ""
  FOUND_DUPLICATES=1
done

if [ $FOUND_DUPLICATES -eq 1 ]; then
  echo "❌ Found duplicate files. Please remove duplicates before committing."
  exit 1
fi
