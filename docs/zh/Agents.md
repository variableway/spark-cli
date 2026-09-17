# AGENTS.md

本文档记录 AI 助手在本项目中执行的关键任务、系统集成工作以及完整的功能说明。
仓库根目录的 [`AGENTS.md`](../../AGENTS.md) 与 [`CLAUDE.md`](../../CLAUDE.md) 是权威来源，本页为站点镜像。

## 项目概述

**Spark** 是一个 CLI 工具（`module spark`，二进制 `spark`），用于管理多个 Git 仓库、脚本、任务工作流，并附带实用系统工具。基于 **Cobra**（CLI）、**Viper**（配置）、**PTerm** + **Bubble Tea**（终端 UI），BDD 测试使用 **Ginkgo/Gomega**。

核心功能：

1. **多仓库更新** — 批量更新多个 Git 仓库到最新版本（支持 SSH）
2. **仓库克隆** — `git clone` 通过 `gh repo clone` 克隆 GitHub 仓库（默认 SSH）；`batch-clone` 支持 GitHub 组织/用户与 GitLab 群组/用户
3. **Submodule 管理** — `submodule add`（URL 或本地目录）、`submodule init`、`submodule status`、`submodule ensure-ssh`、`git sync`
4. **Git 用户配置** — `spark git config` 配置仓库的 Git 用户信息
5. **Gitcode 远程管理** — `spark git gitcode` 添加 Gitcode 远程地址
6. **组织状态** — `spark git update-org-status` 将组织仓库列表写入 README
7. **仓库扫描** — `spark git scan` 扫描目录中的仓库并保存到 SQLite
8. **仓库推送** — `spark git push-all` 批量提交推送所有更改
9. **Issue 创建** — `spark git issues` 从 Markdown/任务文件创建 GitHub Issue
10. **脚本管理** — 从 `~/.spark.yaml` 或 `scripts/` 目录发现并执行脚本
11. **系统工具** — `spark magic` 提供 DNS 缓存刷新、`node_modules`/`.venv` 清理、pip/npm/go 镜像源切换、Neovim/Ghostty 模板部署
12. **文档管理** — `spark docs init`/`spark docs site`（docmd 站点初始化）
13. **进程诊断** — `spark witr`（Why Is This Running），检查进程或端口为何在运行
14. **仓库管理** — `spark repo` 通过 registry 文件管理目录下的多个 GitHub 仓库（`scan`/`clone`/`list`），替代 submodule

## 技术栈

