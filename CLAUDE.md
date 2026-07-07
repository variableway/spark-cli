# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Test Commands

```bash
make build          # Build for current OS + install to ~/.local/bin/spark
make build-linux    # Cross-compile for Linux amd64
make build-darwin   # Cross-compile for macOS amd64
make test           # Run all unit tests (go test ./... -v)
make test-bdd       # Run BDD-style tests with Ginkgo (internal/...)
make lint           # Static analysis (go vet ./...)
make clean          # Remove binary and build artifacts
```

Run a single test:
```bash
go test ./internal/git/... -v -run TestFunctionName
```

## Architecture

Spark is a Go CLI tool (`module spark`, binary `spark`) for managing multiple Git repositories, scripts, and task workflows. Built with **Cobra** (CLI), **Viper** (config), **PTerm** + **Bubble Tea** (TUI), tested with **Ginkgo/Gomega** (BDD).

### Code Structure

- **`main.go`** → calls `cmd.Execute()`
- **`cmd/`** — Cobra command definitions. `root.go` loads config from `~/.spark.yaml` and auto-migrates from legacy `~/.monolize.yaml`. Subdirectories group commands:
  - `cmd/git/` — Git repo management commands
  - `cmd/magic/` — System utility commands (DNS flush, mirror switching, clean, copy-config)
  - `cmd/script/` — Script management commands
  - `cmd/docs/` — Documentation scaffolding commands
  - `cmd/task.go` — Top-level task commands in the root `cmd/` package
  - `cmd/witr.go` — Process diagnostics bridge
- **`internal/`** — Business logic, separated by domain:
  - `config/` — Configuration loading and management
  - `git/` — Core Git operations (find repos, update, remote management, submodule, URL conversion, scanner)
  - `github/` — GitHub API interactions (list org repos, parse org URLs)
  - `gitlab/` — GitLab API interactions (batch-clone)
  - `script/` — Script discovery (from config and `scripts/` dir) and execution
  - `task/` — Task init/dispatch/sync, issue CRUD, and implementation via `kimi` CLI
  - `templates/` — Embedded dotfiles (nvim, ghostty) for `magic copy-config`
  - `tui/` — Shared terminal UI components (spinner, dialogs, selector)
  - `witr/` — Why-Is-This-Running process diagnostics engine
- **`docs/usage/`** — Usage documentation per command

### Command Hierarchy

```
spark
├── git [init|clone|update|submodule [add|init|status|ensure-ssh]|sync|gitcode|config|url|batch-clone|issues|update-org-status|push-all|scan]
├── task [list|init|dispatch|sync|create|delete|impl]
├── script [list|run]
├── magic [flush-dns|clean|copy-config|pip|go|node]
├── docs [init|site]
└── witr
```

### Key Patterns

- **TUI mode**: `task` and other commands accept `--tui` flag for interactive mode with Bubble Tea selectors and PTerm spinners. CLI mode is the default.
- **Config binding**: Flags are bound to Viper via `viper.BindPFlag()` in `init()` functions. Config keys use snake_case in YAML but camelCase in struct tags.
- **Script sources**: Scripts can come from `~/.spark.yaml` (`spark.scripts` or top-level `scripts`) or from a `scripts/` directory. Config scripts take precedence.

### Config

User config at `~/.spark.yaml`. Key sections: `repo-path` (list of directories to scan), `git` (default username/email, scanner db), `task_dir`, `github_owner`, `work_dir`, `spark.scripts`.

## Development Conventions

- Follow standard Go conventions; no comments unless explicitly requested
- New features require BDD-style tests using Ginkgo/Gomega
- Test files use `_test.go` suffix, live alongside source in `internal/`
- Test suite files (`*_suite_test.go`) register the Ginkgo test runner for each package
- Keep `Makefile` as the single source of truth for build/test commands
- New commands should have usage docs in `docs/usage/`
- The UI language is primarily Chinese (documentation, user-facing messages)
