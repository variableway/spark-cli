#!/usr/bin/env bash
# Verify that the installed binary matches the freshly built source.
# Used by both `make verify-install` and `task verify-install`.
set -e

SRC="${1:-spark}"
DST_DIR="${2:-${HOME}/.local/bin}"
DST="${DST_DIR}/$(basename "$SRC" .exe)"

sha256_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" 2>/dev/null | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'
    else
        echo "" >&2
        echo "Neither sha256sum nor shasum is available" >&2
        return 1
    fi
}

file_size() {
    stat -c '%s' "$1" 2>/dev/null || stat -f '%z' "$1"
}

echo ""
echo "Install verification:"

SRC_HASH=""
if [ -f "$SRC" ]; then
    SRC_BYTES=$(file_size "$SRC")
    SRC_HASH=$(sha256_file "$SRC")
    echo "  src: $SRC  ($SRC_BYTES bytes, sha256 $SRC_HASH)"
else
    echo "  src: $SRC  (missing)"
fi

DST_HASHES=()
FOUND_DST=0
for candidate in "$DST" "${DST}.exe"; do
    if [ -f "$candidate" ]; then
        FOUND_DST=1
        DST_BYTES=$(file_size "$candidate")
        CANDIDATE_HASH=$(sha256_file "$candidate")
        echo "  dst: $candidate  ($DST_BYTES bytes, sha256 $CANDIDATE_HASH)"
        DST_HASHES+=("$CANDIDATE_HASH")
    fi
done

if [ "$FOUND_DST" -eq 0 ]; then
    echo "  dst: $DST  (missing)"
fi

if [ -z "$SRC_HASH" ]; then
    echo "  HASH MISMATCH: source not built" >&2
    exit 1
fi

for h in "${DST_HASHES[@]+"${DST_HASHES[@]}"}"; do
    if [ "$h" = "$SRC_HASH" ]; then
        echo "  sha256 matches"
        exit 0
    fi
done

JOINED=$(IFS=,; echo "${DST_HASHES[*]}")
echo "  HASH MISMATCH src=$SRC_HASH dst=$JOINED" >&2
exit 1
