#!/usr/bin/env bash
# Install spark-skills to various AI agent skill directories.
# Usage: ./install.sh <agent-name>
# Supported agents: claude-code, kimi, codex, opencode

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT="${1:-}"

if [ -z "$AGENT" ]; then
    echo "Usage: $0 <agent-name>"
    echo "Supported agents: claude-code, kimi, codex, opencode"
    exit 1
fi

case "$AGENT" in
    claude-code)
        TARGET_DIR="$HOME/.claude/skills"
        ;;
    kimi)
        TARGET_DIR="$HOME/.kimi/skills"
        ;;
    codex)
        TARGET_DIR="$HOME/.codex/skills"
        ;;
    opencode)
        TARGET_DIR="$HOME/.opencode/skills"
        ;;
    *)
        echo "Error: unsupported agent '$AGENT'"
        echo "Supported agents: claude-code, kimi, codex, opencode"
        exit 1
        ;;
esac

echo "Installing spark-skills to $AGENT directory: $TARGET_DIR"
mkdir -p "$TARGET_DIR"

# Find all skill directories (directories containing SKILL.md)
SKILL_COUNT=0
for skill_dir in "$SCRIPT_DIR"/*/; do
    if [ ! -d "$skill_dir" ]; then
        continue
    fi

    skill_name="$(basename "$skill_dir")"
    target_link="$TARGET_DIR/$skill_name"

    if [ -e "$target_link" ] || [ -L "$target_link" ]; then
        echo "  [SKIP] $skill_name already exists at $target_link"
    else
        ln -s "$skill_dir" "$target_link"
        echo "  [OK]   $skill_name -> $target_link"
        ((SKILL_COUNT++)) || true
    fi
done

echo ""
echo "Installation complete. $SKILL_COUNT skill(s) linked."
