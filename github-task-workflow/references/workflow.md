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
# Auto-detect repo from git remote
python scripts/create_issue.py \
  --title "Task Title" \
  --body "Task description..." \
  --labels "enhancement,task"

# Or specify repo explicitly
python scripts/create_issue.py \
  --repo "owner/repo" \
  --title "Task Title" \
  --body "Task description..."

# Use different git remote
python scripts/create_issue.py \
  --remote upstream \
  --title "Task Title" \
  --body "Task description..."
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

Options for updating (repo auto-detected from git by default):

### Option A: Add Comment (Recommended)

```bash
python scripts/update_issue.py \
  --issue 123 \
  --comment "## Implementation Summary\n\n- Changed: ...\n- PR: #456"
```

### Option B: Append to Body

```bash
python scripts/update_issue.py \
  --issue 123 \
  --append \
  --body "## Completed\n\nImplementation details..."
```

### Option C: Close with Comment

```bash
python scripts/update_issue.py \
  --issue 123 \
  --state closed \
  --comment "Completed in PR #456"
```

### Override Auto-detection

```bash
# Specify different repo
python scripts/update_issue.py \
  --repo "owner/other-repo" \
  --issue 123 \
  --comment "Done"

# Use different remote
python scripts/update_issue.py \
  --remote upstream \
  --issue 123 \
  --comment "Done"
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

Scripts require a GitHub personal access token. Configure via (priority order):

### 1. Command-line Argument (Highest Priority)

```bash
python scripts/create_issue.py --token "ghp_xxx" --title "Task" --body "Desc"
```

### 2. Environment Variable

```bash
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
```

### 3. Project Config File

Create `.github-task-workflow.yaml` in project root:

```yaml
github:
  token: ghp_xxxxxxxxxxxx
```

### 4. Global Config File (Lowest Priority)

```bash
# Initialize
python scripts/config_loader.py --init-global

# Then edit: ~/.config/github-task-workflow/config.yaml
github:
  token: ghp_xxxxxxxxxxxx
```

### Token Permissions

Required scopes:
- `repo` - Full repository access (for private repos)
- `public_repo` - Public repositories only

Generate token at: https://github.com/settings/tokens
