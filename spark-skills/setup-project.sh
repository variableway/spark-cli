#!/usr/bin/env bash
# One-click setup of github-task-workflow for the current git project.
# Usage: bash /path/to/spark-skills/setup-project.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_NAME="github-task-workflow"
SKILL_DIR="$SCRIPT_DIR/$SKILL_NAME"

if [ ! -d "$SKILL_DIR" ]; then
    echo "Error: Could not find skill directory at $SKILL_DIR"
    exit 1
fi

if [ ! -d ".git" ]; then
    echo "Error: Current directory is not a git repository."
    exit 1
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

echo "========================================="
echo "Setting up $SKILL_NAME for $(basename "$REPO_ROOT")"
echo "========================================="

# 1. Install Git hooks
echo ""
echo "[1/5] Installing Git hooks..."
cp "$SKILL_DIR/hooks/post-commit" .git/hooks/post-commit
cp "$SKILL_DIR/hooks/prepare-commit-msg" .git/hooks/prepare-commit-msg
chmod +x .git/hooks/post-commit .git/hooks/prepare-commit-msg
echo "  - post-commit"
echo "  - prepare-commit-msg"

# 2. Create project config if missing
echo ""
echo "[2/5] Creating project config..."
if [ ! -f ".github-task-workflow.yaml" ]; then
    cat > .github-task-workflow.yaml <<'EOF'
# GitHub Task Workflow - Project Configuration

github:
  # GitHub token (or use GITHUB_TOKEN env var)
  # token: ghp_xxxxxxxxxxxx

  # Repository for this project (auto-detected from git if not set)
  # repo: owner/repo
EOF
    echo "  Created: .github-task-workflow.yaml"
else
    echo "  Already exists: .github-task-workflow.yaml"
fi

# 3. Create tasks directory and example
echo ""
echo "[3/5] Creating tasks directory..."
mkdir -p tasks
if [ ! -f "tasks/example-feature.md" ]; then
    cat > "tasks/example-feature.md" <<'EOF'
# 示例功能

## 描述
简述本次任务的目标。

## 验收标准
- [ ] 标准 1
- [ ] 标准 2
EOF
    echo "  Created: tasks/"
    echo "  Created: tasks/example-feature.md"
else
    echo "  Already exists: tasks/"
fi

# 4. Create GitHub Actions workflow
echo ""
echo "[4/5] Creating GitHub Actions workflow..."
mkdir -p .github/workflows
if [ ! -f ".github/workflows/close-issue-on-merge.yml" ]; then
    cat > ".github/workflows/close-issue-on-merge.yml" <<'EOF'
name: Close Linked Issue

on:
  pull_request:
    types: [closed]

jobs:
  close-issue:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - name: Extract issue number from branch
        id: extract
        run: |
          ISSUE=$(echo "${{ github.head_ref }}" | grep -oE '^[0-9]+' | head -n 1)
          echo "issue=$ISSUE" >> $GITHUB_OUTPUT

      - name: Close issue via API
        if: steps.extract.outputs.issue != ''
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ISSUE: ${{ steps.extract.outputs.issue }}
          REPO: ${{ github.repository }}
        run: |
          curl -X PATCH \
            -H "Authorization: Bearer $GH_TOKEN" \
            -H "Accept: application/vnd.github+json" \
            "https://api.github.com/repos/$REPO/issues/$ISSUE" \
            -d '{"state":"closed","body":"Closed by PR #${{ github.event.number }}"}'
EOF
    echo "  Created: .github/workflows/close-issue-on-merge.yml"
else
    echo "  Already exists: .github/workflows/close-issue-on-merge.yml"
fi

# 5. Install skill to agents
echo ""
echo "[5/5] Installing skill to agent directories..."

install_to_agent() {
    local target_dir="$1"
    local link_path="$target_dir/$SKILL_NAME"
    mkdir -p "$target_dir"
    if [ -e "$link_path" ] || [ -L "$link_path" ]; then
        echo "  [SKIP] $target_dir"
    else
        ln -s "$SKILL_DIR" "$link_path"
        echo "  [OK]   $target_dir"
    fi
}

install_to_agent "$HOME/.claude/skills"
install_to_agent "$HOME/.kimi/skills"
install_to_agent "$HOME/.config/agents/skills"

echo ""
echo "========================================="
echo "Setup complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Edit .github-task-workflow.yaml to add your GitHub token"
echo "  2. Write task files in tasks/"
echo "  3. Use one of the following to execute tasks:"
echo ""
echo "     Kimi CLI Flow mode:"
echo "       /flow:$SKILL_NAME tasks/my-task.md"
echo ""
echo "     Kimi CLI custom agent:"
echo "       kimi --agent-file $SKILL_DIR/agent/kimi-agent.yaml"
echo ""
echo "     Cross-agent orchestrator:"
echo "       python $SKILL_DIR/scripts/orchestrate.py init tasks/my-task.md"
echo "       # ... AI implements ..."
echo "       python $SKILL_DIR/scripts/orchestrate.py finish"
echo ""
