---
name: github-task-workflow
description: Manage tasks through GitHub issues - create issues from tasks, track implementation, and submit completion details. Use when the user wants to (1) Create a GitHub issue from a task description, (2) Track task implementation via GitHub issues, (3) Submit implementation details to an existing GitHub issue, or (4) Close tasks with implementation summaries.
---

# GitHub Task Workflow

Track tasks from creation to completion using GitHub issues.

## Quick Start

### Create Issue from Task (Auto-detect repo)

```bash
# Run from within a git repository - repo auto-detected from git remote
python scripts/create_issue.py \
  --title "Implement feature X" \
  --body "$(cat task.md)" \
  --labels "enhancement"
```

### Update Issue After Completion (Auto-detect repo)

```bash
# Run from within the same git repository
python scripts/update_issue.py \
  --issue 123 \
  --comment "## Completed\n\n- Changed: src/feature.py\n- PR: #456" \
  --state closed
```

## Workflow

1. **Read task** - Parse task from file or user input
2. **Create issue** - Use `create_issue.py` to create GitHub issue (repo auto-detected)
3. **Implement** - Work on the task, track changes
4. **Submit details** - Use `update_issue.py` to add implementation summary (repo auto-detected)

## Repository Detection

Scripts automatically detect the repository from git configuration:

```bash
# Auto-detect from git remote (default: origin)
python scripts/create_issue.py --title "Task" --body "Description"

# Use different remote
python scripts/create_issue.py --remote upstream --title "Task" --body "Description"

# Override with explicit repo
python scripts/create_issue.py --repo "owner/other-repo" --title "Task" --body "Description"
```

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/create_issue.py` | Create GitHub issue from task |
| `scripts/update_issue.py` | Update issue with implementation details |

## Configuration

GitHub token can be provided via (in priority order):

1. **Command-line**: `--token ghp_xxx`
2. **Environment variable**: `export GITHUB_TOKEN="ghp_xxx"`
3. **Project config**: `.github-task-workflow.yaml` in project root
4. **Global config**: `~/.config/github-task-workflow/config.yaml`

### Setup Config Files

```bash
# Initialize global config
python scripts/config_loader.py --init-global

# Initialize project config (in current directory)
python scripts/config_loader.py --init-project

# Check current config sources
python scripts/config_loader.py --show-sources
```

### Example Config File

```yaml
# .github-task-workflow.yaml or ~/.config/github-task-workflow/config.yaml
github:
  token: ghp_your_token_here
  # repo: owner/repo  # Optional: override auto-detection
```

## Detailed Guide

See [references/workflow.md](references/workflow.md) for:
- Full workflow patterns
- Implementation summary templates
- Authentication details
- Update options (comment vs append vs close)
