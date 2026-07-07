# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.2.0]: https://github.com/variableway/spark-cli/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/variableway/spark-cli/releases/tag/v0.1.0
