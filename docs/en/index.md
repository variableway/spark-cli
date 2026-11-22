---
title: Spark CLI
description: A CLI tool for daily dev automation and AI skill integration
---

# Spark CLI

A CLI tool for daily dev automation and AI skill integration.

**Why Spark?** Deterministic tasks (file scaffolding, mirror switching, config management) can be automated by CLI to save token cost. Spark also provides a CLI app backend for AI skills — so agents can call `spark` instead of burning LLM tokens on repetitive operations.

> Most code is AI-generated, all inspired by real daily workflows.

## Watch

<video src="../assets/video/spark-cli-16x9.mp4" width="100%" controls preload="metadata" poster="../assets/video/spark-cli-16x9.jpg"></video>

52 seconds. Everything on screen is real: the terminal output is recorded from an
actual `spark --help` run, the version and commit come from `spark version`, and the
command tree is the real one. Subtitles are burned in (Chinese + English).

Other sizes: [9:16 for social](/media/) · [1:1 for the site hero](/media/)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Go 1.27 (see `go.mod`) |
| CLI Framework | Cobra |
| Config | Viper (`~/.spark.yaml`) |
| TUI | PTerm + Bubble Tea |
| Testing | Ginkgo / Gomega (BDD, `internal/`) + standard `testing` (`cmd/`) |
| Build | Makefile + Taskfile |
| Docs | docmd (bilingual zh/en) |

## Architecture

```
main.go → cmd.Execute()
├── cmd/                    Cobra command definitions
│   ├── git/                Git repo management commands
│   ├── repo/               Registry-file repo management (scan/clone/list)
│   ├── magic/              System utilities (DNS, mirrors, clean, copy-config)
│   ├── script/             Script management commands
│   ├── docs/               Documentation scaffolding commands
│   ├── version.go          spark version
│   └── witr.go             Process diagnostics bridge
├── internal/               Business logic by domain
│   ├── config/             Config loading & migration
│   ├── git/                Core git operations (+ scanner/)
│   ├── github/             GitHub API interactions
│   ├── gitlab/             GitLab API interactions (batch-clone)
│   ├── registry/           registry file scan/read/merge
│   ├── script/             Script discovery & execution
│   ├── templates/          Embedded nvim/ghostty dotfiles
│   └── witr/               Why-Is-This-Running engine
├── pkg/witr/model/         Shared witr data model
├── docs/zh, docs/en/       Bilingual docmd site
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
make lint           # Static analysis (go vet)
make clean          # Remove binary
```

Verify the installed binary is current:

```bash
spark version       # -> spark v0.3.3 / commit 1ef84d7 / build date ...
spark --version     # -> spark version v0.3.3
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
| `spark git clone <url-or-slug> [dir] [-- <git-args>]` | Clone a GitHub repo via `gh repo clone` (SSH by default) |
| `spark git update [--ssh]` | Update all repos to latest version (`--ssh` forces SSH) |
| `spark git gitcode [-p <path>]` | Add Gitcode remote to repos |
| `spark git config [--username --email]` | Configure git user for repo |
| `spark git url [repo-path]` | Get remote URL of repository |
| `spark git batch-clone <account-or-url> [--ssh] [--include] [--exclude] [--include-forks] [-o <dir>] [--token]` | Clone all repos from a GitHub org/user or a GitLab group/user |
| `spark git update-org-status <org> [--dry-run] [--update-dot-github] [--section <name>]` | Update org README with repo list |
| `spark git issues [-r <owner/repo>] (-d <dir> \| -f <file>) [--dry-run] [-l <labels>]` | Create GitHub issues from markdown docs/tasks |
| `spark git push-all [-p <path>]` | Commit and push all changes in repositories |
| `spark git scan [folder-path] [-d <db>] [--skip-api]` | Scan git repos and save to SQLite |


---

### spark hub — References and app collections

Two catalogs, used differently. `registry` tracks a references directory. `collections` registers apps you develop.

| Command | Description |
|---------|-------------|
| `spark hub registry scan [folder]` | Scan references into `registry_<folder>.yaml` |
| `spark hub registry list -f <registry>` | List repositories in a registry |
| `spark hub registry clone -f <registry> [-r <name>]` | Clone repositories from a registry |
| `spark hub registry clone-registry <registry> [--out <folder>] [--dry-run]` | Clone only entries missing on disk |
| `spark hub collections scan [path] [-o <file>]` | Register apps you develop as `registry/apps.json` |
| `spark hub collections scan --merge <file> [--skip-api] [--deep] [--category <c>]` | Merge the app catalog and keep curated fields |

---

### spark docs — Documentation

| Command | Description |
|---------|-------------|
| `spark docs init [--root]` | Create the standard docs directory structure |
| `spark docs site [--root]` | Initialize the docmd site configuration |

---

### spark version — Version Info

| Command | Description |
|---------|-------------|
| `spark version` | Print version / commit / build date |

---

### spark magic — System Utilities

| Command | Description |
|---------|-------------|
| `spark magic flush-dns` | Flush DNS cache (macOS/Windows/Linux) |
| `spark magic clean [-m node\|python]` | Clean node_modules and .venv directories |

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

---

### spark witr — Process Inspector

| Command | Description |
|---------|-------------|
| `spark witr [process name...]` | Inspect why a process or port is running |
| `spark witr --pid <pid>` | Look up by PID |
| `spark witr --port <port>` | Find process by port |
| `spark witr --file <path>` | Find process holding file open |
| `spark witr --container <name>` | Inspect container |

Flags: `--tree`, `--env`, `--json`, `--short`, `--warnings`, `--verbose`, `--exact`, `--no-color`

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
gitlab:
  host: gitlab.example.com   # optional: scope the token to this instance
  token: glpat-xxxx          # GitLab token for batch-clone
```

## Documentation

Online docs: https://variableway.github.io/spark-cli/

| Path | Content |
|------|---------|
| [usage/usage.md](/en/usage/usage) | Command usage guide overview |
| [usage/git.md](/en/usage/git) | Git repository management |
| [usage/hub.md](/en/usage/hub) | Project hub |
| [usage/magic.md](/en/usage/magic) | System utilities |
| [usage/script.md](/en/usage/script) | Script management |
| [usage/docs-cmd.md](/en/usage/docs-cmd) | Docs management |
| [usage/witr.md](/en/usage/witr) | Process diagnostics |
| [quick-start/golang-cli-101.md](/en/quick-start/golang-cli-101) | Go CLI essentials, lesson 1 |
| [quick-start/nodejs-typescript-101.md](/en/quick-start/nodejs-typescript-101) | Node + TypeScript essentials, lesson 1 |
| [quick-start/docs-site-from-scratch.md](/en/quick-start/docs-site-from-scratch) | Docs site from scratch |
| [spec/git.md](/en/spec/git) | Command specs |
| [features/git.md](/en/features/git) | Feature guides |
| [Agents.md](/en/Agents) | Full command reference (site mirror) |
| [../../AGENTS.md](../../AGENTS.md) | Authoritative source: AI assistant instructions |
