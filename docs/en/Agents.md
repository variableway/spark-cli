# AGENTS.md

This document records the key tasks that AI assistants have executed in this project, the system integration work, and the complete feature reference.
The [`AGENTS.md`](../../AGENTS.md) and [`CLAUDE.md`](../../CLAUDE.md) at the repository root are the authoritative sources; this page is the site mirror.

## Project Overview

**Spark** is a CLI tool (`module spark`, binary `spark`) for managing multiple Git repositories and scripts, with practical system utilities bundled in. Built with **Cobra** (CLI), **Viper** (config), **PTerm** + **Bubble Tea** (terminal UI), and **Ginkgo/Gomega** for BDD testing.

Core capabilities:

1. **Multi-repo update** — batch-update multiple Git repositories to the latest version (SSH supported)
2. **Repo cloning** — `git clone` clones GitHub repositories via `gh repo clone` (SSH by default); `batch-clone` supports GitHub orgs/users and GitLab groups/users
3. **Submodule management** — `submodule add` (URL or local directory), `submodule init`, `submodule status`, `submodule ensure-ssh`, `git sync`
4. **Git user configuration** — `spark git config` configures the repository's Git user info
5. **Gitcode remote management** — `spark git gitcode` adds a Gitcode remote address
6. **Org status** — `spark git update-org-status` writes the org repository list into the README
7. **Repo scanning** — `spark git scan` scans repositories in a directory and saves them to SQLite
8. **Repo pushing** — `spark git push-all` batch-commits and pushes all changes
9. **Issue creation** — `spark git issues` creates GitHub Issues from Markdown/task files
10. **Script management** — discover and run scripts from `~/.spark.yaml` or the `scripts/` directory
11. **System utilities** — `spark magic` provides DNS cache flushing, `node_modules`/`.venv` cleanup, pip/npm/go mirror switching, and Neovim/Ghostty template deployment
12. **Docs management** — `spark docs init`/`spark docs site` (docmd site initialization)
13. **Process diagnostics** — `spark witr` (Why Is This Running), inspecting why a process or port is running
14. **Repo management** — `spark repo` manages multiple GitHub repositories in a directory via a registry file (`scan`/`clone`/`list`), replacing submodules

## Tech Stack

