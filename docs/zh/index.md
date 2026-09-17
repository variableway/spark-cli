---
title: Spark CLI
description: 日常开发自动化和 AI Skill 集成的 CLI 工具
---

# Spark CLI

A CLI tool for daily dev automation and AI skill integration.

**Why Spark?** Deterministic tasks (file scaffolding, mirror switching, config management) can be automated by CLI to save token cost. Spark also provides a CLI app backend for AI skills — so agents can call `spark` instead of burning LLM tokens on repetitive operations.

> Most code is AI-generated, all inspired by real daily workflows.

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

验证安装的二进制确实是最新的：

```bash
spark version       # -> spark v0.3.2 / commit 1ef84d7 / build date ...
spark --version     # -> spark version v0.3.2
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
| `spark git update [--ssh]` | Update all repos to latest version (`--ssh` 强制 SSH) |
| `spark git submodule add [-p <path>]` | Add existing repos as submodules |
| `spark git submodule add <repo-url> [-n <name>]` | Add a remote repo as a submodule |
| `spark git submodule init [-j <n>] [-r] [--name <name>]` | Initialize missing submodules |
| `spark git submodule status` | Show submodule initialization status |
| `spark git submodule ensure-ssh` | Rewrite HTTPS submodule URLs to SSH |
| `spark git sync [repo] [-r]` | Sync all submodules to latest |
| `spark git gitcode [-p <path>]` | Add Gitcode remote to repos |
| `spark git init [--owner <owner>] [--skip-gh]` | Initialize git repo, create GitHub remote |
| `spark git config [--username --email]` | Configure git user for repo |
| `spark git url [repo-path]` | Get remote URL of repository |
| `spark git batch-clone <account-or-url> [--ssh] [--include] [--exclude] [--include-forks] [-o <dir>] [--token]` | Clone all repos from a GitHub org/user or a GitLab group/user |
| `spark git update-org-status <org> [--dry-run] [--update-dot-github] [--section <name>]` | Update org README with repo list |
| `spark git issues [-r <owner/repo>] (-d <dir> \| -f <file>) [--dry-run] [-l <labels>]` | Create GitHub issues from markdown docs/tasks |
| `spark git push-all [-p <path>]` | Commit and push all changes in repositories |
| `spark git scan [folder-path] [-d <db>] [--skip-api]` | Scan git repos and save to SQLite |

---

### spark repo — Repository Management

| Command | Description |
|---------|-------------|
| `spark repo scan [folder-name]` | Scan a directory and write `registry_<folder>.yaml` |
| `spark repo clone -f <file> [-r <name>]` | Clone repos listed in a registry file |
| `spark repo list -f <file>` | List repos in a registry file |

Registry files (`registry_<folder>.yaml`) replace submodules for managing many repos in one directory.

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
  host: gitlab.example.com   # 可选：把 token 限定到该实例
  token: glpat-xxxx          # batch-clone 的 GitLab Token
github-owner: your-username  # spark git init --owner 默认值
```

## Documentation

Online docs: https://variableway.github.io/spark-cli/

| Path | Content |
|------|---------|
| [usage/](usage/usage.md) | 命令使用指南总览 |
| [usage/git.md](usage/git.md) | Git 仓库管理 |
| [usage/repo.md](usage/repo.md) | 仓库管理（registry） |
| [usage/magic.md](usage/magic.md) | 系统工具 |
| [usage/script.md](usage/script.md) | 脚本管理 |
| [usage/docs-cmd.md](usage/docs-cmd.md) | 文档管理 |
| [usage/witr.md](usage/witr.md) | 进程诊断 |
| [Agents.md](Agents.md) | 命令完整参考（站点镜像） |
| [../../AGENTS.md](../../AGENTS.md) | 权威来源：AI 助手指令 |
| [../../CLAUDE.md](../../CLAUDE.md) | Claude Code 开发指南 |
