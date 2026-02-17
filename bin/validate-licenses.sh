#!/bin/bash
# Validate SPDX license identifiers in ATTRIBUTION.json
# SPDX-License-Identifier: MIT

set -euo pipefail

SPDX_FILE="/tmp/spdx-licenses.json"

if [ ! -f "$SPDX_FILE" ]; then
  echo "Downloading SPDX license list..."
  if ! curl -s 'https://raw.githubusercontent.com/spdx/license-list-data/main/json/licenses.json' >"$SPDX_FILE"; then
    echo "❌ Failed to download SPDX license list"
    exit 1
  fi
fi

if [ ! -f "ATTRIBUTION.json" ]; then
  echo "❌ ATTRIBUTION.json not found"
  exit 1
fi

LICENSES=$(jq -r '.[].license' ATTRIBUTION.json)

if [ -z "$LICENSES" ]; then
  echo "⚠️  No licenses found in ATTRIBUTION.json"
  exit 0
fi

VALID_LICENSES=$(jq -r '.licenses[].licenseId' "$SPDX_FILE")

INVALID=0
echo "Validating licenses against SPDX license list..."
echo ""

for LICENSE in $LICENSES; do
  if echo "$VALID_LICENSES" | grep -q "^${LICENSE}$"; then
    echo "✓ Valid: $LICENSE"
  else
    echo "❌ Invalid SPDX license identifier: $LICENSE"
    echo "   See https://spdx.org/licenses/ for valid identifiers"
    INVALID=1
  fi
done

echo ""
if [ $INVALID -eq 0 ]; then
  echo "✅ All licenses are valid SPDX identifiers"
else
  echo "❌ Some licenses are invalid"
fi

exit "$INVALID"
