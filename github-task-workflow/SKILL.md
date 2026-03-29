---
name: github-task-workflow
description: Manage tasks through GitHub issues - create issues from tasks, track implementation, and submit completion details. Use when the user wants to (1) Create a GitHub issue from a task description, (2) Track task implementation via GitHub issues, (3) Submit implementation details to an existing GitHub issue, or (4) Close tasks with implementation summaries.
---

# GitHub Task Workflow

Track tasks from creation to completion using GitHub issues.

## Quick Start

### Create Issue from Task

```bash
# From task file
python scripts/create_issue.py \
  --repo "owner/repo" \
  --title "Implement feature X" \
  --body "$(cat task.md)" \
  --labels "enhancement"
```

### Update Issue After Completion

```bash
# Add implementation summary as comment
python scripts/update_issue.py \
  --repo "owner/repo" \
  --issue 123 \
  --comment "## Completed\n\n- Changed: src/feature.py\n- PR: #456" \
  --state closed
```

## Workflow

1. **Read task** - Parse task from file or user input
2. **Create issue** - Use `create_issue.py` to create GitHub issue
3. **Implement** - Work on the task, track changes
4. **Submit details** - Use `update_issue.py` to add implementation summary

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/create_issue.py` | Create GitHub issue from task |
| `scripts/update_issue.py` | Update issue with implementation details |

## Environment

Set GitHub token:

```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
```

## Detailed Guide

See [references/workflow.md](references/workflow.md) for:
- Full workflow patterns
- Implementation summary templates
- Authentication details
- Update options (comment vs append vs close)
