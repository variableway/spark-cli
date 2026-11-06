# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `spark skill list [--json]` — Discover agent skills (`SKILL.md` directories) across project (`.mimocode/`, `.agents/`), global (`~/.claude/`, `~/.agents/`, `~/.mimocode/`), and builtin skill-pack locations, deduplicated by name with version-aware builtin preference (`internal/skill`)
- `spark skill sync <dir> [--clear]` — Copy all discovered skills into a target directory, optionally clearing it first
- `spark hub scan [path] [-o <file>]` — Scan git repositories with an `origin` remote, enrich via the GitHub API (description, language, visibility), and emit innate-apps registry format (`registry/apps.json`) (`internal/collection`)
- `spark hub scan --merge <registry>` — Merge with an existing registry file while preserving curated fields (`title`/`category`/`status`/`url`/`description`) and unmatched entries; `--skip-api`, `--deep`, `--category` flags
- `github.GetRepo(owner, repo)` — Fetch single-repository metadata (topics, homepage, created/pushed timestamps, owner) with `GITHUB_TOKEN` support
- BDD tests for `internal/skill` (discovery/dedup/sync) and `internal/collection` (parse/scan/merge/read-write)
- Docs — `docs/{zh,en}/usage/{skill,hub}.md`, README command tables, navigation entries
- `skills/spark-cli/SKILL.md` — Ready-to-install agent skill that documents how to drive the CLI: command map, common workflows, and the three routes for fetching a GitHub repository list
- `docs/{zh,en}/quick-start/nodejs-typescript-101.md` — Beginner lesson one for Node + TypeScript, using "write a navigation.json generator for a docs site" as the running case (mirrors the Go lesson), with a course prompt and SKILL.md template
- `docs/{zh,en}/spec/{skill,hub,witr,version}.md` and `docs/{zh,en}/features/{skill,hub,witr}.md` — Command specs and feature pages for the `skill`, `hub` and `witr` command groups, plus `spark version`
- `docs/{zh,en}/usage/git.md` — New section "How to get the list of GitHub repository projects" comparing `spark git update-org-status`, the `gh` CLI and `spark hub scan`

### Changed

- `spark git update-org-status` now accepts an **account** (organization **or** user) instead of an organization only; the account type is auto-detected and the matching profile repository is targeted — `<org>/.github` for organizations, `<user>/<user>` for users (e.g. `qdriven/qdriven`). The repository list is now fetched **paginated** (100 per page) instead of a single page, and `GITHUB_TOKEN` is honoured on every GitHub API call
- `internal/github` — Added `User-Agent: spark-cli` to API requests (requests without a User-Agent can be answered with `504` by intermediaries) and unified the JSON fetch path in `getJSON`
- Docs — `docs/{zh,en}/Agents.md` regenerated as a true mirror of `AGENTS.md` (command tree, per-command reference, automation history, build/test detail, config keys and assistant guidelines) instead of a condensed summary

### Fixed

- `internal/witr/proc` — `getCwdAndBinaryPath` (macOS) failed to parse `lsof` output because `strings.Lines` yields lines with trailing newlines, so the `cwd`/`txt` field labels never matched. Trim whitespace from the field label; the darwin test `TestGetCwdAndBinaryPath` now passes
- Docs — corrected several statements that contradicted the implementation: `spark git submodule add` takes one positional argument (the global `-p/--path` flag does not apply to it) and `submodule status` does have `-r/--recursive` and `-j/--parallel`; `spark git update` pulls `origin <current-branch>`; `spark magic clean` in node mode also deletes `package-lock.json` files; `spark script` config scripts use `name`/`content`/`path` (a `command:` key yields "script has no content"); `spark hub scan` scans the top level by default and writes back to the `--merge` file when no `-o` is given; the `default` mirror entry is documented for pip/go/node; `spark magic copy-config` gained a spec section; `spark git clone` and `spark git issues` gained spec sections
- Docs — fixed broken relative links (`../.vscode/*.json` pointed inside `docs/zh/`) and made every navigation entry, locale mirror and cross-link resolve
- Docs — the two historical analysis documents (external CLI integration report and the `spark-hub` RFC, both dated 2026-04-02) now carry a status banner: they were **not adopted**, and the `spark hub` command that ships today is the innate-apps registry scanner, an unrelated feature
- Docs — `AGENTS.md` contained literal backspace bytes inside the Windows pnpm path (`D:\pnpm^Hin`); restored to `D:\pnpm\bin`
- Docs — version samples refreshed from `v0.3.2` to `v0.3.3`; the README test-report line now matches the current package count (32 packages, 18 with tests)

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
