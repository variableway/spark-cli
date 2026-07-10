#!/usr/bin/env bash
# Install the just-built spark binary into ~/.local/bin.
# On Windows we keep both `spark.exe` and the no-extension `spark` in sync,
# because bash matches the exact filename first when both exist in PATH.
set -e

SRC="${1:-spark}"
DST_DIR="${2:-${HOME}/.local/bin}"
DST="${DST_DIR}/$(basename "$SRC" .exe)"

if [ ! -f "$SRC" ]; then
    echo "Source binary not found: $SRC" >&2
    exit 1
fi

mkdir -p "$DST_DIR"

if [[ "$SRC" == *.exe ]]; then
    # Windows: replace shadow file then copy both names
    rm -f "$DST" 2>/dev/null || true
    cp "$SRC" "${DST}.exe"
    cp "$SRC" "$DST"
    echo "Installed $SRC -> ${DST}.exe and $DST"
else
    cp "$SRC" "$DST"
    echo "Installed $SRC -> $DST"
fi
