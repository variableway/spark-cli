# Spark CLI Project Analysis

## Overview

Spark CLI is a Go-based command-line tool that positions itself as a CLI backend for everyday dev automation.

**Core idea:** deterministic tasks are executed via the CLI to save LLM token cost.

## Tech Stack

| Layer | Choice |
|-------|--------|
| Language | Go 1.27 (see `go.mod`) |
| CLI framework | Cobra |
| Config | Viper |
| Terminal UI | PTerm + Bubble Tea |
| Testing | Ginkgo / Gomega (`internal/`) + standard `testing` (`cmd/`) |
| Build | Makefile + Taskfile |
| Docs | docmd (bilingual zh/en) |

## Modules

| Module | Command | Capability |
|--------|---------|------------|
| Git management | `spark git` | Multi-repo update, clone, repo init, submodule management, Gitcode remote, batch clone (GitHub/GitLab), issues, scan, push |
| Repo management | `spark repo` | Registry-file driven scan / clone / list, an alternative to submodules |
| System utilities | `spark magic` | DNS flush, pip/go/node mirror switching, directory cleanup, dotfiles deploy |
| Script management | `spark script` | Custom script discovery and execution |
| Docs management | `spark docs` | Docs structure init, docmd site config |
| Process diagnostics | `spark witr` | Why-Is-This-Running process inspection |

## Architecture

```
main.go → cmd.Execute()
│
├── cmd/                    # Cobra command definitions
│   ├── git/                # Git commands
│   ├── repo/               # Registry-based repo management
│   ├── magic/              # System utilities
│   ├── script/             # Script management
│   ├── docs/               # Docs management
│   ├── version.go          # Version info
│   └── witr.go             # Process diagnostics bridge
│
└── internal/               # Business logic
    ├── config/             # Config loading & migration
    ├── git/                # Core Git operations (+ scanner/)
    ├── github/             # GitHub API interactions
    ├── gitlab/             # GitLab API interactions (batch clone)
    ├── registry/           # Registry file scan/read/merge
    ├── script/             # Script discovery & execution
    ├── templates/          # Embedded nvim/ghostty dotfiles
    └── witr/               # Process diagnostics engine
```

**Design notes**:
- `cmd/` is responsible for arg parsing and calling `internal/` logic.
- The `internal/` packages are loosely coupled; each has a single responsibility.

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
- `internal/witr/` coverage is still concentrated in the `output` subpackage.
- `cmd/` lacks integration tests (pure functions are covered with standard `testing`).
- Existing test quality is good (Ginkgo BDD style), but the surface needs to expand.

### 2. Heavy reliance on external commands
Lots of `exec.Command` calls into `git`, `gh`, `glab`, `npm`, with no abstraction layer. Consequences:
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
- Limited env-var override support (keys such as `gitlab.token` contain a `.`, so `viper.AutomaticEnv` cannot map them and `os.Getenv` is needed instead).

## Recommendations

| Priority | Improvement | Expected benefit |
|----------|-------------|------------------|
| High | Add tests across the `internal/` packages | Higher code reliability |
| High | Extract an external-command abstraction | Testability + maintainability |
| Medium | Unify the mirror-switch pattern in `magic` | Removes ~60% of duplicated code |
| Medium | Add config validation | Fewer user config errors |
| Low | Add integration tests | End-to-end verification |
| Low | Add a contribution guide | Lower contribution barrier |

## Summary

Spark CLI is a practical dev tool with clean architecture and reasonable feature coverage. Its core strength is unifying many day-to-day dev operations (Git management, mirror switching) into one CLI, while the profile system and TUI mode deliver a good user experience. The main improvement areas are expanding test coverage, reducing code duplication, and unifying the external-command invocation pattern.
