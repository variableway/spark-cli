# Spark CLI

A CLI tool for daily dev automation and AI skill integration.

**Why Spark?** Deterministic tasks (file scaffolding, mirror switching, config management) can be automated by CLI to save token cost. Spark also provides a CLI app backend for AI skills — so agents can call `spark` instead of burning LLM tokens on repetitive operations.

> Most code is AI-generated, all inspired by real daily workflows.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Go 1.25 |
| CLI Framework | Cobra + Viper |
| Config | `~/.spark.yaml` |
| TUI | PTerm + Bubble Tea |
| Testing | Ginkgo / Gomega (BDD) |
| Docs | docmd |

## Architecture

```
main.go → cmd.Execute()
├── cmd/                    Cobra command definitions
│   ├── git/                Git repo management
│   ├── magic/              System utilities (DNS, mirrors, clean, dotfiles)
│   ├── script/             Script management
│   ├── docs/               Documentation scaffolding
│   ├── task.go             Task workflow commands
│   └── witr.go             Process diagnostics
├── internal/               Business logic by domain
│   ├── config/             Config loading & migration
│   ├── git/                Core git operations (+ scanner)
│   ├── github/             GitHub API
│   ├── gitlab/             GitLab API (batch-clone)
│   ├── script/             Script discovery & execution
│   ├── task/               Task dispatch/sync/issue CRUD
│   ├── templates/          Embedded dotfiles (nvim, ghostty)
│   ├── tui/                Shared terminal UI components
│   └── witr/               Why-Is-This-Running engine
├── docs/                   Documentation (docmd)
└── scripts/                User-defined automation scripts
```

## Build

```bash
make build          # Build + install to ~/.local/bin/spark
make verify-install # Compare ~/.local/bin/spark sha256 against source
make build-linux    # Cross-compile Linux amd64
make build-darwin   # Cross-compile macOS amd64
make test           # Run all unit tests
make test-bdd       # BDD-style tests (Ginkgo)
```

验证安装的二进制确实是最新的：
```bash
spark version       # -> spark v0.3.2 / commit 1ef84d7 / build date ...
spark --version     # -> spark version v0.3.2
```
make lint           # Static analysis (go vet)
make clean          # Remove binary
```

Run a single test:
```bash
go test ./internal/git/... -v -run TestFunctionName
```

## Commands

### Global Flags

| Flag | Description |
|------|-------------|
| `--config` | Config file (default `~/.spark.yaml`) |
| `-p, --path` | Directory containing git repos |

---

### spark git — Git Repository Management

| Command | Description |
|---------|-------------|
| `spark git update [--ssh]` | Update all repos to latest version |
| `spark git clone <url-or-slug> [dir]` | Clone a GitHub repo via `gh` (default SSH) |
| `spark git submodule add/init/status/ensure-ssh` | Submodule management |
| `spark git sync [--recursive]` | Sync all submodules to latest |
| `spark git gitcode` | Add Gitcode remote to repos |
| `spark git init [--owner] [--skip-gh]` | Initialize repo and create GitHub remote |
| `spark git config [--username --email]` | Configure git user for repo |
| `spark git url [repo-path]` | Get remote URL of repository |
| `spark git batch-clone <account-or-url> [--ssh] [--token] [-o <dir>]` | Clone all repos from GitHub or GitLab |
| `spark git update-org-status <org>` | Update org README with repo list |
| `spark git issues (-d <dir> \| -f <file>)` | Create GitHub issues from markdown/tasks |
| `spark git push-all` | Commit and push changes across repos |
| `spark git scan [path] [--db] [--skip-api]` | Scan repos and save to SQLite |

---

### spark task — Task Management

| Command | Description |
|---------|-------------|
| `spark task init` | Initialize task directory structure |
| `spark task list` | List all tasks and issues |
| `spark task create <name> [--content]` | Create issue file |
| `spark task delete <name> [--force]` | Delete issue file |
| `spark task impl <name>` | Implement issue via kimi CLI |
| `spark task dispatch [name] [--dest]` | Dispatch task to workspace |
| `spark task sync [name] [--work-path]` | Sync task back |

Flags: `--task-dir`, `--owner`, `--work-dir`, `--tui`

---

### spark magic — System Utilities

| Command | Description |
|---------|-------------|
| `spark magic flush-dns` | Flush DNS cache (macOS/Windows/Linux) |
| `spark magic clean [-m node\|python]` | Clean `node_modules` and `.venv` |
| `spark magic copy-config [<target>]` | Deploy bundled nvim + ghostty templates |
| `spark magic pip/go/node {list,use,current}` | Switch pip / Go / npm mirrors |

---

### spark script — Custom Scripts

| Command | Description |
|---------|-------------|
| `spark script list` | List available scripts |
| `spark script run <name> [args...]` | Execute a script |

Scripts sourced from `~/.spark.yaml` (`spark.scripts`) and `scripts/` directory.

---

### spark docs — Documentation

| Command | Description |
|---------|-------------|
| `spark docs init [--root]` | Create standard docs directory structure |
| `spark docs site [--root]` | Initialize docmd site config |

---

### spark witr — Process Diagnostics

| Command | Description |
|---------|-------------|
| `spark witr <name>` | Diagnose why a process is running |
| `spark witr --pid/--port/--file/--container` | Lookup by PID, port, file, or container |

## Configuration

Config file: `~/.spark.yaml`

```yaml
repo-path:
  - /path/to/repos
git:
  username: your-name
  email: your@email.com
  scanner:
    db: ~/.innate/feeds.db
task_dir: /path/to/tasks
github_owner: your-username
work_dir: ./workspace
```

## Related Projects

- [golang-cli-app skill](https://github.com/variableway/fire-skills/tree/main/dev/golang-cli-app) - Go CLI app code templates and best practices (Cobra/Viper/PTerm/Bubble Tea)

## Documentation

Online docs: https://variableway.github.io/spark-cli/

| Path | Content |
|------|---------|
| [docs/usage/](docs/usage/) | Per-command usage guides |
| [docs/analysis/](docs/analysis/) | Architecture & RFC documents |
| [AGENTS.md](AGENTS.md) | AI integration guide |
| [CLAUDE.md](CLAUDE.md) | Claude Code development guide |
| [CHANGELOG.md](CHANGELOG.md) | Release history |
