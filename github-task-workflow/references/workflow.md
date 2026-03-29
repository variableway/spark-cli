# GitHub Task Workflow Reference

## Workflow Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Read Task  │────▶│Create Issue │────▶│  Implement  │────▶│Update Issue │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

## Phase 1: Read Task

Task sources:
- Markdown file (e.g., `tasks/feature-123.md`)
- User description in conversation
- Task management system export

Extract from task:
- **Title**: Concise summary
- **Description**: Detailed requirements
- **Acceptance Criteria**: Checklist of completion criteria
- **Priority**: Optional label (high/medium/low)

## Phase 2: Create GitHub Issue

Use `scripts/create_issue.py`:

```bash
python scripts/create_issue.py \
  --repo "owner/repo" \
  --title "Task Title" \
  --body "Task description..." \
  --labels "enhancement,task"
```

Store the issue number for later updates.

## Phase 3: Implementation

Work on the task:
- Create feature branch
- Implement changes
- Write tests
- Update documentation

Track notable implementation details:
- Files changed
- Key design decisions
- Dependencies added
- Breaking changes
- Testing approach

## Phase 4: Update Issue with Implementation

Options for updating:

### Option A: Add Comment (Recommended)

```bash
python scripts/update_issue.py \
  --repo "owner/repo" \
  --issue 123 \
  --comment "## Implementation Summary\n\n- Changed: ...\n- PR: #456"
```

### Option B: Append to Body

```bash
python scripts/update_issue.py \
  --repo "owner/repo" \
  --issue 123 \
  --append \
  --body "## Completed\n\nImplementation details..."
```

### Option C: Close with Comment

```bash
python scripts/update_issue.py \
  --repo "owner/repo" \
  --issue 123 \
  --state closed \
  --comment "Completed in PR #456"
```

## Implementation Summary Template

```markdown
## Implementation Summary

### Changes Made
- File A: Description of changes
- File B: Description of changes

### Design Decisions
- Decision 1: Rationale
- Decision 2: Rationale

### Testing
- Test approach
- Coverage notes

### Pull Request
- Link: #PR_NUMBER

### Notes
Any additional notes or follow-up tasks
```

## Authentication

Scripts require `GITHUB_TOKEN` environment variable:

```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
```

Token needs permissions:
- `repo` - Full repository access
- Or `public_repo` - Public repositories only
