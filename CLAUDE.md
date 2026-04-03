# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Test Commands

```bash
make build          # Build for current OS (outputs ./spark)
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

Spark is a Go CLI tool (`module monolize`, binary `spark`) for managing multiple Git repositories. Built with **Cobra** (CLI), **Viper** (config), **PTerm** + **Bubble Tea** (TUI), tested with **Ginkgo/Gomega** (BDD).

### Code Structure

- **`main.go`** → calls `cmd.Execute()`
- **`cmd/`** — Cobra command definitions. `root.go` loads config from `~/.spark.yaml`. Subdirectories `cmd/git/` and `cmd/magic/` group related commands.
- **`internal/`** — Business logic, separated by domain:
  - `agent/` — AI agent config management (Claude Code, Codex, Kimi, GLM)
  - `config/` — Configuration loading and management
  - `git/` — Core Git operations (update, create, sync)
  - `mono/` — Mono-repo creation and submodule management
  - `task/` — Task dispatch/sync and GitHub repo creation
  - `tui/` — Shared terminal UI components (spinner, dialogs)
- **`docs/usage/`** — Usage documentation per command

### Command Hierarchy

```
spark
├── git [update|create|sync|gitcode|config|url|clone-org]
├── agent [list|view|edit|use|current] + agent profile [list|add|edit]
├── task [list|dispatch|sync]
└── magic [dns]
```

### Config

User config at `~/.spark.yaml` (see `.spark.yaml.example`). Key sections: `repo-path` (list of directories to scan), `git` (default username/email), `task_dir`, `github_owner`, `work_dir`.

## Development Conventions

- Follow standard Go conventions; no comments unless explicitly requested
- New features require BDD-style tests using Ginkgo/Gomega
- Test files use `_test.go` suffix, live alongside source in `internal/`
- Keep `Makefile` as the single source of truth for build/test commands
- New commands should have usage docs in `docs/usage/`
- The UI language is primarily Chinese (documentation, user-facing messages)
