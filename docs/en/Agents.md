# AGENTS.md

This document records the key tasks AI assistants have executed in this project, the system integration work, and the complete feature reference.
The [`AGENTS.md`](../../AGENTS.md) at the repository root is the authoritative source; this page is the site mirror.

## Project Overview

**Spark** is a CLI tool (`module spark`, binary `spark`) for managing multiple Git repositories, scripts, and task workflows, with practical system utilities bundled in. Built on **Cobra** (CLI), **Viper** (config), **PTerm** (terminal UI), with **Ginkgo/Gomega** for BDD testing.

Core capabilities:

1. **Multi-repo update** — batch-update multiple Git repositories to the latest version (SSH supported)
2. **Repo cloning** — clone GitHub repositories via `gh repo clone` (SSH by default); `batch-clone` supports GitHub organizations/users and GitLab groups/users
3. **Submodule management** — `submodule add` (URL or local directory), `submodule init`, `submodule status`, `submodule ensure-ssh`, `git sync`
4. **Git user configuration** — `spark git config` configures the repository's Git user info
5. **Gitcode remote management** — `spark git gitcode` adds a Gitcode remote address
6. **Account status** — `spark git update-org-status` writes the account (organization/user) repository list into the README
7. **Repo scanning** — `spark git scan` scans the repositories in a directory and saves them to SQLite
8. **Repo pushing** — `spark git push-all` batch-commits and pushes all changes
9. **Issue creation** — `spark git issues` creates GitHub Issues from Markdown/task files
10. **Script management** — discover and run scripts from `~/.spark.yaml` or the `scripts/` directory
11. **System utilities** — `spark magic` provides DNS cache flushing, `node_modules`/`.venv` cleanup, pip/npm/go mirror switching, and Neovim/Ghostty template deployment
12. **Docs management** — `spark docs init`/`spark docs site` (docmd site initialization)
13. **Process diagnostics** — `spark witr` (Why Is This Running), inspecting why a process or port is running
14. **Repo management** — `spark repo` manages multiple GitHub repositories in a directory via a registry file (`scan`/`clone`/`list`), replacing submodules
15. **Skill management** — `spark skill` discovers and syncs AI agent skills (`SKILL.md` directories), with `list`/`sync`
16. **Project hub** — `spark hub scan` scans local Git repositories and generates innate-apps registry (`registry/apps.json`) registration info

## Tech Stack

