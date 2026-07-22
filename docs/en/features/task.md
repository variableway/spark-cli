# Task Management

## Overview

`spark task` covers the full task lifecycle: create, implement, dispatch, sync. It can drive an AI agent (the `kimi` CLI) to auto-implement issues, and dispatches tasks into dedicated working directories for development.

## Core Capabilities

### Task Initialization

Create the standard task directory structure (`tasks/issues/`) inside a project.

```bash
spark task init
```

### Issue File Management

Create, list, and delete issue descriptor files. Issue files are Markdown-format task descriptions.

```bash
spark task create my-feature                     # Create an issue
spark task create my-feature --content "description"    # With content
spark task list                                  # List
spark task delete my-feature                     # Delete
```

### AI Implementation

Automatically implement the task described in an issue via the `kimi` CLI.

```bash
spark task impl my-feature
spark task impl my-feature --tui    # Interactive mode
```

### Task Dispatch and Sync

Dispatch a task to a dedicated working directory; sync the implementation back when development is complete.

```bash
# Dispatch to a working directory (auto-init Git, create GitHub repo)
spark task dispatch my-feature

# Sync back to the task directory once development is done
spark task sync my-feature
```

## Workflow

```
create → impl → dispatch → (develop) → sync
  ↑                                      ↓
  └────── tasks/issues/*.md ←───────────┘
```

## Parameters

| Parameter | Description |
|-----------|-------------|
| `--task-dir` | Task directory path |
| `--owner` | GitHub owner |
| `--work-dir` | Working directory, default `.` |
| `--dest` | Dispatch destination path |
| `--work-path` | Sync working path |
| `--tui` | Interactive TUI mode |
| `--force` | Skip confirmation (delete) |
| `--content` | Custom content (create) |

## Dependencies

- `git` and the `gh` CLI (dispatch needs the GitHub API)
- The `kimi` CLI (required for `impl`)

## Related

- [Task Command Spec](/en/spec/task)
- [Task Usage Guide](/en/usage/task)
