# Spark CLI Project Analysis

## Overview

Spark CLI is a Go-based command-line tool that positions itself as a CLI backend for everyday dev automation.

**Core idea:** deterministic tasks are executed via the CLI to save LLM token cost.

## Tech Stack

| Layer | Choice |
|-------|--------|
| Language | Go 1.25 |
| CLI framework | Cobra |
| Config | Viper |
| Terminal UI | PTerm + Bubble Tea |
| Testing | Ginkgo / Gomega |
| Docs | docmd |

## Modules

| Module | Command | Capability |
|--------|---------|------------|
| Git management | `spark git` | Multi-repo update, repo init, submodule management, Gitcode remote, org clone |
| Task management | `spark task` | Task create, dispatch, sync, AI implement |
| System utilities | `spark magic` | DNS flush, pip/go/node mirror switching |
| Script management | `spark script` | Custom script discovery and execution |
| Docs management | `spark docs` | Docs structure init, docmd site config |

## Architecture

```
main.go → cmd.Execute()
│
├── cmd/                    # Cobra command definitions
│   ├── git/                # Git commands
│   ├── magic/              # System utilities
│   ├── script/             # Script management
│   ├── docs/               # Docs management
│   └── task.go             # Task commands
│
└── internal/               # Business logic
    ├── config/             # Config loading & migration
    ├── git/                # Core Git operations
    ├── github/             # GitHub API interactions
    ├── script/             # Script discovery & execution
    ├── task/               # Task workflow
    └── tui/                # Terminal UI components
```

**Design notes**:
- `cmd/` is responsible for arg parsing and calling `internal/` logic.
- The `internal/` packages are loosely coupled; each has a single responsibility.
- The `--tui` flag toggles between CLI and interactive mode.

## Strengths

### 1. Clean architectural layering
The split between `cmd/` and `internal/` is clear. The command layer only does arg parsing and UI; business logic lives in `internal/`.

### 2. Solid library choices
Cobra + Viper + PTerm are a proven stack for Go CLI development, reducing dev and maintenance cost.

### 3. Practical, workflow-driven
Every feature originates from a real daily need (multi-repo management, mirror switching, DNS flush) — not technology for its own sake.

### 4. Config migration
The legacy `.monolize.yaml` config is auto-migrated to `.spark.yaml`, which is respectful of existing users.

## Areas for Improvement

### 1. Test coverage is thin
- `internal/mono/` has no tests.
- `cmd/` lacks integration tests.
- Existing test quality is good (Ginkgo BDD style), but the surface needs to expand.

### 2. Heavy reliance on external commands
Lots of `exec.Command` calls into `git`, `gh`, `kimi`, `npm`, with no abstraction layer. Consequences:
- Hard to run in environments without these tools.
- Unit tests have to mock entire environments.
- Error messages are not always precise.

### 3. Inconsistent error handling
- Some functions return error chains (`fmt.Errorf("...: %w", err)`); others just return the error.
- No unified error type or user-friendly messages.
- Some code paths lack context.

### 4. Code duplication
- `cmd/magic/`'s `pip.go`, `go.go`, and `node.go` are highly similar (list/use/current) — extract a common template.
- File copy logic is duplicated.
- The `exec.Command` invocation pattern is repeated.

### 5. Missing config validation
- No validation of config values.
- No schema definition for the config file.
- Limited env-var override support.

## Recommendations

| Priority | Improvement | Expected benefit |
|----------|-------------|------------------|
| High | Add tests for `internal/mono/` | Higher code reliability |
| High | Extract an external-command abstraction | Testability + maintainability |
| Medium | Unify the mirror-switch pattern in `magic` | Removes ~60% of duplicated code |
| Medium | Add config validation | Fewer user config errors |
| Low | Add integration tests | End-to-end verification |
| Low | Add a contribution guide | Lower contribution barrier |

## Summary

Spark CLI is a practical dev tool with clean architecture and reasonable feature coverage. Its core strength is unifying many day-to-day dev operations (Git management, mirror switching) into one CLI, while the profile system and TUI mode deliver a good user experience. The main improvement areas are expanding test coverage, reducing code duplication, and unifying the external-command invocation pattern.