- **Language**: Go 1.27+ (see `go.mod`)
- **CLI framework**: [Cobra](https://github.com/spf13/cobra) + [Viper](https://github.com/spf13/viper)
- **Terminal UI**: [pterm](https://github.com/pterm/pterm) + [Bubble Tea](https://github.com/charmbracelet/bubbletea) + custom TUI components
- **Test framework**: [Ginkgo](https://github.com/onsi/ginkgo) + [Gomega](https://github.com/onsi/gomega) (BDD style, `internal/`) + standard `testing` (`cmd/`)
- **Build system**: Makefile + Taskfile (cross-platform: Windows / Linux / macOS)

## Project Structure

```
spark-cli/
├── main.go                  # Entry point (calls cmd.Execute())
├── cmd/
│   ├── root.go              # Root command, global flags, config loading and .monolize.yaml auto-migration
│   ├── version.go           # spark version (prints version / commit / build date)
│   ├── witr.go              # Bridge to internal/witr/app.Root()
│   ├── git/                 # Git repository management commands
│   │   ├── git.go           # GitCmd parent command
│   │   ├── init.go          # spark git init
│   │   ├── clone.go         # spark git clone
│   │   ├── update.go        # spark git update (--ssh)
│   │   ├── submodule.go     # spark git submodule {add,init,status,ensure-ssh}
│   │   ├── sync.go          # spark git sync (--recursive)
│   │   ├── gitcode.go       # spark git gitcode (--url)
│   │   ├── config.go        # spark git config (--username, --email)
│   │   ├── url.go           # spark git url
│   │   ├── batch_clone.go   # spark git batch-clone (GitHub + GitLab)
│   │   ├── issues.go        # spark git issues (-r, -f, -d, -l, --dry-run)
│   │   ├── update_org_status.go  # spark git update-org-status (account type auto-detection)
│   │   ├── push_all.go      # spark git push-all
│   │   └── scan.go          # spark git scan (-d/--db, --skip-api)
│   ├── repo/                # Repository registry management commands
│   │   ├── repo.go          # RepoCmd parent command
│   │   ├── scan.go          # spark repo scan [folder-name]
│   │   ├── clone.go         # spark repo clone (-r, -f)
│   │   └── list.go          # spark repo list (-f)
│   ├── magic/               # System utility commands
│   │   ├── magic.go         # MagicCmd parent command
│   │   ├── clean.go         # spark magic clean (-m node|python)
│   │   ├── copy_config.go   # spark magic copy-config (deploy nvim/ghostty templates)
│   │   ├── flush_dns.go     # spark magic flush-dns
│   │   ├── pip.go           # spark magic pip {list,use,current}
│   │   ├── go.go            # spark magic go {list,use,current}
│   │   └── node.go          # spark magic node {list,use,current}
│   ├── script/              # Script management
│   │   ├── script.go        # ScriptCmd parent command
│   │   ├── list.go          # spark script list
│   │   └── run.go           # spark script run <name> [args...]
│   ├── skill/               # AI Skill management
│   │   ├── skill.go         # SkillCmd parent command
│   │   ├── list.go          # spark skill list [--json]
│   │   └── sync.go          # spark skill sync <dir> [--clear]
│   ├── hub/                 # Project Hub (collections registration)
│   │   ├── hub.go           # HubCmd parent command
│   │   └── scan.go          # spark hub scan [path] [-o, --merge, --skip-api, --deep]
│   └── docs/                # Documentation management
│       ├── docs.go          # DocsCmd parent command
│       ├── init.go          # spark docs init (--root)
│       └── site.go          # spark docs site (--root)
├── internal/
│   ├── config/              # Config loading
│   ├── git/                 # Git operation wrappers (finder/updater/init/submodule/pusher + scanner subpackage)
│   │   └── scanner/         # Scanning and SQLite persistence used by git scan
│   ├── github/              # GitHub API (org / markdown issue)
│   ├── gitlab/              # GitLab API (batch-clone: URL parsing, token sources, nested groups)
│   ├── registry/            # Scan/read-write/merge logic for the repo command
│   ├── collection/          # registry/apps.json model, scan and merge for the hub command
│   ├── script/              # Script discovery (config + scripts/ directory) and execution
│   ├── skill/               # Skill discovery (SKILL.md directory scanning) and sync
│   ├── templates/           # Embedded dotfiles (nvim + ghostty)
│   ├── testreport/          # Ginkgo JSON report → self-contained HTML renderer (incl. BDD tests)
│   └── witr/                # Why-Is-This-Running process diagnostics engine
├── tools/
│   └── testreport/          # test-report CLI: read ginkgo --json-report output, generate HTML
├── pkg/
│   └── witr/model/          # Shared data model for witr
├── docs/                    # docmd documentation site (bilingual Chinese/English)
│   ├── zh/                  # Chinese (default locale, rendered at the root URL)
│   │   ├── usage/           # Usage notes for each command
│   │   ├── spec/            # Specification documents
│   │   ├── features/        # Feature descriptions
│   │   ├── analysis/        # Architecture analysis and RFCs
│   │   ├── quick-start/     # Quick start
│   │   ├── Agents.md        # Site mirror of AGENTS.md
│   │   └── navigation.json  # Sidebar navigation
│   ├── en/                  # English mirror (rendered at /en/, hierarchy exactly parallel to zh/)
│   └── ...
├── skills/                  # Installable Agent Skill (spark-cli usage notes)
│   └── spark-cli/SKILL.md
├── scripts/                 # Default script directory (used by spark script) + install/verify scripts
├── .vscode/                 # VS Code configuration (tasks/launch/settings)
├── Makefile                 # Build scripts (build/build-linux/build-darwin/test/lint/clean)
├── Taskfile.yml             # Equivalent Task commands (build/install/install-binary/verify-install)
├── docmd.config.js          # docmd site configuration (i18n.default: zh)
├── go.mod / go.sum
└── package.json             # docmd dependencies
```

## Command Hierarchy

```
spark
├── version                 (shows spark version / commit / build date)
├── git
│   ├── init                 (--owner, -r/--repo, --private, --skip-gh)
│   ├── clone                (<url-or-slug> [directory] [-- <git-args>])
│   ├── update               (-p, --ssh)
│   ├── submodule
│   │   ├── add              (<path-or-url>, -n, --name)
│   │   ├── init             (-r, --recursive, -j, --parallel, --name)
│   │   ├── status           (-r, --recursive)
│   │   └── ensure-ssh
│   ├── sync                 ([repo-path], -r, --recursive)
│   ├── gitcode              (-p, --url)
│   ├── config               ([repo-path], --username, --email)
│   ├── url                  ([repo-path])
│   ├── batch-clone          (<account-name-or-url>, --ssh, --include, --exclude,
│   │                         --include-forks, -o, --token)
│   ├── issues               (-r, -f, -d, -l, --dry-run)
│   ├── update-org-status    (<account-name-or-url>, --dry-run, -o, --update-dot-github,
│   │                         --section, --skip-push)
│   ├── push-all             (-p)
│   └── scan                 ([folder-path], -d, --db, --skip-api)
├── repo
│   ├── scan                 ([folder-name])
│   ├── clone                (-r, --repo, -f, --file)
│   └── list                 (-f, --file)
├── script
│   ├── list
│   └── run
├── skill
│   ├── list                 (--json)
│   └── sync                 (<target-dir>, --clear)
├── hub
│   └── scan                 ([path], -o/--output, --merge, --skip-api, --deep, --category)
├── magic
│   ├── clean                (-m, --mode)
│   ├── copy-config          ([<user@host:path>])
│   ├── flush-dns
│   ├── pip {list,use,current}
│   ├── go {list,use,current}
│   └── node {list,use,current}
├── docs
│   ├── init                 (--root)
│   └── site                 (--root)
└── witr                     (--pid, --port/-o, --file/-f, --container/-c, --tree/-t,
                              --env, --json, --short/-s, --warnings,
                              --verbose, --exact/-x, --no-color)
```

## Automation Task Record

### 1. BDD Test Integration (2026-02-26)
- **Task**: Add BDD-style unit tests for the `internal` packages.
- **Tooling**: Introduced the `Ginkgo` and `Gomega` frameworks.
- **Coverage**: `internal/config`, `internal/git` (incl. finder/updater/submodule), `internal/script`, `internal/github` (issue/markdown_issue/org), `internal/gitlab`, `internal/witr/output`.
- **Verification**: All tests pass, verified via `make test-bdd`.

### 2. Cross-platform Makefile Build (2026-02-26)
- **Task**: Create a build system supporting Windows, Linux and macOS.
- **Features**:
    - Automatic OS detection (`ifeq ($(OS),Windows_NT)`).
    - Cross-compilation support (`build-linux`, `build-darwin`).
    - A unified clean and test interface.
    - Build artifacts are installed automatically into `~/.local/bin/spark`.

### 3. VS Code Environment Standardization (2026-02-26)
- **Task**: Optimize the `.vscode` directory configuration.
- **Results**:
    - `tasks.json`: deeply bound to the Makefile.
    - `launch.json`: provides a standardized debug template.
    - `settings.json`: unified Go language development conventions.

### 4. GitLab batch-clone Support
- Added the `internal/gitlab` subpackage;
- `spark git batch-clone <git-host>/<group>/<subgroup>` also supports self-hosted GitLab;
- Supports authentication via the `--token` / `GITLAB_TOKEN` / `GITLAB_PRIVATE_TOKEN` environment variables.
- See "Complete CLI Command Reference" below for the full command list.

### 5. GitLab Nested Groups and Credential Scoping (2026-09-16)
- **Nested groups**: `detectAccountType` / `apiGetGroupProjects` / `apiGetUserProjects` uniformly encode paths with
  `escapePath` (`url.PathEscape`), and `include_subgroups=true` recursively pulls subgroups at any depth;
  `ProjectRelativePath` lays them out by namespace-relative path, so that identically named projects in
  different subgroups do not overwrite each other.
- **Scheme-less input**: `IsGitLabURL` recognizes `gitlab.com/group/sub`, and `ParseGitLabURL` automatically
  prepends `https://`.
- **Traceable credential source**: new `TokenSourceFlag` / `TokenSourceConfig` / `TokenSourceEnv` / `TokenSourceEnvAlt`
  constants and `tokenOrigin()`; `cmd/git.resolveGitLabToken` resolves
  `--token` > `gitlab.token` > `GITLAB_TOKEN` > `GITLAB_PRIVATE_TOKEN`,
  prints `Using token from: ...` on startup, and names the source of the rejected credential in errors.
- **Credential host scoping**: the new `gitlab.host` config scopes automatically discovered credentials to that
  instance; on a mismatch it prints `Ignoring ...: it is scoped to ...` and skips the credential;
  `internal/gitlab.ExtractHost` normalizes URLs / bare domains / `host:port` to a lowercase host for comparison.
- **Error classification**: an unauthenticated private instance returns 404 rather than 401, so `detectAccountType`
  distinguishes three messages: "credentials rejected" / "no credentials provided" / "path does not exist".
- **Tests**: `internal/gitlab/gitlab_test.go` (including `httptest` mocks for nested groups and 401/404) and
  `cmd/git/batch_clone_test.go` (table-driven cases for the host scoping of `resolveGitLabToken`).

### 6. repo Registry and magic/docs Commands
- `spark repo` (`cmd/repo/` + `internal/registry`) replaces submodules with `registry_<folder>.yaml` to manage
  multiple repositories under a directory: `scan` / `clone` / `list`.
- `spark magic` (`cmd/magic/`) provides `clean` / `copy-config` / `flush-dns` / `pip|go|node {list,use,current}`.
- `spark docs` (`cmd/docs/`) provides `init` / `site`, for scaffolding a docmd site.
- `spark version` (`cmd/version.go`) prints version / commit / build date.

### 7. Windows Test and Build Fixes (2026-10-20)
- **Build stability**: `go.sum` was removed from `.gitignore` and committed (previously a fresh clone always failed
  to build); `task build` dropped the sources/generates fingerprint (previously a second run skipped the install).
- **Test fixes** (all were wrong Windows platform assumptions, not deleted cases):
  - `TestAddNestedRepos`: `git update-index --cacheinfo` rejects backslash paths —
    `AddExistingRepoAsSubmodule` and `isSubmoduleGitlink` now uniformly use `filepath.ToSlash`,
    so `.gitmodules` always stores forward-slash paths.
  - `TestIntegration_ReadProcessNonexistent`: PID 0 on Windows is the readable System Idle
    Process — switched to `math.MaxInt32` (nonexistent on every platform).
  - `TestGetCmdlineSelf`: the test binary compiled by the ginkgo CLI has no `.exe` suffix — also accept `.test`.
- **HTML test report**: `make test-report` / `task test-report` run the full Ginkgo suite and generate
  `reports/test-report.html` (suite/case status, duration, failure details, status filtering + search).
  Ginkgo on Windows must be given `--output-dir` (an internal `path.Dir` bug); the target pre-creates the directory.

### 8. pnpm Global Configuration, Documentation Completion and Global innate-fe-cli (2026-10-20)
- **pnpm global paths point to the D drive**: `store-dir=D:\.pnpm-store`, `global-dir=D:\pnpm\global`,
  `global-bin-dir=D:\pnpm\bin`, `PNPM_HOME=D:\pnpm` + `D:\pnpm\bin` at the front of the user PATH
  (written with `[Environment]::SetEnvironmentVariable`; do not use `setx`, which truncates PATH at 1024 characters).
  pnpm was upgraded to 12.14.0.
- **Windows build chain**: `task build` produces `spark.exe` and installs it into `~/.local/bin` (both `spark.exe`
  and the extension-less `spark`, verified with sha256); `pnpm install && pnpm build` produces the documentation
  site; fixed the cross-compilation env in `Taskfile.yml` (per-command `env` was ignored, so `build:all` produced PE
  binaries for every platform).
- **Documentation**: the README gained a Quick Start section (`spark magic flush-dns`) and a Test Report screenshot
  (`docs/assets/test-report.png`); added `docs/{zh,en}/usage/how-to-build.md`
  (Go / Node / Bun builds + pnpm environment) and `docs/{zh,en}/quick-start/golang-cli-101.md`
  (the first lesson of the Golang CLI course, including the course prompt and the Skill template).
- **Global innate-fe-cli**: after `bun build --compile` produces a single binary, it is installed into
  `~/.local/bin` via an NTFS hard link (`innate-fe` / `innate-fe-cli` each carry a `.exe`, and the 4 names share
  1 copy of the data on disk).

### 9. From-Scratch Build Tutorials and SKILL Documentation (2026-10-21, issue #24)
- **New step-by-step tutorials** (complementary to the conceptual lessons of golang-cli-101, with code that can be
  copied and run as-is):
  - `docs/{zh,en}/quick-start/golang-project-from-scratch.md` — creating a Go CLI project from scratch:
    a line-by-line explanation of how `go mod init` generates go.mod, the dependency list and installation of the
    CLI trio (Cobra/Viper/PTerm), the standard cmd/internal/pkg layering responsibilities, the first Cobra command,
    a section-by-section reading of the Taskfile + a minimal template, with the SKILL
    `golang-project-from-scratch` attached.
  - `docs/{zh,en}/quick-start/docs-site-from-scratch.md` — creating a docmd documentation site from scratch:
    a field-by-field explanation of `npm init` and package.json (including a Go↔Node comparison table), docmd
    installation, an explanation of the docmd.config.js configuration, navigation.json and bilingual i18n, publishing
    to GitHub Pages with GitHub Actions (the full text of `.github/workflows/docs.yml` + Settings → Pages →
    Source: GitHub Actions), with the SKILL `docs-site-from-scratch` attached.
- **Navigation**: the quick-start group in `docs/{zh,en}/navigation.json` gains two pages; the SKILL is embedded as
  an appendix code block (following the installation convention of appendix B in golang-cli-101, effective once
  stored in `.claude/skills/<name>/SKILL.md`).

## Complete CLI Command Reference

### Global Options

Defined by `cmd/root.go` via `rootCmd.PersistentFlags()`:

| Option | Description |
|------|------|
| `--config` | Config file path (default: `$HOME/.spark.yaml`) |
| `-p, --path` | Repository scan directory path (StringSlice, default `["."]`, bound to the viper key `repo-path`) |

Config initialization flow (`initConfig` + `migrateOldConfig`):

1. If `--config` is specified, use that file; otherwise default to `$HOME/.spark.yaml`.
2. On startup, detect the legacy config `~/.monolize.yaml`: if it exists and `~/.spark.yaml` does not, it is
   automatically renamed/migrated.
3. `viper.AutomaticEnv()` enables environment-variable overrides.

---

### `spark git` — Git Repository Management

The parent command `GitCmd` is defined in `cmd/git/git.go` and contains the following subcommands (registered per file in the `init()` functions):

```bash
spark git init                   # Initialize the repository and create the GitHub remote
spark git clone <url-or-slug>    # Clone via gh repo clone (SSH by default)
spark git update [-p ...]        # Scan and update all repositories (--ssh forces SSH)
spark git submodule add ...      # Add a submodule
spark git submodule init ...     # Initialize all/specified submodules
spark git submodule status       # Show the submodule status
spark git submodule ensure-ssh   # Rewrite HTTPS in .gitmodules to SSH
spark git sync [path]            # Sync all submodules of the current repository
spark git gitcode [-p ...]       # Add a gitcode remote
spark git config [path]          # Configure the Git user info
spark git url [path]             # Print the remote URL of the current repository
spark git batch-clone <account>  # Batch-clone the repositories of a GitHub/GitLab account
spark git issues                 # Create GitHub Issues from Markdown/task files
spark git update-org-status <account> # Generate the account repository list and write it into the README
spark git push-all [-p ...]      # Scan and commit/push all repositories
spark git scan [folder-path]     # Scan the repositories and write to SQLite
```

#### `spark git update`
Scan all repositories under `repo-path` and update them to the latest version.

```bash
spark git update -p /path/to/repos
spark git update -p ~/workspace -p ~/projects
spark git update --ssh                                  # Force HTTPS→SSH
```

| Option | Description |
|------|------|
| `-p, --path` | Scan directories (may be specified multiple times, overrides `repo-path`) |
| `--ssh` | Force HTTPS GitHub URLs to be rewritten to SSH before updating |

#### `spark git clone`
Clone a GitHub repository via `gh repo clone`, using SSH by default.

```bash
spark git clone https://github.com/Nutlope/pdf-to-interactive-lesson.git
spark git clone Nutlope/pdf-to-interactive-lesson
spark git clone https://github.com/owner/repo.git my-dir -- --branch main --depth 1
```

Supported input formats:
- `https://github.com/owner/repo.git`
- `git@github.com:owner/repo.git`
- `github.com/owner/repo`
- `owner/repo`

Extra arguments after `--` are passed through to `git clone`.

#### `spark git init`
Initialize the current directory as a Git repository and create the GitHub remote repository.

```bash
spark git init --owner variableway              # Initialize and create the remote repository
spark git init --owner variableway --private    # Create a private repository
spark git init --skip-gh --owner variableway    # Local init only, skip GitHub
```

| Option | Description |
|------|------|
| `--owner` | GitHub owner (default: the `github-owner` config) |
| `-r, --repo` | Repository name (default: the current directory name) |
| `--private` | Create a private repository |
| `--skip-gh` | Skip `gh repo create --push` |

Execution steps (when the GitHub repository already exists, only steps 2-3 apply):
1. `git init`
2. Configure `git user.name` / `user.email` (from `git.username` / `git.email`)
3. Scan the GitHub repositories in the subdirectories and add them as submodules
4. Generate `.gitignore`
5. `chore: initial commit via spark git init`
6. `gh repo create --push` (unless `--skip-gh`)

#### `spark git submodule`
Parent command for submodule management.

##### `submodule add <path-or-url>`
- URL mode: `spark git submodule add https://github.com/owner/repo`
- Folder mode: `spark git submodule add ./path/to/folder` (scans all GitHub repositories in the directory and adds them as submodules)

| Option | Description |
|------|------|
| `-n, --name` | Custom submodule path name (in URL mode the repository name is used by default) |

##### `submodule init`
Runs `git submodule update --init`:

```bash
spark git submodule init                          # Initialize all uninitialized submodules serially
spark git submodule init -j 4                     # Parallel, 4 workers
spark git submodule init --recursive              # Recursively initialize nested submodules
spark git submodule init --name spark-cli         # Initialize only the specified submodule
```

| Option | Description |
|------|------|
| `-r, --recursive` | Recursively initialize nested submodules |
| `-j, --parallel` | Number of parallel workers (default 1) |
| `--name` | Initialize only the submodule with the given name |

##### `submodule status`
Shows the path, initialization state, commit hash and branch of each submodule.

| Option | Description |
|------|------|
| `-r, --recursive` | Show nested submodules |
| `-j, --parallel` | Not used in the status command |

##### `submodule ensure-ssh`
Rewrites all HTTPS GitHub URLs in `.gitmodules` to their SSH form (`git@github.com:...`).

#### `spark git sync [path]`
Pulls the remote of the parent repository and updates all submodules to the latest remote commit.

```bash
spark git sync .
spark git sync --recursive        # Nested submodules
spark git sync /path/to/repo
```

#### `spark git gitcode`
Batch-adds a `gitcode` remote to GitHub repositories (automatically converting `github.com` → `gitcode.com`).

```bash
spark git gitcode -p /path/to/repos
spark git gitcode --url https://custom.gitcode.url
```

| Option | Description |
|------|------|
| `--url` | Custom Gitcode remote URL (converted automatically by default) |

#### `spark git config [path]`
Reads the default `git.username`/`git.email` (from `~/.spark.yaml`) and writes them into the local repository's `git config`.

```bash
spark git config                                # Show the current configuration
spark git config --username foo --email bar     # Explicit override
```

| Option | Description |
|------|------|
| `--username` | Git user name (default: `git.username`) |
| `--email` | Git email (default: `git.email`) |

Configuration precedence: command line → `~/.spark.yaml` → prompt the user to configure.

#### `spark git url [path]`
Reads and prints the origin URL of the current repository.

#### `spark git batch-clone`
Automatically recognizes GitHub or GitLab from the input and clones all repositories under the account.

```bash
# GitHub
spark git batch-clone variableway
spark git batch-clone https://github.com/variableway

# GitLab (self-hosted or gitlab.com, nested groups at any depth are supported recursively)
spark git batch-clone https://gitlab.example.com/myorg/mygroup
spark git batch-clone https://gitlab.example.com/myorg/mygroup/subgroup
spark git batch-clone https://gitlab.com/gitlab-com/gl-infra --token <token>
spark git batch-clone gitlab.com/gitlab-com/gl-infra         # https:// may be omitted

# General
spark git batch-clone variableway --ssh
spark git batch-clone variableway -o ./repos
spark git batch-clone <url> --token <token>      # the GITLAB_TOKEN / GITLAB_PRIVATE_TOKEN environment variables are also supported
```

GitLab implementation notes:

- `gitlab.IsGitLabURL` supports scheme-less input (`gitlab.com/group/sub`): as long as the first path segment is a
  domain containing `.` it is treated as GitLab; `gitlab.ParseGitLabURL` automatically prepends the `https://` prefix,
  so `spark git batch-clone gitlab.com/gitlab-com/gl-infra` is valid
- Group paths must be URL-encoded when calling API v4 (`group/sub/project` → `group%2Fsub%2Fproject`),
  otherwise nested groups return 404; see `internal/gitlab.escapePath` (shared by `detectAccountType` and the two
  projects fetch functions)
- Resolution order: with `--token` the REST API is used first (it can give precise errors), otherwise it falls back to
  `glab`, and finally tries the API without credentials
- Clone paths on disk follow the namespace-relative path (`internal/gitlab.ProjectRelativePath`),
  e.g. `archiver`, `observability/tenant-observability/argocd-tenant-plugin`, so that identically named projects in
  subgroups do not overwrite each other
- Token precedence: `--token` > `gitlab.token` in `~/.spark.yaml` (`viper.BindPFlag`) > `GITLAB_TOKEN` >
  `GITLAB_PRIVATE_TOKEN`; the source label is computed by `cmd/git.resolveGitLabToken`, which prints
  `Using token from: ...` on startup, and is included in errors too (a stale invalid token left in the config file
  takes precedence over the environment variable, which is a common source of confusion)
- `gitlab.host` (optional) scopes automatically discovered credentials (config file + environment variables) to that
  instance: on a host mismatch the credential is skipped with the message
  `Ignoring ...: it is scoped to ...`, preventing a self-hosted instance's token from being sent to `gitlab.com` and
  making even public groups fail to authenticate; `--token` is explicitly specified and therefore unrestricted, and
  without a configured host the previous behavior is preserved (see `internal/gitlab.ExtractHost`)
- An unauthenticated private instance / private group returns 404 rather than 401, so the error message distinguishes
  the three cases "no credentials provided" / "credentials invalid or no access" / "path does not exist", avoiding
  reporting a missing token as not found

| Option | Description |
|------|------|
| `--ssh` | Use SSH URLs (GitHub `git@github.com:...`, GitLab `git@<host>:...`) |
| `--include` | Only clone repositories whose name contains any of the patterns (comma-separated) |
| `--exclude` | Skip repositories whose name contains any of the patterns (comma-separated) |
| `--include-forks` | Include forked repositories (GitHub determines this via `repo.Fork`; GitLab via the `forked_from` field) |
| `-o, --output` | Output directory (default `.`) |
| `--token` | GitLab private token (explicitly specified, not restricted by `gitlab.host`; can also be provided by the `GITLAB_TOKEN` / `GITLAB_PRIVATE_TOKEN` environment variables or `gitlab.token` in `~/.spark.yaml`) |

> Token source constants are defined in `internal/gitlab.TokenSourceFlag` / `TokenSourceConfig` / `TokenSourceEnv` / `TokenSourceEnvAlt`,
> and are returned by `cmd/git.resolveGitLabToken` with the precedence above, printing `Using token from: ...`.

#### `spark git issues`
Two modes: create an Issue from every Markdown file in a directory, or create an Issue from a task file (`## Task <id>...`).

```bash
# Directory mode
spark git issues -d ./docs -r owner/repo

# Task mode
spark git issues -f ./issues/task-bug-fix.md -r owner/repo

# Automatically resolve owner/repo from the current repository (requires a GitHub remote)
spark git issues -d ./docs --dry-run

# Add labels
spark git issues -d ./docs -l bug,enhancement
```

| Option | Description |
|------|------|
| `-r, --repo` | Target repository (`owner/repo`); when not specified it is resolved from the current git remote |
| `-d, --dir` | Markdown directory (directory mode) |
| `-f, --file` | Task file (task mode) |
| `-l, --labels` | Issue labels (comma-separated) |
| `--dry-run` | Preview only, nothing is created |

> `-d` and `-f` are mutually exclusive; exactly one must be given.

#### `spark git update-org-status`
Fetches all repositories under a GitHub account (organization or user), sorts them by star count, and writes them as a section into the README.

```bash
spark git update-org-status qdriven                       # Write to .github/README.md
spark git update-org-status qdriven --update-dot-github   # Push directly to the profile repository
spark git update-org-status qdriven --dry-run
spark git update-org-status qdriven -o ./docs/README.md
spark git update-org-status qdriven --section "Projects"
spark git update-org-status qdriven --skip-push
```

| Option | Description |
|------|------|
| `--dry-run` | Print the content, do not write it to the file |
| `-o, --output` | Output path in local mode (default: `.github/README.md`) |
| `--update-dot-github` | Clone that account's profile repository directly and modify it |
| `--section` | Name of the section to update/insert (default: `Project List`) |
| `--skip-push` | Skip `git commit` and `git push` |

Features:
- **Automatic account type detection**: for an organization the profile repository is `<org>/.github`
  (`README.md` + `profile/README.md`); for a user it is `<user>/<user>` (`README.md` at the repository root).
  Therefore a personal profile repository (e.g. `qdriven/qdriven`) can be refreshed with the same command
- The repository list is **fetched page by page** (100 per page), so the single-page limit does not apply
- Setting `GITHUB_TOKEN` raises the API rate limit (60 requests/hour when anonymous)
- Forked repositories are not written into the table and are not counted in the statistics
- By default it writes to the local `.github/README.md`; when run inside a `.github` directory it also writes `profile/README.md`
- With `--update-dot-github` it clones to `$TMPDIR/github-repo-<account>-<ts>`, writes the content, and then commits/pushes

#### `spark git push-all`
Scan all repositories under `repo-path` and run `git add -A` → `git commit` → `git push` for GitHub repositories that have changes, prompting on conflicts.

#### `spark git scan [folder-path]`
Recursively scan the repositories in a directory, optionally calling the GitHub/GitLab API to fetch metadata, and write the result to SQLite.

```bash
spark git scan                                # Scan the current directory by default
spark git scan ~/workspace
spark git scan . --skip-api
spark git scan . --db ~/.innate/feeds.db
```

| Option | Description |
|------|------|
| `[folder-path]` | Directory to scan (positional argument, default `.`) |
| `-d, --db` | SQLite database path (default: `~/.innate/feeds.db`, configurable via `git.scanner.db` or the `~`-prefix extension) |
| `--skip-api` | Skip the API, scan local repositories only |

The default database path can be set via `git.scanner.db` in `~/.spark.yaml`. Setting `GITHUB_TOKEN` raises the GitHub API rate limit.

---

### `spark repo` — Repository Management

The parent command `RepoCmd` is defined in `cmd/repo/repo.go` and manages multiple GitHub repositories under a directory via a registry file (replacing submodules).

```bash
spark repo scan [folder-name]                       # Scan the directory and write registry_<folder>.yaml
spark repo clone -f registry_<folder>.yaml          # Clone all repositories in the registry
spark repo clone -r <name> -f registry_<folder>.yaml # Clone only the specified repository
spark repo list -f registry_<folder>.yaml           # List the repositories in the registry
```

Registry file format:

```yaml
# Project registry
# Synced by spark repo scan

projects:
    - name: spark-cli
      repo: https://github.com/variableway/spark-cli.git
      path: tooling/spark-cli
      desc: Spark CLI tool
```

#### `spark repo scan [folder-name]`

Recursively scan the directory, discover Git repositories that have an `origin` remote, and write them to `registry_<folder>.yaml` in the current directory. Hidden directories and `node_modules`/`venv`/`.venv`/`__pycache__`/`dist`/`build` are skipped; SSH URLs are normalized to the HTTPS form for storage; repeated scans are merged with the existing registry (matched first by `path`, then by `repo` URL, keeping the old `name`/`desc`, deleting stale entries whose directories no longer exist, and appending newly discovered repositories).

#### `spark repo clone`

Clone the repositories from the registry file into the folder directory (the directory name is derived from `registry_<folder>.yaml` as `<folder>`). It skips repositories that already have a `.git` or whose directory already exists; it runs `git clone <repo> <target>` one by one; at the end it prints the `cloned / skipped / failed` statistics and returns an error when `failed > 0`.

| Option | Description |
|------|------|
| `-r, --repo` | Clone only the repository with the given name (omit to clone all) |
| `-f, --file` | Registry file (required) |

#### `spark repo list`

List the repositories in the registry file, printing `name<TAB>repo<TAB>path` per line; when the registry is empty it prints `No repositories in registry.`.

| Option | Description |
|------|------|
| `-f, --file` | Registry file (required) |

---

### `spark script` — Script Management

```bash
spark script list
spark script run <script-name> [args...]
```

#### `spark script list`
List all available scripts, grouped by source (`spark.scripts` in `~/.spark.yaml` and the `scripts/` directory).

#### `spark script run`
Search for scripts in this order:
1. `spark.scripts` in `~/.spark.yaml`
2. Script files in the current directory (configurable via `--scripts-dir` or `spark.scripts_dir`, default `scripts/`)

Supported script types (identified by extension): `.sh` `.bash` `.zsh` `.py` `.rb` `.pl` `.ps1` `.bat` `.cmd`

Built-in script examples:
- `copy-template.sh`
- `list-dirs.sh`

---

### `spark skill` — AI Skill Management

Find and sync AI agent skills (`SKILL.md` directories).

```bash
spark skill list                    # List all discovered skills
spark skill list --json             # JSON output
spark skill sync <target-dir>       # Copy all skills to the target directory
spark skill sync <target-dir> --clear  # Clear the target directory, then copy
```

Discovery locations (deduplicated by skill name, project > global > builtin):

- `<cwd>/.mimocode/skills/`, `.mimocode/skill/`, `.agents/skills/`
- `~/.claude/skills/`, `~/.agents/skills/`, `~/.mimocode/skills/`
- `~/.local/share/mimocode/builtin_skills/<version>/skills/` (the newest version wins when several exist)

The `name`/`description` in the YAML frontmatter of SKILL.md are parsed, falling back to the directory name when they are absent.

---

### `spark hub` — Project Hub (Collections Registration)

Scan local Git repositories and generate registration information in the innate-apps registry format (`registry/apps.json`).

```bash
spark hub scan <path>                              # Scan the directory, output JSON
spark hub scan <path> -o registry/apps.json        # Write to a file
spark hub scan <path> --merge registry/apps.json   # Merge with the existing registration file
spark hub scan <path> --skip-api                   # Skip the GitHub API
spark hub scan <path> --deep                       # Include nested repositories
```

| Option | Description |
|------|------|
| `-o, --output` | Output file path (default stdout) |
| `--merge` | Merge with the existing registration file, keeping the manual fields (`title`/`category`/`status`/`url`/`description`) |
| `--skip-api` | Skip the GitHub API, use only local git information |
| `--deep` | Include nested repositories (default: top-level directories only) |
| `--category` | Set the category for newly discovered entries (`base`/`app`/`reference`) |

Merge behavior: manual fields are preserved, automatic fields are refreshed (`repo`/`local_path`/`visibility`/`language`),
existing entries that did not appear in the scan are preserved (e.g. the `../base/` base framework), and newly
discovered repositories are appended. Setting `GITHUB_TOKEN` raises the API rate limit.

---

### `spark magic` — System Utilities

```bash
spark magic clean                  # Clean node_modules and .venv
spark magic copy-config            # Deploy the built-in nvim + ghostty templates
spark magic flush-dns              # Flush DNS (macOS/Windows/Linux)
spark magic pip {list,use,current}
spark magic go {list,use,current}
spark magic node {list,use,current}
```

#### `spark magic clean`
Recursively clean all `node_modules` and `.venv` directories under `repo-path` (or `.`); it skips recursion when it encounters a `.git` subdirectory.

```bash
spark magic clean                  # Clean both by default
spark magic clean -m node          # node_modules only
spark magic clean -m python        # .venv only
```

| Option | Description |
|------|------|
| `-m, --mode` | `node` or `python` (default: clean both) |

#### `spark magic copy-config [<user@host:path>]`
Deploy the nvim and ghostty templates that are bundled into the binary at build time via `embed.FS` to the target location. It prefers `rsync` and falls back to `cp` when it is missing.

```bash
spark magic copy-config                                # Deploy to the local ~/.config/{nvim,ghostty}
spark magic copy-config user@192.168.1.100:~/          # Deploy to a remote PC over SSH
spark magic copy-config /mnt/usb/backup/               # Deploy to a custom local path
```

The source templates live in `internal/templates/dotfiles/` and are embedded at build time via `//go:embed`.

#### `spark magic flush-dns`
Select the flush command automatically according to the operating system:
- macOS: `sudo dscacheutil -flushcache` + `sudo killall -HUP mDNSResponder`
- Windows: `ipconfig /flushdns`
- Linux: tries `systemctl restart systemd-resolved`, `service nscd restart`, `service dnsmasq restart`, `rndc flush` in order

#### `spark magic pip {list,use,current}`
Switch the pip mirror source; supported: `default` / `tsinghua` / `aliyun` / `douban` / `ustc` / `tencent`. The configuration is written to the `[global].index-url` of `~/.pip/pip.conf`, and `trusted-host` is set as well.

#### `spark magic go {list,use,current}`
Switch the Go module proxy; supported: `default` / `aliyun` / `tsinghua` / `goproxy` / `ustc` / `nju`. Set via `go env -w GOPROXY=...`.

#### `spark magic node {list,use,current}`
Switch the npm registry; supported: `default` / `taobao` / `aliyun` / `tencent` / `huawei` / `ustc`. Set via `npm config set registry <url>`.

---

### `spark docs` — Documentation Management

```bash
spark docs init                    # Create the docs directory structure
spark docs site                    # Initialize the docmd site configuration
```

| Option (shared) | Description |
|------|------|
| `--root` | Project root directory (default `.`) |

#### `spark docs init`
Create the standard structure (skipping directories/files that already exist):

```
docs/
├── analysis/
├── features/
├── quick-start/
├── spec/
├── tips/
├── usage/
├── index.md
└── README.md
```

#### `spark docs site`
Automatically detect the project title and the GitHub Pages URL from `git remote get-url origin` and write them into `docmd.config.js`; if `docmd` is not installed it is installed globally via `npm install -g @docmd/core`; when `package.json` is missing it is initialized via `npm init -y`; then `npm install` is executed.

---

### `spark witr` — Process Diagnostics

A diagnostic tool for why a process is running, from `internal/witr/app`:

```bash
spark witr nginx
spark witr --pid 1234
spark witr --port 8080
spark witr --file /var/lib/dpkg/lock
spark witr --container redis
spark witr nginx --tree
spark witr nginx --env
spark witr nginx --json
```

| Option | Description |
|------|------|
| `--pid` | Find by PID (repeatable) |
| `--port` / `-o` | Find by port (repeatable) |
| `--file` / `-f` | Find by file (repeatable) |
| `--container` / `-c` | Find by container name (repeatable) |
| `--tree` / `-t` | Show the process ancestor tree |
| `--env` | Show the process environment variables |
| `--json` | JSON output |
| `--short` / `-s` | Single-line short output |
| `--warnings` | Show only suspicious environment/arguments/parent processes |
| `--verbose` | Extended information (memory, I/O, fds) |
| `--exact` / `-x` | Exact match |
| `--no-color` | Disable colors |

Subpackages: `launchd`, `output`, `pipeline`, `proc`, `source`, `target`, `tools`, `tui`, `version`; the model lives in `pkg/witr/model`.

---

## Build & Test

### Build Commands

> Note: `go.sum` must be committed to the repository (it must not be added to `.gitignore`), otherwise after a fresh
> clone `go build` fails with "missing go.sum entry", which makes the Windows/macOS/Linux builds unstable.

```bash
make build          # Compile to bin/ + stamp version/commit/date ldflags + install to ~/.local/bin/spark
make build-linux    # Cross-compile Linux amd64 (bin/spark_linux)
make build-darwin   # Cross-compile macOS amd64 (bin/spark_darwin)
make clean          # Remove the binaries and build artifacts
make install        # Same as build
make install-only   # Only copy the existing binary to ~/.local/bin (does not touch the source)
make verify-install # Compare the sha256/size/mtime of ~/.local/bin/spark with the source spark.exe
```

Equivalent commands for `task` (Taskfile):

```bash
task build          # Equivalent to make build (artifact in bin/; on Windows both spark.exe and spark go to ~/.local/bin)
task install        # Equivalent to task build
task install-binary # Only copy the existing spark.exe to ~/.local/bin (does not touch the source)
task verify-install # Equivalent to make verify-install
task build:windows        # Cross-compile Windows amd64 (bin/spark_windows.exe)
task build:windows:arm64  # Cross-compile Windows arm64 (bin/spark_windows_arm64.exe)
task build:all            # Cross-compile for all platforms (all artifacts go into bin/, clean deletes bin/)
```

**Windows installation principle**: both `spark.exe` and the extension-less `spark` exist under `~/.local/bin`, because
bash matches the latter first; the install step atomically refreshes both files and immediately prints the sha256
comparison to avoid a stale shadow copy.

**Self-check**:

```bash
spark version       # -> spark v0.3.3 / commit xxx / build date ...
spark --version     # -> spark version v0.3.3
```

### Documentation Site Build (Node Stack)

The documentation site is an independent Node project (`package.json` + `pnpm` + docmd), built in parallel with the Go binary:

```bash
pnpm install        # Dependencies are hard-linked from the pnpm store (on Windows the store can point at D:\.pnpm-store)
pnpm build          # docmd build -> site/ (zh at the root, en at /en/)
pnpm dev            # Local preview
```

See the complete build guide (Go binary / documentation site / Bun single binary / Windows pnpm global paths) in
[`usage/how-to-build.md`](usage/how-to-build.md).
pnpm global paths (to save space on the C drive): `store-dir=D:\.pnpm-store`, `global-dir=D:\pnpm\global`,
`global-bin-dir=D:\pnpm\bin`, `PNPM_HOME=D:\pnpm`.
Also: Bun's `bun build --compile` can, like Go, produce a single binary from TS (e.g. `innate-fe-cli`);
see section 3 of how-to-build for details.

### Test Commands

```bash
make test           # go test ./... -v
make test-bdd       # ginkgo -v ./internal/...
make test-report    # Full ginkgo run + generate the HTML report reports/test-report.html
make lint           # go vet ./...
```

How `test-report` works: the Ginkgo CLI runs `./...` with `--output-dir=reports --json-report=ginkgo-report.json`
(note that `--output-dir` must be used to pre-create the directory — Ginkgo internally uses `path.Dir` instead of
`filepath.Dir` to create directories, so on Windows writing `reports/xxx.json` directly fails because the directory
does not exist), and then `tools/testreport` renders the JSON into a self-contained HTML page (summary cards,
suite/case tables, failure details, filtering by status + text search). The renderer lives in `internal/testreport`
(including BDD tests).

Running a single test:

```bash
go test ./internal/git/... -v -run TestUpdateRepository
```

---

## Configuration File

The configuration file lives at `~/.spark.yaml` and is migrated automatically from the legacy `~/.monolize.yaml`. See [`.spark.yaml.example`](../../.spark.yaml.example) for a complete example:

```yaml
repo-path:
  - ~/workspace
  - ~/projects
  - ./repos

git:
  username: your-name              # Default for spark git config / init
  email: your-email@example.com
  scanner:
    db: ~/.innate/feeds.db         # Default SQLite path for spark git scan

gitlab:
  host: gitlab.example.com         # Optional: scope the automatically discovered credentials to this instance (without it they are sent to any instance)
  token: glpat-xxxx                # GitLab Token for spark git batch-clone (= --token = GITLAB_TOKEN)
                                   # Requires the read_api scope; cloning private repositories also requires read_repository
                                   # Takes precedence over the environment variable; a stale invalid token takes precedence over GITLAB_TOKEN

github-owner: your-github-username # Default for spark git init --owner

default_branch: main
auto_commit: true
```

Configuration keys and where they are actually read (`viper.GetString` / `viper.GetStringSlice`):

| Config key | Read by |
|--------|--------|
| `repo-path` (global `-p, --path`) | `cmd/git/update.go`, `push_all.go`, `magic/clean.go`, `gitcode.go` |
| `git.username` / `git.email` | `cmd/git/config.go`, `cmd/git/init.go` |
| `git.scanner.db` (`--db`) | `cmd/git/scan.go` |
| `gitlab.host` / `gitlab.token` (`--token`) | `cmd/git/batch_clone.go` |
| `github-owner` | `cmd/git/init.go` |
| `spark.scripts_dir` | `cmd/script/list.go`, `cmd/script/run.go` |

Why the GitLab Token environment variable uses `os.Getenv` instead of `viper.AutomaticEnv()`: viper would map
`gitlab.token` to `GITLAB.TOKEN`, and a shell cannot define a variable name containing `.`; therefore environment
variables always go through an explicit `os.Getenv`.

Configuration key naming conversion: snake_case is used in `~/.spark.yaml`, associated with persistent flags via
`viper.BindPFlag`. Struct tags still habitually use camelCase. Script-related:

```yaml
spark:
  scripts_dir: scripts            # Search directory for spark script run
  scripts:
    - name: hello
      content: |
        #!/bin/bash
        echo "Hello, World!"
    - name: deploy
      content: |
        #!/bin/bash
        echo "Deploying to $1 environment..."
```

Configuration key precedence: `--config` flag → `$HOME/.spark.yaml` → environment variables (`viper.AutomaticEnv`).

---

## Assistant Guidelines Reference

This project keeps a highly cohesive, loosely coupled Go code style. When continuing development, please:

1. **Code style**
   - Follow the Go standard code conventions
   - Do not add comments (unless explicitly requested)
   - Use the existing library and tool patterns (Cobra + Viper + PTerm + Ginkgo/Gomega)

2. **Testing requirements**
   - New features must add BDD-style tests
   - Test files end with `_test.go`, and the test suite (`*_suite_test.go`) registers the Ginkgo runner
   - Test coverage: `config` / `git` (incl. `scanner`) / `script` / `github` / `gitlab` / `witr/output`
   - Pure functions under `cmd/` (such as `resolveGitLabToken`, `parseRepoSlug`) can be covered directly with standard `testing`

3. **Build consistency**
   - Prefer updating the `Makefile` to keep the build consistent
   - Ensure the `.vscode` configuration stays generic
   - Run `make lint` and `make test` before committing

4. **Documentation updates**
   - When adding/modifying commands, update the corresponding documents in `docs/zh/usage/` and `docs/en/usage/` together with this `AGENTS.md`
   - `docs/zh/Agents.md` and `docs/en/Agents.md` are the in-site mirrors and must be kept up to date as well
   - Keep the `AGENTS.md` command hierarchy consistent with the actual `cmd/` / `internal/` implementation
   - The documentation is primarily Chinese UI; command lines / code identifiers stay in English
   - The documentation site `docs/` already supports Chinese and English (`i18n.default: 'zh'` in `docmd.config.js`):
     Chinese is the default locale rendered at the root URL; the English mirror is at `/en/`
     New/modified documents must update `docs/zh/...` and `docs/en/...` at the same time, and keep
     `docs/zh/navigation.json` / `docs/en/navigation.json` consistent with the i18n `locales` configuration
     docmd automatically falls back to the default locale when a page is missing in a non-default locale,
     so this behavior can be relied on temporarily before the translation is complete