| Layer | Technology |
|------|------|
| Language | Go 1.27+ (see `go.mod`) |
| CLI framework | [Cobra](https://github.com/spf13/cobra) + [Viper](https://github.com/spf13/viper) |
| Terminal UI | [pterm](https://github.com/pterm/pterm) + [Bubble Tea](https://github.com/charmbracelet/bubbletea) |
| Testing | [Ginkgo](https://github.com/onsi/ginkgo) + [Gomega](https://github.com/onsi/gomega) (`internal/`), standard `testing` (`cmd/`) |
| Build | Makefile + Taskfile (Windows / Linux / macOS) |
| Docs | docmd (bilingual Chinese/English) |

## Project Structure

```
spark-cli/
├── main.go                  # Entry point (calls cmd.Execute())
├── cmd/
│   ├── root.go              # Root command, global flags, config loading and .monolize.yaml auto-migration
│   ├── version.go           # spark version
│   ├── witr.go              # Bridge to internal/witr/app.Root()
│   ├── git/                 # init/clone/update/submodule/sync/gitcode/config/url/
│   │                        # batch-clone/issues/update-org-status/push-all/scan
│   ├── repo/                # Registry-file-driven repo management (scan/clone/list)
│   ├── magic/               # clean/copy-config/flush-dns/pip/go/node
│   ├── script/              # list/run
│   └── docs/                # init/site
├── internal/
│   ├── config/              # Configuration loading
│   ├── git/                 # Git operation wrappers (finder/updater/init/submodule/pusher + scanner)
│   ├── github/              # GitHub API (org / markdown issue)
│   ├── gitlab/              # GitLab API (batch-clone: URL parsing, token sources, nested groups)
│   ├── registry/            # Scan/read-write/merge logic for the repo command
│   ├── script/              # Script discovery and execution
│   ├── templates/           # Embedded dotfiles (nvim + ghostty)
│   └── witr/                # Why-Is-This-Running process diagnostics engine
├── pkg/witr/model/          # Shared witr data model
├── docs/{zh,en}/            # docmd site (Chinese is the default locale, English mirror at /en/)
├── scripts/                 # Default script directory + install/verify scripts
├── Makefile / Taskfile.yml  # Build and test entry points
└── docmd.config.js          # docmd config (i18n.default: zh)
```

## Complete CLI Command Reference

### Global options

| Option | Description |
|------|------|
| `--config` | Config file path (default: `$HOME/.spark.yaml`) |
| `-p, --path` | Directory paths to scan for repos (StringSlice, default `["."]`, bound to viper key `repo-path`) |

Config initialization (`initConfig` + `migrateOldConfig`): `--config` takes precedence; at startup, if the legacy
`~/.monolize.yaml` exists and `~/.spark.yaml` does not, it is automatically renamed/migrated; `viper.AutomaticEnv()`
enables environment-variable overrides.

---

### `spark git` — Git repository management

```bash
spark git init [--owner <o>] [-r <name>] [--private] [--skip-gh]   # Initialize and create the GitHub remote
spark git clone <url-or-slug> [directory] [-- <git-args>]          # gh repo clone (SSH by default)
spark git update [-p <dir>] [--ssh]                                # Scan and update all repos
spark git submodule add <path-or-url> [-n <name>]                  # Add a submodule
spark git submodule init [-r] [-j <n>] [--name <n>]                # Initialize submodules
spark git submodule status [-r]                                    # Submodule status
spark git submodule ensure-ssh                                     # HTTPS → SSH rewrite
spark git sync [repo-path] [-r]                                    # Sync submodules to latest
spark git gitcode [-p <dir>] [--url <url>]                         # Add a Gitcode remote
spark git config [repo-path] [--username <u>] [--email <e>]        # Configure the Git user
spark git url [repo-path]                                          # Print the remote URL
spark git batch-clone <account-or-url> [flags]                     # Batch-clone a GitHub/GitLab account
spark git issues (-d <dir> | -f <file>) [-r <owner/repo>] [-l ...] [--dry-run]
spark git update-org-status <org> [--dry-run] [-o <path>] [--update-dot-github] [--section <n>] [--skip-push]
spark git push-all [-p <dir>]                                      # commit + push all repos
spark git scan [folder-path] [-d <db>] [--skip-api]                # Scan and write to SQLite
```

`spark git clone` accepts four input forms: `https://github.com/owner/repo.git`, `git@github.com:owner/repo.git`,
`github.com/owner/repo`, and `owner/repo`; arguments after `--` are passed through to `git clone`.

`spark git batch-clone` options:

| Option | Description |
|------|------|
| `--ssh` | Use SSH URLs (GitHub `git@github.com:...`, GitLab `git@<host>:...`) |
| `--include` / `--exclude` | Name include/exclude patterns (comma-separated) |
| `--include-forks` | Include forked repos |
| `-o, --output` | Output directory (default `.`) |
| `--token` | GitLab private token (explicit; not restricted by `gitlab.host`) |

GitLab implementation notes:

- Scheme-less input is supported (`gitlab.com/gitlab-com/gl-infra`); `internal/gitlab.ParseGitLabURL` prepends `https://` automatically
- API v4 group paths must be URL-encoded (`group/sub` → `group%2Fsub`), see `internal/gitlab.escapePath`;
  combined with `include_subgroups=true` it recurses into subgroups at any depth
- Clone paths on disk follow the namespace-relative path (`internal/gitlab.ProjectRelativePath`),
  e.g. `observability/tenant-observability/argocd-tenant-plugin`, so same-named projects in subgroups do not overwrite each other
- Token precedence: `--token` > `gitlab.token` > `GITLAB_TOKEN` > `GITLAB_PRIVATE_TOKEN`,
  resolved by `cmd/git.resolveGitLabToken`, which prints `Using token from: ...`
- `gitlab.host` scopes automatically discovered credentials to that instance; on mismatch it prints
  `Ignoring ...: it is scoped to ...` and skips the credential; `--token` is not restricted
- Unauthenticated access to a private instance/private group returns 404 rather than 401, so error messages distinguish
  "credentials rejected" / "no credentials provided" / "path does not exist"

---

### `spark repo` — Repository management

Manages multiple GitHub repositories in a directory via a registry file (replacing submodules):

```bash
spark repo scan [folder-name]                        # Scan the directory and write registry_<folder>.yaml
spark repo clone -f registry_<folder>.yaml           # Clone every repo in the registry
spark repo clone -r <name> -f registry_<folder>.yaml # Clone only the specified repo
spark repo list -f registry_<folder>.yaml            # List the repos in the registry
```

| Option | Command | Description |
|------|------|------|
| `-r, --repo` | `clone` | Clone only the named repo (omit to clone all) |
| `-f, --file` | `clone` / `list` | Registry file (required) |

---

### `spark script` — Script management

```bash
spark script list
spark script run <script-name> [args...]
```

Search order: `spark.scripts` in `~/.spark.yaml` → script files under `spark.scripts_dir` (default `scripts/`).
Supported extensions: `.sh` `.bash` `.zsh` `.py` `.rb` `.pl` `.ps1` `.bat` `.cmd`.

---

### `spark magic` — System utilities

```bash
spark magic clean [-m node|python]     # Clean node_modules / .venv
spark magic copy-config [<user@host:path>]  # Deploy the embedded nvim + ghostty templates
spark magic flush-dns                  # Flush DNS (macOS/Windows/Linux)
spark magic pip {list,use,current}     # default/tsinghua/aliyun/douban/ustc/tencent
spark magic go {list,use,current}      # default/aliyun/tsinghua/goproxy/ustc/nju
spark magic node {list,use,current}    # default/taobao/aliyun/tencent/huawei/ustc
```

The `copy-config` templates come from `internal/templates/dotfiles/` and are embedded at build time via `//go:embed`;
it prefers `rsync` and falls back to `cp` when unavailable.

---

### `spark docs` — Documentation management

```bash
spark docs init [--root <dir>]   # Create the docs directory structure
spark docs site [--root <dir>]   # Initialize the docmd site config
```

---

### `spark witr` — Process diagnostics

```bash
spark witr nginx
spark witr --pid 1234 --tree
spark witr --port 8080
spark witr --file /var/lib/dpkg/lock
spark witr --container redis --json
```

| Option | Description |
|------|------|
| `--pid` | Find by PID (repeatable) |
| `--port` / `-o` | Find by port (repeatable) |
| `--file` / `-f` | Find by file (repeatable) |
| `--container` / `-c` | Find by container name (repeatable) |
| `--tree` / `-t` | Show the process ancestor tree |
| `--env` | Show process environment variables |
| `--json` | JSON output |
| `--short` / `-s` | Single-line short output |
| `--warnings` | Show only suspicious environment/arguments/parent processes |
| `--verbose` | Extended information (memory, I/O, fds) |
| `--exact` / `-x` | Exact match |
| `--no-color` | Disable colors |

---

### `spark version`

Prints version / commit / build date (injected by the Makefile's ldflags into `internal/witr/version`).

## Configuration File

The config file lives at `~/.spark.yaml` and is automatically migrated from the legacy `~/.monolize.yaml`. See `.spark.yaml.example` for a complete example:

```yaml
repo-path:
  - ~/workspace
  - ~/projects

git:
  username: your-name
  email: your-email@example.com
  scanner:
    db: ~/.innate/feeds.db         # Default SQLite path for spark git scan

gitlab:
  host: gitlab.example.com         # Optional: scope automatically discovered credentials to this instance
  token: glpat-xxxx                # Requires read_api; cloning private repos also requires read_repository

github-owner: your-github-username # Default for spark git init --owner

spark:
  scripts_dir: scripts
  scripts:
    - name: hello
      content: |
        #!/bin/bash
        echo "Hello, World!"
```

| Config key | Read by |
|--------|--------|
| `repo-path` (global `-p, --path`) | `cmd/git/update.go`, `push_all.go`, `magic/clean.go`, `gitcode.go` |
| `git.username` / `git.email` | `cmd/git/config.go`, `cmd/git/init.go` |
| `git.scanner.db` (`--db`) | `cmd/git/scan.go` |
| `gitlab.host` / `gitlab.token` (`--token`) | `cmd/git/batch_clone.go` |
| `github-owner` | `cmd/git/init.go` |
| `spark.scripts_dir` | `cmd/script/list.go`, `cmd/script/run.go` |

The GitLab token environment variable uses `os.Getenv` rather than `viper.AutomaticEnv()`: viper would map
`gitlab.token` to `GITLAB.TOKEN`, and shells cannot define variable names containing `.`.

## Build & Test

```bash
make build          # Compile + stamp version/commit/date ldflags + install to ~/.local/bin/spark
make build-linux    # Cross-compile Linux amd64
make build-darwin   # Cross-compile macOS amd64
make test           # go test ./... -v
make test-bdd       # ginkgo -v ./internal/...
make lint           # go vet ./...
make clean          # Clean build artifacts
```

`Taskfile.yml` provides equivalent commands: `task build` / `task install` / `task install-binary` / `task verify-install`.

Running a single test:

```bash
go test ./internal/git/... -v -run TestUpdateRepository
```

## Assistant Guidelines Reference

1. **Code style**: follow standard Go conventions; do not add comments (unless explicitly requested); reuse existing libraries and patterns (Cobra + Viper + PTerm + Ginkgo/Gomega)
2. **Testing requirements**: new features must include tests; use Ginkgo/Gomega BDD style for `internal/`, and standard `testing` for pure functions under `cmd/`
3. **Build consistency**: prefer updating the `Makefile`; keep `.vscode` configuration general-purpose; run `make lint` and `make test` before committing
4. **Documentation updates**: keep `docs/zh/**` and `docs/en/**`, `docs/{zh,en}/navigation.json`, `docs/{zh,en}/Agents.md`, and the repository-root `AGENTS.md` and `CLAUDE.md` in sync
