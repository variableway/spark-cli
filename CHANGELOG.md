# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
