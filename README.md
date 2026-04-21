# Spark CLI

A CLI tool for daily dev automation and AI skill integration.

**Why Spark?** Deterministic tasks (file scaffolding, mirror switching, config management) can be automated by CLI to save token cost. Spark also provides a CLI app backend for AI skills — so agents can call `spark` instead of burning LLM tokens on repetitive operations.

> Most code is AI-generated, all inspired by real daily workflows.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Go 1.25 |
| CLI Framework | Cobra |
| Config | Viper (`~/.spark.yaml`) |
| TUI | PTerm + Bubble Tea |
| Testing | Ginkgo / Gomega (BDD) |
| Docs | docmd |

## Architecture

```
main.go → cmd.Execute()
├── cmd/                    Cobra command definitions
│   ├── git/                Git repo management commands
│   ├── magic/              System utilities (DNS, mirrors)
│   ├── script/             Script management commands
│   ├── agent.go            AI agent config management
│   ├── agent_profile.go    Agent profile templates
│   └── task.go             Task workflow commands
├── internal/               Business logic by domain
│   ├── agent/              AI agent config (Claude Code, Codex, Kimi, GLM)
│   ├── config/             Config loading & migration
│   ├── git/                Core git operations
│   ├── github/             GitHub API interactions
│   ├── mono/               Mono-repo & submodule management
│   ├── script/             Script discovery & execution
│   ├── task/               Task dispatch/sync/issue CRUD
│   └── tui/                Shared terminal UI components
├── docs/                   Documentation (docmd)
└── scripts/                User-defined automation scripts
```

## Build

```bash
make build          # Build + install to ~/.local/bin/spark
make build-linux    # Cross-compile Linux amd64
make build-darwin   # Cross-compile macOS amd64
make test           # Run all unit tests
make test-bdd       # BDD-style tests (Ginkgo)
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
| `spark git update` | Update all repos to latest version |
| `spark git mono add [-p <path>]` | Add existing repos as submodules |
| `spark git mono sync <mono-path>` | Sync all submodules to latest |
| `spark git gitcode [-p <path>]` | Add Gitcode remote to repos |
| `spark git config [--username --email]` | Configure git user for repo |
| `spark git url [repo-path]` | Get remote URL of repository |
| `spark git batch-clone <account> [--ssh] [--include] [--exclude] [-o <dir>]` | Clone all repos from GitHub org/user |
| `spark git update-org-status <org> [--dry-run] [--update-dot-github] [--section <name>]` | Update org README with repo list |
| `spark git issues [-r <owner/repo>] (-d <dir> \| -f <file>) [--dry-run] [-l <labels>]` | Create GitHub issues from markdown docs/tasks |

---

### spark agent — AI Agent Configuration

| Command | Description |
|---------|-------------|
| `spark agent list` | List supported agents |
| `spark agent view <agent>` | View agent config files |
| `spark agent edit <agent> [index]` | Edit agent config in editor |
| `spark agent reset <agent>` | Reset agent config |
| `spark agent profile list` | List config profiles |
| `spark agent profile add <name> -t <type>` | Add new profile |
| `spark agent profile show <name>` | Show profile config |
| `spark agent profile edit <name> [index]` | Edit profile config |
| `spark agent use <profile> [-p <dir>]` | Apply profile to project |
| `spark agent current [-p <dir>]` | Show active profile |

Supported agents: `claude-code`, `codex`, `kimi`, `glm`

---

### spark task — Task Management

| Command | Description |
|---------|-------------|
| `spark task init` | Initialize task directory structure |
| `spark task list` | List all tasks and issues |
| `spark task create <name> [--content <text>]` | Create issue file |
| `spark task delete <name> [--force]` | Delete issue file |
| `spark task impl <name>` | Implement issue via kimi CLI |
| `spark task dispatch [name] [--dest <path>]` | Dispatch task to workspace |
| `spark task sync [name] [--work-path <path>]` | Sync task back |

Flags: `--task-dir`, `--owner`, `--work-dir`, `--tui`

---

### spark magic — System Utilities

| Command | Description |
|---------|-------------|
| `spark magic flush-dns` | Flush DNS cache (macOS/Windows/Linux) |

#### Mirror Switching (list / use / current)

| Command | Targets |
|---------|---------|
| `spark magic pip [list\|use\|current]` | Python pip mirrors (tsinghua, aliyun, douban, ustc, tencent) |
| `spark magic go [list\|use\|current]` | Go module proxy (aliyun, tsinghua, goproxy, ustc, nju) |
| `spark magic node [list\|use\|current]` | npm registry (taobao, aliyun, tencent, huawei, ustc) |

---

### spark script — Custom Scripts

| Command | Description |
|---------|-------------|
| `spark script list` | List available scripts |
| `spark script run <name> [args...]` | Execute a script |

Scripts sourced from `~/.spark.yaml` (`spark.scripts`) and `scripts/` directory.

## Configuration

Config file: `~/.spark.yaml`

```yaml
repo-path:
  - /path/to/repos
git:
  username: your-name
  email: your@email.com
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
| [AGENTS.md](AGENTS.md) | AI agent integration guide |
| [CLAUDE.md](CLAUDE.md) | Claude Code development guide |
