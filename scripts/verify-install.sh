#!/usr/bin/env bash
# Verify that the installed binary matches the freshly built source.
# Used by both `make verify-install` and `task verify-install`.
set -e

SRC="${1:-spark}"
DST_DIR="${2:-${HOME}/.local/bin}"
DST="${DST_DIR}/$(basename "$SRC" .exe)"

echo ""
echo "Install verification:"

if [ -f "$SRC" ]; then
    SRC_BYTES=$(stat -c '%s' "$SRC" 2>/dev/null || stat -f '%z' "$SRC")
    SRC_HASH=$(sha256sum "$SRC" 2>/dev/null | awk '{print $1}')
    echo "  src: $SRC  ($SRC_BYTES bytes, sha256 $SRC_HASH)"
else
    echo "  src: $SRC  (missing)"
fi

if [ -f "$DST" ] || [ -f "${DST}.exe" ]; then
    for candidate in "$DST" "${DST}.exe"; do
        if [ -f "$candidate" ]; then
            DST_BYTES=$(stat -c '%s' "$candidate" 2>/dev/null || stat -f '%z' "$candidate")
            DST_HASH=$(sha256sum "$candidate" 2>/dev/null | awk '{print $1}')
            echo "  dst: $candidate  ($DST_BYTES bytes, sha256 $DST_HASH)"
        fi
    done
else
    echo "  dst: $DST  (missing)"
fi

DST_HASH=$(sha256sum "${DST}.exe" 2>/dev/null | awk '{print $1}')
SRC_HASH=$(sha256sum "$SRC" 2>/dev/null | awk '{print $1}')
if [ -n "$SRC_HASH" ] && [ "$SRC_HASH" = "$DST_HASH" ]; then
    echo "  sha256 matches"
else
    echo "  HASH MISMATCH src=$SRC_HASH dst=$DST_HASH" >&2
    exit 1
fi
