#!/bin/bash
# Kimi CLI Hook: Auto-create GitHub issue when a task file is written.
# Install: reference this script in ~/.kimi/config.toml under [[hooks]] event = "PostToolUse"

read JSON

# Extract file path from the JSON context
FILE=$(echo "$JSON" | python3 -c "
import sys, json
data = json.load(sys.stdin)
inp = data.get('tool_input', {})
path = inp.get('file_path') or inp.get('path') or ''
print(path)
")

# Only trigger for .md files in tasks/ directory
if [[ ! "$FILE" =~ /tasks/ ]] && [[ ! "$FILE" =~ ^tasks/ ]]; then
    exit 0
fi
if [[ ! "$FILE" =~ \.md$ ]]; then
    exit 0
fi

# Must be in a git repo
REPO_DIR=$(git -C "$(dirname "$FILE")" rev-parse --show-toplevel 2>/dev/null)
if [ -z "$REPO_DIR" ]; then
    exit 0
fi

# Resolve skill directory
SKILL_DIR="$REPO_DIR/.kimi/skills/github-task-workflow"
if [ ! -d "$SKILL_DIR" ]; then
    SKILL_DIR="$HOME/.kimi/skills/github-task-workflow"
fi
if [ ! -d "$SKILL_DIR" ]; then
    SKILL_DIR="$HOME/.claude/skills/github-task-workflow"
fi
if [ ! -d "$SKILL_DIR" ]; then
    SKILL_DIR="$HOME/.config/agents/skills/github-task-workflow"
fi
if [ ! -d "$SKILL_DIR" ]; then
    exit 0
fi

# Read title from first line, fallback to filename
TITLE=$(head -n 1 "$FILE" | sed 's/^# //')
if [ -z "$TITLE" ]; then
    TITLE=$(basename "$FILE" .md)
fi

BODY=$(cat "$FILE")

cd "$REPO_DIR" || exit 0

# Create issue silently
python3 "$SKILL_DIR/scripts/create_issue.py" \
  --title "$TITLE" \
  --body "$BODY" \
  --labels "task" \
  > /dev/null 2>&1

exit 0