| 分层 | 技术 |
|------|------|
| 语言 | Go 1.27+（见 `go.mod`） |
| CLI 框架 | [Cobra](https://github.com/spf13/cobra) + [Viper](https://github.com/spf13/viper) |
| 终端 UI | [pterm](https://github.com/pterm/pterm) + [Bubble Tea](https://github.com/charmbracelet/bubbletea) |
| 测试 | [Ginkgo](https://github.com/onsi/ginkgo) + [Gomega](https://github.com/onsi/gomega)（`internal/`）、标准 `testing`（`cmd/`） |
| 构建 | Makefile + Taskfile（Windows / Linux / macOS） |
| 文档 | docmd（中英双语） |

## 项目结构

```
spark-cli/
├── main.go                  # 入口（调用 cmd.Execute()）
├── cmd/
│   ├── root.go              # 根命令、全局 flag、配置加载与 .monolize.yaml 自动迁移
│   ├── version.go           # spark version
│   ├── witr.go              # 桥接到 internal/witr/app.Root()
│   ├── git/                 # init/clone/update/submodule/sync/gitcode/config/url/
│   │                        # batch-clone/issues/update-org-status/push-all/scan
│   ├── repo/                # registry 文件驱动的仓库管理（scan/clone/list）
│   ├── magic/               # clean/copy-config/flush-dns/pip/go/node
│   ├── script/              # list/run
│   └── docs/                # init/site
├── internal/
│   ├── config/              # 配置加载
│   ├── git/                 # Git 操作封装（finder/updater/init/submodule/pusher + scanner）
│   ├── github/              # GitHub API（org / markdown issue）
│   ├── gitlab/              # GitLab API（batch-clone：URL 解析、token 来源、嵌套群组）
│   ├── registry/            # repo 命令的扫描/读写/merge 逻辑
│   ├── script/              # 脚本发现与执行
│   ├── templates/           # 嵌入的 dotfiles（nvim + ghostty）
│   └── witr/                # Why-Is-This-Running 进程诊断引擎
├── pkg/witr/model/          # witr 共享数据模型
├── docs/{zh,en}/            # docmd 站点（中文为默认 locale，英文镜像在 /en/）
├── scripts/                 # 默认脚本目录 + 安装/校验脚本
├── Makefile / Taskfile.yml  # 构建与测试入口
└── docmd.config.js          # docmd 配置（i18n.default: zh）
```

## CLI 命令完整参考

### 全局选项

| 选项 | 说明 |
|------|------|
| `--config` | 配置文件路径（默认：`$HOME/.spark.yaml`） |
| `-p, --path` | 仓库扫描目录路径（StringSlice，默认 `["."]`，绑定 viper key `repo-path`） |

配置初始化（`initConfig` + `migrateOldConfig`）：`--config` 优先；启动时若存在旧版 `~/.monolize.yaml`
且 `~/.spark.yaml` 不存在则自动重命名迁移；`viper.AutomaticEnv()` 启用环境变量覆盖。

---

### `spark git` — Git 仓库管理

```bash
spark git init [--owner <o>] [-r <name>] [--private] [--skip-gh]   # 初始化并创建 GitHub 远程
spark git clone <url-or-slug> [directory] [-- <git-args>]          # gh repo clone（默认 SSH）
spark git update [-p <dir>] [--ssh]                                # 扫描并更新所有仓库
spark git submodule add <path-or-url> [-n <name>]                  # 添加子模块
spark git submodule init [-r] [-j <n>] [--name <n>]                # 初始化子模块
spark git submodule status [-r]                                    # 子模块状态
spark git submodule ensure-ssh                                     # HTTPS → SSH 重写
spark git sync [repo-path] [-r]                                    # 同步子模块到最新
spark git gitcode [-p <dir>] [--url <url>]                         # 添加 Gitcode 远程
spark git config [repo-path] [--username <u>] [--email <e>]        # 配置 Git 用户
spark git url [repo-path]                                          # 打印 remote URL
spark git batch-clone <account-or-url> [flags]                     # 批量克隆 GitHub/GitLab 账号
spark git issues (-d <dir> | -f <file>) [-r <owner/repo>] [-l ...] [--dry-run]
spark git update-org-status <org> [--dry-run] [-o <path>] [--update-dot-github] [--section <n>] [--skip-push]
spark git push-all [-p <dir>]                                      # commit + push 所有仓库
spark git scan [folder-path] [-d <db>] [--skip-api]                # 扫描并写入 SQLite
```

`spark git clone` 支持 `https://github.com/owner/repo.git`、`git@github.com:owner/repo.git`、
`github.com/owner/repo`、`owner/repo` 四种输入，`--` 之后的参数透传给 `git clone`。

`spark git batch-clone` 选项：

| 选项 | 说明 |
|------|------|
| `--ssh` | 使用 SSH URL（GitHub `git@github.com:...`，GitLab `git@<host>:...`） |
| `--include` / `--exclude` | 名称包含/排除模式（逗号分隔） |
| `--include-forks` | 包含 fork 仓库 |
| `-o, --output` | 输出目录（默认 `.`） |
| `--token` | GitLab 私有 Token（显式指定，不受 `gitlab.host` 限制） |

GitLab 实现要点：

- 支持无 scheme 输入（`gitlab.com/gitlab-com/gl-infra`），`internal/gitlab.ParseGitLabURL` 自动补 `https://`
- API v4 的群组路径必须 URL 编码（`group/sub` → `group%2Fsub`），见 `internal/gitlab.escapePath`；
  配合 `include_subgroups=true` 递归任意层级子群组
- 克隆落盘路径按命名空间相对路径展开（`internal/gitlab.ProjectRelativePath`），
  如 `observability/tenant-observability/argocd-tenant-plugin`，避免子群组同名项目互相覆盖
- Token 优先级：`--token` > `gitlab.token` > `GITLAB_TOKEN` > `GITLAB_PRIVATE_TOKEN`，
  由 `cmd/git.resolveGitLabToken` 解析并打印 `Using token from: ...`
- `gitlab.host` 把自动发现的凭证限定到该实例，不匹配时打印
  `Ignoring ...: it is scoped to ...` 并跳过；`--token` 不受限制
- 私有实例/私有群组未认证时返回 404 而非 401，错误信息据此区分
  「凭证被拒绝」/「未提供凭证」/「路径不存在」

---

### `spark repo` — 仓库管理

通过 registry 文件管理目录下的多个 GitHub 仓库（替代 submodule）：

```bash
spark repo scan [folder-name]                        # 扫描目录写入 registry_<folder>.yaml
spark repo clone -f registry_<folder>.yaml           # 克隆 registry 中全部仓库
spark repo clone -r <name> -f registry_<folder>.yaml # 仅克隆指定仓库
spark repo list -f registry_<folder>.yaml            # 列出 registry 中的仓库
```

| 选项 | 命令 | 说明 |
|------|------|------|
| `-r, --repo` | `clone` | 仅克隆指定名称的仓库（省略则全部） |
| `-f, --file` | `clone` / `list` | registry 文件（必填） |

---

### `spark script` — 脚本管理

```bash
spark script list
spark script run <script-name> [args...]
```

搜索顺序：`~/.spark.yaml` 的 `spark.scripts` → `spark.scripts_dir`（默认 `scripts/`）下的脚本文件。
支持扩展名：`.sh` `.bash` `.zsh` `.py` `.rb` `.pl` `.ps1` `.bat` `.cmd`。

---

### `spark magic` — 系统工具

```bash
spark magic clean [-m node|python]     # 清理 node_modules / .venv
spark magic copy-config [<user@host:path>]  # 部署内置 nvim + ghostty 模板
spark magic flush-dns                  # 刷新 DNS（macOS/Windows/Linux）
spark magic pip {list,use,current}     # default/tsinghua/aliyun/douban/ustc/tencent
spark magic go {list,use,current}      # default/aliyun/tsinghua/goproxy/ustc/nju
spark magic node {list,use,current}    # default/taobao/aliyun/tencent/huawei/ustc
```

`copy-config` 的模板来自 `internal/templates/dotfiles/`，构建时通过 `//go:embed` 嵌入，
优先使用 `rsync`，缺失时回退 `cp`。

---

### `spark docs` — 文档管理

```bash
spark docs init [--root <dir>]   # 创建 docs 目录结构
spark docs site [--root <dir>]   # 初始化 docmd 站点配置
```

---

### `spark witr` — 进程诊断

```bash
spark witr nginx
spark witr --pid 1234 --tree
spark witr --port 8080
spark witr --file /var/lib/dpkg/lock
spark witr --container redis --json
```

| 选项 | 说明 |
|------|------|
| `--pid` | 按 PID 查找（可多次） |
| `--port` / `-o` | 按端口查找（可多次） |
| `--file` / `-f` | 按文件查找（可多次） |
| `--container` / `-c` | 按容器名查找（可多次） |
| `--tree` / `-t` | 显示进程祖先树 |
| `--env` | 显示进程环境变量 |
| `--json` | JSON 输出 |
| `--short` / `-s` | 单行简短输出 |
| `--warnings` | 仅显示可疑的环境/参数/父进程 |
| `--verbose` | 扩展信息（内存、I/O、fd） |
| `--exact` / `-x` | 精确匹配 |
| `--no-color` | 禁用颜色 |

---

### `spark version`

打印 version / commit / build date（由 Makefile 的 ldflags 注入到 `internal/witr/version`）。

## 配置文件

配置文件位于 `~/.spark.yaml`，从旧版 `~/.monolize.yaml` 自动迁移。完整示例见 `.spark.yaml.example`：

```yaml
repo-path:
  - ~/workspace
  - ~/projects

git:
  username: your-name
  email: your-email@example.com
  scanner:
    db: ~/.innate/feeds.db         # spark git scan 默认 SQLite 路径

gitlab:
  host: gitlab.example.com         # 可选：把自动发现的凭证限定到该实例
  token: glpat-xxxx                # 需 read_api，克隆私有仓库还需 read_repository

github-owner: your-github-username # spark git init --owner 默认值

spark:
  scripts_dir: scripts
  scripts:
    - name: hello
      content: |
        #!/bin/bash
        echo "Hello, World!"
```

| 配置键 | 读取处 |
|--------|--------|
| `repo-path`（全局 `-p, --path`） | `cmd/git/update.go`、`push_all.go`、`magic/clean.go`、`gitcode.go` |
| `git.username` / `git.email` | `cmd/git/config.go`、`cmd/git/init.go` |
| `git.scanner.db`（`--db`） | `cmd/git/scan.go` |
| `gitlab.host` / `gitlab.token`（`--token`） | `cmd/git/batch_clone.go` |
| `github-owner` | `cmd/git/init.go` |
| `spark.scripts_dir` | `cmd/script/list.go`、`cmd/script/run.go` |

GitLab Token 的环境变量用 `os.Getenv` 而非 `viper.AutomaticEnv()`：viper 会把 `gitlab.token`
映射为 `GITLAB.TOKEN`，而 shell 无法定义含 `.` 的变量名。

## 构建与测试

```bash
make build          # 编译 + 打 version/commit/date ldflags + 安装到 ~/.local/bin/spark
make build-linux    # 交叉编译 Linux amd64
make build-darwin   # 交叉编译 macOS amd64
make test           # go test ./... -v
make test-bdd       # ginkgo -v ./internal/...
make lint           # go vet ./...
make clean          # 清理构建产物
```

`Taskfile.yml` 提供等价命令：`task build` / `task install` / `task install-binary` / `task verify-install`。

运行单个测试：

```bash
go test ./internal/git/... -v -run TestUpdateRepository
```

## 助手指令参考

1. **代码风格**：遵循 Go 标准规范；不添加注释（除非明确要求）；沿用既有库与模式（Cobra + Viper + PTerm + Ginkgo/Gomega）
2. **测试要求**：新功能必须添加测试；`internal/` 用 Ginkgo/Gomega BDD 风格，`cmd/` 下的纯函数用标准 `testing`
3. **构建一致性**：优先更新 `Makefile`；确保 `.vscode` 配置通用；提交前运行 `make lint` 与 `make test`
4. **文档更新**：同步 `docs/zh/**` 与 `docs/en/**`、`docs/{zh,en}/navigation.json`、`docs/{zh,en}/Agents.md`、仓库根 `AGENTS.md` 与 `CLAUDE.md`
