# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `spark repo scan --json` — additionally writes a formatted (2-space indent) `registry_<folder>.json` with the same content as the YAML registry
- `spark repo scan --flatten` — moves repositories nested deeper than two levels (`category/repo` layout) up into the two-level layout before scanning; conflicts are skipped with a warning and never overwritten, empty intermediate directories are removed (fixes #26)

## [0.3.3] - 2026-10-20

### Added

- README — Quick Start (`spark magic flush-dns`) and a Test Report screenshot (`docs/assets/test-report.png`)
- `docs/{zh,en}/usage/how-to-build.md` — Build guide: Go binary, Node docs site, Bun `build --compile` single binaries, and the Windows pnpm global-path setup (store / global-dir / bin on D:)
- `docs/{zh,en}/quick-start/golang-cli-101.md` — Beginner lesson one (Go CLI basics, third-party packages, dependency management, Makefile vs Taskfile) with a ready-to-use course prompt and SKILL.md template
- `docs/{zh,en}/quick-start/git-worktree.md` — Git worktree development guide
- HTML test report — `make test-report` / `task test-report` run all suites via Ginkgo and write a self-contained interactive HTML report (suite/spec states, durations, failure details, filtering) to `reports/test-report.html`; backed by `internal/testreport` (renderer + BDD tests) and `tools/testreport` (JSON→HTML converter)
- `pnpm-lock.yaml` — Lockfile for reproducible docs-site installs

### Fixed

- Stable cross-platform build — `go.sum` removed from `.gitignore` and committed so `go build` no longer fails with "missing go.sum entry" on fresh clones (fixes #21)
- `Taskfile.yml` — `build` task no longer skips rebuild/reinstall via sources/generates fingerprinting; `task build` always rebuilds and reinstalls, matching Makefile behavior
- `spark git submodule add` (folder mode) — nested repos on Windows no longer fail with "Invalid path": all git-facing submodule paths are normalized to forward slashes (`update-index --cacheinfo` rejects backslashes; `rm`/`ls-files` pathspecs silently fail to match them)
- Windows test stability — `TestIntegration_ReadProcessNonexistent` now uses `math.MaxInt32` instead of PID 0 (PID 0 is the readable System Idle Process on Windows); `TestGetCmdlineSelf` also accepts the `.test` binary suffix used by the ginkgo CLI
- `Taskfile.yml` — Cross-compile `GOOS`/`GOARCH` moved to task-level `env` (per-command `env` was silently ignored, so `build:all` produced Windows PE files for every target)

### Changed

- AGENTS.md — Structure tree gains `cmd/version.go`; build section covers Taskfile cross-compile targets and the docs-site build; new automation records
- Docs navigation (`docs/{zh,en}/navigation.json`) — Quick Start group, How-to-Build and git-worktree entries

## [0.3.2] - 2026-09-17

### Added

- `spark repo` — Registry-file based multi-repository management (`scan` / `clone` / `list`) as an alternative to submodules, backed by `internal/registry`
- `spark version` — Print version, commit and build date stamped via ldflags
- `Taskfile.yml` — Task runner entry points mirroring the Makefile (build / install / install-binary / verify-install)
- `scripts/install-binary.{sh,ps1}` and `scripts/verify-install.{sh,ps1}` — Binary installation and install verification helpers
- Bilingual documentation site — `docs/zh/` (default locale) plus `docs/en/` mirror

### Changed

- `spark git batch-clone` — GitLab token provenance reporting (`--token` > `gitlab.token` > `GITLAB_TOKEN` > `GITLAB_PRIVATE_TOKEN`), `gitlab.host` scoping of auto-discovered credentials, and clearer "credentials rejected / no credentials / path not found" errors
- `spark magic clean` — Reworked traversal and cleanup logic
- Makefile — Version / commit / build-date ldflags stamping and cross-platform build targets
- Dependencies updated, pnpm workspace metadata added

### Fixed

- `spark git submodule add` — Local directory and multi-repository additions no longer fail
- `scripts/verify-install.sh` — Verification logic corrected

### Removed

- `spark task` — Task management commands and the `internal/task` package, along with the `task_dir` / `github_owner` / `work_dir` config keys
- `internal/tui` — TUI helpers that were only used by `spark task`
- `tasks/` — Legacy task/issue planning documents
- `scripts/copy-template.sh` — Sample script that referenced `tasks/example-feature.md`
- `.github-task-workflow.yaml` / `.github-task-workflow.active-issue` — GitHub Task Workflow tool config and state files

## [0.2.0] - 2026-07-07

### Added

- `spark git batch-clone` — GitLab support for self-hosted and gitlab.com instances, including nested subgroups
- `spark git batch-clone --token` — GitLab authentication via flag or `GITLAB_TOKEN` / `GITLAB_PRIVATE_TOKEN` env vars
- `spark git update --ssh` — Force HTTPS GitHub remotes to SSH during batch update
- `spark magic copy-config` — Deploy embedded Neovim and Ghostty dotfile templates to local, SSH, or custom paths
- `internal/gitlab` — GitLab API client for batch-clone
- `internal/templates` — Embedded nvim/ghostty configs via `//go:embed`

### Changed

- `spark git clone` — Improved URL/slug parsing and `gh repo clone` integration (default SSH)
- Documentation aligned with current command set (`README.md`, `AGENTS.md`, `docs/usage/`, `CLAUDE.md`)

### Fixed

- GitLab batch-clone fork detection via `forked_from` field

## [0.1.0] - 2026-05-29

### Added

- Initial public release
- `spark magic clean` — Recursively clean `node_modules` and `.venv` directories
- Core `spark git`, `spark task`, `spark script`, `spark magic`, `spark docs`, and `spark witr` commands
- Cross-platform binaries (Linux, macOS amd64/arm64, Windows)

[0.3.2]: https://github.com/variableway/spark-cli/compare/v0.2.0...v0.3.2
[0.2.0]: https://github.com/variableway/spark-cli/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/variableway/spark-cli/releases/tag/v0.1.0
