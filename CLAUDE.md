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

Spark is a Go CLI tool (`module spark`, binary `spark`) for managing multiple Git repositories, AI agent configs, scripts, and task workflows. Built with **Cobra** (CLI), **Viper** (config), **PTerm** + **Bubble Tea** (TUI), tested with **Ginkgo/Gomega** (BDD).

### Code Structure

- **`main.go`** → calls `cmd.Execute()`
- **`cmd/`** — Cobra command definitions. `root.go` loads config from `~/.spark.yaml` and auto-migrates from legacy `~/.monolize.yaml`. Subdirectories group commands:
  - `cmd/git/` — Git repo management commands
  - `cmd/magic/` — System utility commands (DNS flush, mirror switching)
  - `cmd/script/` — Script management commands
  - `cmd/agent.go`, `cmd/agent_profile.go`, `cmd/task.go` — Top-level commands in the root `cmd/` package
- **`internal/`** — Business logic, separated by domain:
  - `agent/` — AI agent config management (Claude Code, Codex, Kimi, GLM) and profile templates
  - `config/` — Configuration loading and management
  - `git/` — Core Git operations (find repos, update, remote management, URL conversion)
  - `github/` — GitHub API interactions (list org repos, parse org URLs)
  - `mono/` — Mono-repo creation and submodule management
  - `script/` — Script discovery (from config and `scripts/` dir) and execution
  - `task/` — Task init/dispatch/sync, feature CRUD, and implementation via `kimi` CLI
  - `tui/` — Shared terminal UI components (spinner, dialogs, selector)
- **`docs/usage/`** — Usage documentation per command

### Command Hierarchy

```
spark
├── git [update|create|sync|gitcode|config|url|clone-org|update-org-status]
├── agent [list|view|edit|reset] + agent profile [list|add|edit]
├── task [list|init|dispatch|sync|create|delete|impl]
├── script [list|run]
└── magic [flush-dns|pip|go|node]     # Mirror source switching + DNS
```

### Key Patterns

- **TUI mode**: `task`, `agent`, and other commands accept `--tui` flag for interactive mode with Bubble Tea selectors and PTerm spinners. CLI mode is the default.
- **Config binding**: Flags are bound to Viper via `viper.BindPFlag()` in `init()` functions. Config keys use snake_case in YAML but camelCase in struct tags.
- **Script sources**: Scripts can come from `~/.spark.yaml` (`spark.scripts` or top-level `scripts`) or from a `scripts/` directory. Config scripts take precedence.

### Config

User config at `~/.spark.yaml`. Key sections: `repo-path` (list of directories to scan), `git` (default username/email), `task_dir`, `github_owner`, `work_dir`, `spark.scripts`.

## Development Conventions

- Follow standard Go conventions; no comments unless explicitly requested
- New features require BDD-style tests using Ginkgo/Gomega
- Test files use `_test.go` suffix, live alongside source in `internal/`
- Test suite files (`*_suite_test.go`) register the Ginkgo test runner for each package
- Keep `Makefile` as the single source of truth for build/test commands
- New commands should have usage docs in `docs/usage/`
- The UI language is primarily Chinese (documentation, user-facing messages)
