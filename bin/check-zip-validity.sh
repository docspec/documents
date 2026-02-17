#!/bin/bash
# Check if ODT/EPUB/DOCX files are valid ZIP archives
# SPDX-License-Identifier: MIT

set -euo pipefail

echo "Checking if ODT/EPUB/DOCX files are valid ZIP archives..."
echo ""

INVALID=0
TOTAL=0

# Find all ODT, EPUB, and DOCX files
while IFS= read -r -d '' FILE; do
  TOTAL=$((TOTAL + 1))

  if unzip -t "$FILE" >/dev/null 2>&1; then
    echo "✓ Valid: $FILE"
  else
    echo "❌ Invalid: $FILE"
    INVALID=$((INVALID + 1))
  fi
done < <(find documents/ -type f \( -name "*.odt" -o -name "*.docx" -o -name "*.epub" \) -print0)

echo ""
echo "Checked $TOTAL files"

if [ $INVALID -eq 0 ]; then
  echo "✅ All files are valid ZIP archives"
  exit 0
else
  echo "❌ Found $INVALID invalid ZIP file(s)"
  exit 1
fi
