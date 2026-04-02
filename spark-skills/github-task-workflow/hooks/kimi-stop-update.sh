#!/bin/bash
# Kimi CLI Hook: Auto-update the active issue when the session ends.
# Install: reference this script in ~/.kimi/config.toml under [[hooks]] event = "Stop"

read JSON

# Check if stop hook is already active (prevents infinite loops)
IS_ACTIVE=$(echo "$JSON" | python3 -c "
import sys, json
print(json.load(sys.stdin).get('stop_hook_active', False))
")

if [ "$IS_ACTIVE" = "True" ]; then
    exit 0
fi

REPO_DIR=$(git rev-parse --show-toplevel 2>/dev/null)
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

# Find the most recently created issue number from a local marker file
ISSUE_FILE="$REPO_DIR/.github-task-workflow.active-issue"
if [ ! -f "$ISSUE_FILE" ]; then
    exit 0
fi

ISSUE=$(cat "$ISSUE_FILE")
rm -f "$ISSUE_FILE"

cd "$REPO_DIR" || exit 0

python3 "$SKILL_DIR/scripts/update_issue.py" \
  --issue "$ISSUE" \
  --comment "### Session Completed\n\nAssociated Kimi CLI session has ended." \
  > /dev/null 2>&1

exit 0
