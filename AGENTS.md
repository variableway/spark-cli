# AGENTS.md

本文档记录了 AI 助手在本项目中执行的关键任务、系统集成工作以及完整的功能说明。

## 项目概述

**Spark** 是一个 CLI 工具（`module spark`，二进制 `spark`），用于管理多个 Git 仓库、脚本、任务工作流，并附带实用系统工具。基于 **Cobra**（CLI）、**Viper**（配置）、**PTerm**（终端 UI），BDD 测试使用 **Ginkgo/Gomega**。

核心功能：

1. **多仓库更新** — 批量更新多个 Git 仓库到最新版本（支持 SSH）
2. **仓库克隆** — 通过 `gh repo clone` 克隆 GitHub 仓库（默认 SSH）；`batch-clone` 支持 GitHub 组织/用户与 GitLab 群组/用户
3. **Submodule 管理** — `submodule add`（URL 或本地目录）、`submodule init`、`submodule status`、`submodule ensure-ssh`、`git sync`
4. **Git 用户配置** — `spark git config` 配置仓库的 Git 用户信息
5. **Gitcode 远程管理** — `spark git gitcode` 添加 Gitcode 远程地址
6. **组织状态** — `spark git update-org-status` 将组织仓库列表写入 README
7. **仓库扫描** — `spark git scan` 扫描目录中的仓库并保存到 SQLite
8. **仓库推送** — `spark git push-all` 批量提交推送所有更改
9. **Issue 创建** — `spark git issues` 从 Markdown/任务文件创建 GitHub Issue
10. **任务管理** — `spark task` 任务分发、同步、issue CRUD 与 `impl`（基于 `kimi` CLI）
11. **脚本管理** — 从 `~/.spark.yaml` 或 `scripts/` 目录发现并执行脚本
12. **系统工具** — `spark magic` 提供 DNS 缓存刷新、`node_modules`/`.venv` 清理、pip/npm/go 镜像源切换、Neovim/Ghostty 模板部署
13. **文档管理** — `spark docs init`/`spark docs site`（docmd 站点初始化）
14. **进程诊断** — `spark witr`（Why Is This Running），检查进程或端口为何在运行

## 技术栈

- **语言**: Go 1.24+
- **CLI 框架**: [Cobra](https://github.com/spf13/cobra) + [Viper](https://github.com/spf13/viper)
- **终端 UI**: [pterm](https://github.com/pterm/pterm) + 自定义 TUI 组件
- **测试框架**: [Ginkgo](https://github.com/onsi/ginkgo) + [Gomega](https://github.com/onsi/gomega) (BDD 风格)
- **构建系统**: Makefile（跨平台：Windows / Linux / macOS）

## 项目结构

```
spark-cli/
├── main.go                  # 入口（调用 cmd.Execute()）
├── cmd/
│   ├── root.go              # 根命令、全局 flag、配置加载与 .monolize.yaml 自动迁移
│   ├── task.go              # task 命令及所有子命令（dispatch/sync/list/init/create/delete/impl）
│   ├── witr.go              # 桥接到 internal/witr/app.Root()
│   ├── git/                 # Git 仓库管理命令
│   │   ├── git.go           # GitCmd 父命令
│   │   ├── init.go          # spark git init
│   │   ├── clone.go         # spark git clone
│   │   ├── update.go        # spark git update（--ssh）
│   │   ├── submodule.go     # spark git submodule {add,init,status,ensure-ssh}
│   │   ├── sync.go          # spark git sync（--recursive）
│   │   ├── gitcode.go       # spark git gitcode（--url）
│   │   ├── config.go        # spark git config（--username, --email）
│   │   ├── url.go           # spark git url
│   │   ├── batch_clone.go   # spark git batch-clone（GitHub + GitLab）
│   │   ├── issues.go        # spark git issues（-r, -f, -d, -l, --dry-run）
│   │   ├── update_org_status.go  # spark git update-org-status
│   │   ├── push_all.go      # spark git push-all
│   │   └── scan.go          # spark git scan（-d/--db, --skip-api）
│   ├── magic/               # 系统实用命令
│   │   ├── magic.go         # MagicCmd 父命令
│   │   ├── clean.go         # spark magic clean（-m node|python）
│   │   ├── copy_config.go   # spark magic copy-config（部署 nvim/ghostty 模板）
│   │   ├── flush_dns.go     # spark magic flush-dns
│   │   ├── pip.go           # spark magic pip {list,use,current}
│   │   ├── go.go            # spark magic go {list,use,current}
│   │   └── node.go          # spark magic node {list,use,current}
│   ├── script/              # 脚本管理
│   │   ├── script.go        # ScriptCmd 父命令
│   │   ├── list.go          # spark script list
│   │   └── run.go           # spark script run <name> [args...]
│   └── docs/                # 文档管理
│       ├── docs.go          # DocsCmd 父命令
│       ├── init.go          # spark docs init（--root）
│       └── site.go          # spark docs site（--root）
├── internal/
│   ├── config/              # 配置加载
│   ├── git/                 # Git 操作封装（finder/updater/init/submodule/pusher + scanner 子包）
│   │   └── scanner/         # git scan 使用的扫描与 SQLite 持久化
│   ├── github/              # GitHub API（org / markdown issue）
│   ├── gitlab/              # GitLab API（用于 batch-clone）
│   ├── script/              # 脚本发现（配置 + scripts/ 目录）与执行
│   ├── task/                # 任务 init/dispatch/sync、issue CRUD、impl（kimi）
│   ├── templates/           # 嵌入的 dotfiles（nvim + ghostty）
│   ├── tui/                 # PTerm 上层封装（确认对话框、选择器）
│   └── witr/                # Why-Is-This-Running 进程诊断引擎
├── pkg/
├── docs/
│   ├── usage/               # 每个命令的使用说明
│   ├── specs/               # 规约文档
│   ├── analysis/            # 架构分析
│   └── features/            # 功能说明
├── scripts/                 # 默认脚本目录（spark script 使用）
├── .vscode/                 # VS Code 配置（tasks/launch/settings）
├── Makefile                 # 构建脚本（build/build-linux/build-darwin/test/lint/clean）
├── docmd.config.js          # docmd 站点配置
├── go.mod / go.sum
└── package.json             # docmd 依赖
```

## 命令层级

```
spark
├── version                 (显示 spark version / commit / build date)
├── git
│   ├── init
│   ├── clone
│   ├── update               (--ssh)
│   ├── submodule
│   │   ├── add              (-n, --name)
│   │   ├── init             (-r, --recursive, -j, --parallel, --name)
│   │   ├── status           (-r, --recursive)
│   │   └── ensure-ssh
│   ├── sync                 (-r, --recursive)
│   ├── gitcode              (--url)
│   ├── config               (--username, --email)
│   ├── url
│   ├── batch-clone          (--ssh, --include, --exclude, --include-forks, -o, --token)
│   ├── issues               (-r, -f, -d, -l, --dry-run)
│   ├── update-org-status    (--dry-run, -o, --update-dot-github, --section, --skip-push)
│   ├── push-all
│   └── scan                 (-d, --db, --skip-api)
├── task                     (--task-dir, --owner, --work-dir, --tui)
│   ├── dispatch             (--dest)
│   ├── sync                 (--work-path)
│   ├── list
│   ├── init
│   ├── create               (--content)
│   ├── delete               (--force)
│   └── impl
├── script
│   ├── list
│   └── run
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

## 自动化任务记录

### 1. BDD 测试集成 (2026-02-26)
- **任务**: 为 `internal` 包添加 BDD 风格的单元测试。
- **工具**: 引入了 `Ginkgo` 和 `Gomega` 框架。
- **覆盖范围**: `internal/config`、`internal/git`（含 finder/updater/submodule）、`internal/script`、`internal/task`、`internal/github`（issue/markdown_issue/org）、`internal/gitlab`、`internal/witr/output`。
- **验证**: 所有测试已通过 `make test-bdd` 验证。

### 2. 跨平台 Makefile 构建 (2026-02-26)
- **任务**: 创建支持 Windows、Linux、macOS 的构建系统。
- **功能**:
    - 自动 OS 检测（`ifeq ($(OS),Windows_NT)`）。
    - 交叉编译支持（`build-linux`、`build-darwin`）。
    - 统一的清理与测试接口。
    - 构建产物自动安装到 `~/.local/bin/spark`。

### 3. VS Code 环境标准化 (2026-02-26)
- **任务**: 优化 `.vscode` 目录配置。
- **成果**:
    - `tasks.json`: 与 Makefile 深度绑定。
    - `launch.json`: 提供标准化的调试模板。
    - `settings.json`: 统一 Go 语言开发规范。

### 4. GitLab batch-clone 支持
- 增加 `internal/gitlab` 子包；
- `spark git batch-clone <git-host>/<group>/<subgroup>` 同时支持自托管 GitLab；
- 支持 `--token` / `GITLAB_TOKEN` / `GITLAB_PRIVATE_TOKEN` 环境变量认证。

## CLI 命令完整参考

### 全局选项

由 `cmd/root.go` 通过 `rootCmd.PersistentFlags()` 定义：

| 选项 | 说明 |
|------|------|
| `--config` | 配置文件路径（默认：`$HOME/.spark.yaml`） |
| `-p, --path` | 仓库扫描目录路径（StringSlice，默认 `["."]`，绑定到 viper key `repo-path`） |

配置初始化流程（`initConfig` + `migrateOldConfig`）：

1. 若 `--config` 被指定则使用该文件，否则默认 `$HOME/.spark.yaml`。
2. 启动时检测旧配置 `~/.monolize.yaml`：存在且 `~/.spark.yaml` 不存在则自动重命名迁移。
3. `viper.AutomaticEnv()` 启用环境变量覆盖。

---

### `spark git` — Git 仓库管理

父命令 `GitCmd` 在 `cmd/git/git.go` 中定义，包含以下子命令（在 `init()` 函数中按文件注册）：

```bash
spark git init                   # 初始化仓库并创建 GitHub 远程
spark git clone <url-or-slug>    # 通过 gh repo clone（默认 SSH）
spark git update [-p ...]        # 扫描并更新所有仓库（--ssh 强制走 SSH）
spark git submodule add ...      # 添加子模块
spark git submodule init ...     # 初始化所有/指定子模块
spark git submodule status       # 查看子模块状态
spark git submodule ensure-ssh   # 将 .gitmodules 中 HTTPS 重写为 SSH
spark git sync [path]            # 同步当前仓库的所有子模块
spark git gitcode [-p ...]       # 添加 gitcode 远程
spark git config [path]          # 配置 Git 用户信息
spark git url [path]             # 打印当前仓库的远程 URL
spark git batch-clone <account>  # 批量克隆 GitHub/GitLab 账号下仓库
spark git issues                 # 从 Markdown/任务文件创建 GitHub Issue
spark git update-org-status <org># 生成组织仓库列表并写入 README
spark git push-all [-p ...]      # 扫描并 commit/push 所有仓库
spark git scan [folder-path]     # 扫描仓库并写入 SQLite
```

#### `spark git update`
扫描 `repo-path` 下所有仓库并更新到最新版本。

```bash
spark git update -p /path/to/repos
spark git update -p ~/workspace -p ~/projects
spark git update --ssh                                  # 强制 HTTPS→SSH
```

| 选项 | 说明 |
|------|------|
| `-p, --path` | 扫描目录（可多次指定，覆盖 `repo-path`） |
| `--ssh` | 强制将 HTTPS GitHub URL 重写为 SSH 后更新 |

#### `spark git clone`
通过 `gh repo clone` 克隆 GitHub 仓库，默认走 SSH。

```bash
spark git clone https://github.com/Nutlope/pdf-to-interactive-lesson.git
spark git clone Nutlope/pdf-to-interactive-lesson
spark git clone https://github.com/owner/repo.git my-dir -- --branch main --depth 1
```

支持的输入格式：
- `https://github.com/owner/repo.git`
- `git@github.com:owner/repo.git`
- `github.com/owner/repo`
- `owner/repo`

`--` 之后的额外参数会透传给 `git clone`。

#### `spark git init`
初始化当前目录为 Git 仓库并创建 GitHub 远程仓库。

```bash
spark git init --owner variableway              # 初始化并创建远程仓库
spark git init --owner variableway --private    # 创建私有仓库
spark git init --skip-gh --owner variableway    # 仅本地初始化，跳过 GitHub
```

| 选项 | 说明 |
|------|------|
| `--owner` | GitHub owner（默认：`github-owner` 配置） |
| `-r, --repo` | 仓库名（默认：当前目录名） |
| `--private` | 创建私有仓库 |
| `--skip-gh` | 跳过 `gh repo create --push` |

执行步骤（已存在 GitHub 仓库时仅步骤 2-3）：
1. `git init`
2. 配置 `git user.name` / `user.email`（来自 `git.username` / `git.email`）
3. 扫描子目录中的 GitHub 仓库并以子模块加入
4. 生成 `.gitignore`
5. `chore: initial commit via spark git init`
6. `gh repo create --push`（除非 `--skip-gh`）

#### `spark git submodule`
子模块管理父命令。

##### `submodule add <path-or-url>`
- URL 模式：`spark git submodule add https://github.com/owner/repo`
- 文件夹模式：`spark git submodule add ./path/to/folder`（扫描目录中所有 GitHub 仓库作为子模块加入）

| 选项 | 说明 |
|------|------|
| `-n, --name` | 自定义子模块路径名（URL 模式默认取仓库名） |

##### `submodule init`
执行 `git submodule update --init`：

```bash
spark git submodule init                          # 串行初始化所有未初始化的子模块
spark git submodule init -j 4                     # 并行，4 workers
spark git submodule init --recursive              # 递归初始化嵌套子模块
spark git submodule init --name spark-cli         # 仅初始化指定子模块
```

| 选项 | 说明 |
|------|------|
| `-r, --recursive` | 递归初始化嵌套子模块 |
| `-j, --parallel` | 并行 worker 数（默认 1） |
| `--name` | 仅初始化指定名称的子模块 |

##### `submodule status`
显示每个子模块的路径、是否已初始化、提交哈希、分支。

| 选项 | 说明 |
|------|------|
| `-r, --recursive` | 显示嵌套子模块 |
| `-j, --parallel` | 在 status 命令中未使用 |

##### `submodule ensure-ssh`
将 `.gitmodules` 中所有 HTTPS GitHub URL 重写为 SSH 形式（`git@github.com:...`）。

#### `spark git sync [path]`
拉取父仓库远端并把所有子模块更新到远端最新 commit。

```bash
spark git sync .
spark git sync --recursive        # 嵌套子模块
spark git sync /path/to/repo
```

#### `spark git gitcode`
为 GitHub 仓库批量添加 `gitcode` 远程（自动将 `github.com` → `gitcode.com`）。

```bash
spark git gitcode -p /path/to/repos
spark git gitcode --url https://custom.gitcode.url
```

| 选项 | 说明 |
|------|------|
| `--url` | 自定义 Gitcode 远程 URL（默认自动转换） |

#### `spark git config [path]`
读取默认 `git.username`/`git.email`（来自 `~/.spark.yaml`），写入本地仓库 `git config`。

```bash
spark git config                                # 查看当前配置
spark git config --username foo --email bar     # 显式覆盖
```

| 选项 | 说明 |
|------|------|
| `--username` | Git 用户名（默认：`git.username`） |
| `--email` | Git 邮箱（默认：`git.email`） |

配置优先级：命令行 → `~/.spark.yaml` → 提示用户配置。

#### `spark git url [path]`
读取并打印当前仓库的 origin URL。

#### `spark git batch-clone`
根据输入自动识别 GitHub 或 GitLab，克隆账号下所有仓库。

```bash
# GitHub
spark git batch-clone variableway
spark git batch-clone https://github.com/variableway

# GitLab（自托管或 gitlab.com，递归支持子群组）
spark git batch-clone https://gitlab.example.com/myorg/mygroup
spark git batch-clone https://gitlab.example.com/myorg/mygroup/subgroup

# 通用
spark git batch-clone variableway --ssh
spark git batch-clone variableway -o ./repos
spark git batch-clone <url> --token <token>      # 也支持 GITLAB_TOKEN / GITLAB_PRIVATE_TOKEN 环境变量
```

| 选项 | 说明 |
|------|------|
| `--ssh` | 使用 SSH URL（GitHub `git@github.com:...`，GitLab `git@<host>:...`） |
| `--include` | 仅克隆名称含任一模式（逗号分隔）的仓库 |
| `--exclude` | 跳过名称含任一模式（逗号分隔）的仓库 |
| `--include-forks` | 包含 fork 仓库（GitHub 通过 `repo.Fork` 判定；GitLab 通过 `forked_from` 字段） |
| `-o, --output` | 输出目录（默认 `.`） |
| `--token` | GitLab 私有 Token（也可由 `GITLAB_TOKEN` / `GITLAB_PRIVATE_TOKEN` 环境变量提供） |

#### `spark git issues`
两种模式：从目录中每个 Markdown 文件创建 Issue，或从任务文件（`## Task <id>...`）创建 Issue。

```bash
# 目录模式
spark git issues -d ./docs -r owner/repo

# 任务模式
spark git issues -f tasks/issues/task-bug-fix.md -r owner/repo

# 自动从当前仓库解析 owner/repo（需 GitHub remote）
spark git issues -d ./docs --dry-run

# 加标签
spark git issues -d ./docs -l bug,enhancement
```

| 选项 | 说明 |
|------|------|
| `-r, --repo` | 目标仓库（`owner/repo`），未指定时从当前 git remote 解析 |
| `-d, --dir` | Markdown 目录（目录模式） |
| `-f, --file` | 任务文件（任务模式） |
| `-l, --labels` | Issue 标签（逗号分隔） |
| `--dry-run` | 仅预览，不创建 |

> `-d` 与 `-f` 互斥，必须二选一。

#### `spark git update-org-status`
获取 GitHub 组织所有仓库，按 star 数排序，写入一个 section 到 README。

```bash
spark git update-org-status variableway                    # 写入 .github/README.md
spark git update-org-status variableway --update-dot-github
spark git update-org-status variableway --dry-run
spark git update-org-status variableway -o ./docs/README.md
spark git update-org-status variableway --section "Projects"
spark git update-org-status variableway --skip-push
```

| 选项 | 说明 |
|------|------|
| `--dry-run` | 打印内容，不写入文件 |
| `-o, --output` | 本地模式输出路径（默认：`.github/README.md`） |
| `--update-dot-github` | 直接克隆组织的 `.github` 仓库并修改 |
| `--section` | 要更新/插入的 section 名（默认：`Project List`） |
| `--skip-push` | 跳过 `git commit` 与 `git push` |

特性：
- 默认写入本地 `.github/README.md`；若在 `.github` 目录下，同时写入 `profile/README.md`
- 使用 `--update-dot-github` 时会克隆到 `$TMPDIR/github-repo-<org>-<ts>`，写入后再 commit/push

#### `spark git push-all`
扫描 `repo-path` 下所有仓库，对 GitHub 仓库且有更改的执行 `git add -A` → `git commit` → `git push`，冲突时提示。

#### `spark git scan [folder-path]`
递归扫描目录中的仓库，可选调用 GitHub/GitLab API 拉取元数据，写入 SQLite。

```bash
spark git scan                                # 默认扫描当前目录
spark git scan ~/workspace
spark git scan . --skip-api
spark git scan . --db ~/.innate/feeds.db
```

| 选项 | 说明 |
|------|------|
| `[folder-path]` | 要扫描的目录（位置参数，默认 `.`） |
| `-d, --db` | SQLite 数据库路径（默认：`~/.innate/feeds.db`，可由 `git.scanner.db` 配置或 `~`-prefix 扩展） |
| `--skip-api` | 跳过 API，仅扫描本地仓库 |

`~/.spark.yaml` 中可通过 `git.scanner.db` 设置默认数据库路径。设置 `GITHUB_TOKEN` 可提升 GitHub API 速率限制。

---

### `spark task` — 任务管理

```bash
spark task init                    # 初始化 tasks/ 目录结构
spark task list                    # 列出任务目录与 issue 文件
spark task create <feature>        # 新建 issue 文件（--content 写入 ## 描述）
spark task delete <feature>        # 删除 issue 文件（--force 跳过确认）
spark task impl <feature>          # 使用 kimi CLI 实现 issue
spark task dispatch [task-name]    # 复制任务到 --dest 并创建 GitHub 仓库
spark task sync [task-name]        # 将 --work-path 中的实现同步回任务目录
```

> TUI 模式默认开启（通过 `--tui=false` 关闭）。TUI 启用时通过 PTerm 任务列表、确认对话框与进度条交互。

| 选项（持久） | 说明 |
|------|------|
| `--task-dir` | 任务目录（绑定到 `task_dir`） |
| `--owner` | GitHub owner（绑定到 `github_owner`） |
| `--work-dir` | 工作目录（绑定到 `work_dir`，默认 `.`） |
| `--tui` | 是否启用 TUI（默认 `true`；关闭用 `--tui=false`） |

| 子命令 | 选项 | 说明 |
|--------|------|------|
| `dispatch` | `--dest` | 任务分发目标路径（默认 `<work-dir>/<task-name>`） |
| `sync` | `--work-path` | 已分发任务的工作路径 |
| `create` | `--content` | 自定义内容写入 `## 描述` |
| `delete` | `--force` | 强制删除不提示 |

任务目录结构（`task init` 创建）：

```
tasks/
├── issues/
├── config/
├── analysis/
├── mindstorm/
├── planning/
└── prd/
```

`task impl` 依赖：kimi CLI、`github-task-workflow` 工具。流程：
1. 读取 issue 文件
2. 创建 GitHub issue
3. 通过 kimi CLI 执行实现
4. 更新 issue 与提交更改

---

### `spark script` — 脚本管理

```bash
spark script list
spark script run <script-name> [args...]
```

#### `spark script list`
列出所有可用脚本，按来源分组（`~/.spark.yaml` 中的 `spark.scripts` 与 `scripts/` 目录）。

#### `spark script run`
按以下顺序搜索脚本：
1. `~/.spark.yaml` 中的 `spark.scripts`
2. 当前目录（可通过 `--scripts-dir` 或 `spark.scripts_dir` 配置，默认为 `scripts/`）下的脚本文件

支持的脚本类型（根据扩展名识别）：`.sh` `.bash` `.zsh` `.py` `.rb` `.pl` `.ps1` `.bat` `.cmd`

仓库内置脚本示例：
- `copy-template.sh`
- `list-dirs.sh`

---

### `spark magic` — 系统工具

```bash
spark magic clean                  # 清理 node_modules 和 .venv
spark magic copy-config            # 部署内置 nvim + ghostty 模板
spark magic flush-dns              # 刷新 DNS（macOS/Windows/Linux）
spark magic pip {list,use,current}
spark magic go {list,use,current}
spark magic node {list,use,current}
```

#### `spark magic clean`
递归清理 `repo-path`（或 `.`）下所有 `node_modules` 与 `.venv` 目录；遇到 `.git` 子目录跳过递归。

```bash
spark magic clean                  # 默认两者都清理
spark magic clean -m node          # 仅 node_modules
spark magic clean -m python        # 仅 .venv
```

| 选项 | 说明 |
|------|------|
| `-m, --mode` | `node` 或 `python`（默认两者都清理） |

#### `spark magic copy-config [<user@host:path>]`
将编译时通过 `embed.FS` 打包进二进制的 nvim 和 ghostty 模板部署到目标位置。优先使用 `rsync`，缺失时回退到 `cp`。

```bash
spark magic copy-config                                # 部署到本机 ~/.config/{nvim,ghostty}
spark magic copy-config user@192.168.1.100:~/          # 通过 SSH 部署到远端 PC
spark magic copy-config /mnt/usb/backup/               # 部署到自定义本地路径
```

来源模板位于 `internal/templates/dotfiles/`，构建时通过 `//go:embed` 嵌入。

#### `spark magic flush-dns`
按操作系统自动选择刷新命令：
- macOS：`sudo dscacheutil -flushcache` + `sudo killall -HUP mDNSResponder`
- Windows：`ipconfig /flushdns`
- Linux：依次尝试 `systemctl restart systemd-resolved`、`service nscd restart`、`service dnsmasq restart`、`rndc flush`

#### `spark magic pip {list,use,current}`
切换 pip 镜像源，支持：`default` / `tsinghua` / `aliyun` / `douban` / `ustc` / `tencent`。配置写入 `~/.pip/pip.conf` 的 `[global].index-url`，并设置 `trusted-host`。

#### `spark magic go {list,use,current}`
切换 Go module proxy，支持：`default` / `aliyun` / `tsinghua` / `goproxy` / `ustc` / `nju`。通过 `go env -w GOPROXY=...` 设置。

#### `spark magic node {list,use,current}`
切换 npm registry，支持：`default` / `taobao` / `aliyun` / `tencent` / `huawei` / `ustc`。通过 `npm config set registry <url>` 设置。

---

### `spark docs` — 文档管理

```bash
spark docs init                    # 创建 docs 目录结构
spark docs site                    # 初始化 docmd 站点配置
```

| 选项（共享） | 说明 |
|------|------|
| `--root` | 项目根目录（默认 `.`） |

#### `spark docs init`
创建标准结构（跳过已存在的目录/文件）：

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
从 `git remote get-url origin` 自动检测项目标题与 GitHub Pages URL，写入 `docmd.config.js`；若 `docmd` 未安装则通过 `npm install -g @docmd/core` 全局安装；缺 `package.json` 时通过 `npm init -y` 初始化；执行 `npm install`。

---

### `spark witr` — 进程诊断

进程为何在运行的诊断工具，来自 `internal/witr/app`：

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

子包：`launchd`、`output`、`pipeline`、`proc`、`source`、`target`、`tools`、`tui`、`version`；模型在 `pkg/witr/model`。

---

## 构建与测试

### 构建命令

```bash
make build          # 编译 + 打 version/commit/date ldflags + 安装到 ~/.local/bin/spark
make build-linux    # 交叉编译 Linux amd64 (spark_linux)
make build-darwin   # 交叉编译 macOS amd64 (spark_darwin)
make clean          # 移除二进制与构建产物
make install        # 同 build
make install-only   # 仅复制已有二进制到 ~/.local/bin（不动 source）
make verify-install # 对比 ~/.local/bin/spark 与源 spark.exe 的 sha256/大小/mtime
```

`task` (Taskfile) 的等价命令：

```bash
task build          # 等价 make build（包括 Windows 的 spark.exe + spark 同步）
task install        # 等价 task build
task install-binary # 仅复制已有 spark.exe 到 ~/.local/bin（不动 source）
task verify-install # 等价 make verify-install
```

**Windows 安装原理**：`~/.local/bin` 下同时存在 `spark.exe` 与去后缀名 `spark`，因为 bash 优先命中后者；install 步骤原子刷新两个文件，并立即打印 sha256 对比避免 stale 影子。

**自检**：

```bash
spark version       # -> spark v0.3.2 / commit 1ef84d7 / build date 2026-07-10T...
spark --version     # -> spark version v0.3.2
```

### 测试命令

```bash
make test           # go test ./... -v
make test-bdd       # ginkgo -v ./internal/...
make lint           # go vet ./...
```

运行单个测试：

```bash
go test ./internal/git/... -v -run TestUpdateRepository
```

---

## 配置文件

配置文件位于 `~/.spark.yaml`，从旧版 `~/.monolize.yaml` 自动迁移。完整示例见 `.spark.yaml.example`：

```yaml
repo-path:
  - ~/workspace
  - ~/projects
  - ./repos

git:
  username: your-name              # spark git config / init 默认值
  email: your-email@example.com
  scanner:
    db: ~/.innate/feeds.db         # spark git scan 默认 SQLite 路径

task_dir: ~/tasks                  # spark task --task-dir
github_owner: your-github-username # spark task --owner
work_dir: ~/workspace              # spark task --work-dir

default_branch: main
auto_commit: true
```

配置键命名转换：`~/.spark.yaml` 中使用 snake_case（`task_dir`、`github_owner`、`work_dir`、`repo_path`），通过 `viper.BindPFlag` 与持久 flag 关联。结构体 tag 中习惯仍使用 camelCase。脚本相关：

```yaml
spark:
  scripts_dir: scripts            # spark script run 搜索目录
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

配置键优先级：`--config` flag → `$HOME/.spark.yaml` → 环境变量（`viper.AutomaticEnv`）。

---

## Spark Skills（外部）

> ⚠️ Skill 集合位于 **外部仓库** `variableway/spark-cli` 的 `spark-skills/` 目录，**不包含在本仓库内**。请按官方仓库说明安装：

| Skill | 描述 |
|-------|------|
| `github-task-workflow` | GitHub 任务工作流管理 |
| `spark-task-init` | `spark task` 初始化辅助 |

```bash
git clone https://github.com/variableway/spark-cli
cd spark-cli/spark-skills
./install.sh kimi        # 或 ./install.sh claude-code
```

---

## 助手指令参考

本项目保持高内聚、低耦合的 Go 代码风格。在进行后续开发时，请务必：

1. **代码风格**
   - 遵循 Go 标准代码规范
   - 不添加注释（除非明确要求）
   - 使用现有的库和工具模式（Cobra + Viper + PTerm + Ginkgo/Gomega）

2. **测试要求**
   - 新功能必须添加 BDD 风格测试
   - 测试文件以 `_test.go` 结尾，测试套件（`*_suite_test.go`）注册 Ginkgo runner
   - 测试覆盖：`config` / `git`（含 `scanner`）/ `script` / `task` / `github` / `gitlab` / `witr/output`

3. **构建一致性**
   - 优先更新 `Makefile` 以保持构建一致性
   - 确保 `.vscode` 配置的通用性
   - 提交前运行 `make lint` 和 `make test`

4. **文档更新**
   - 新增/修改命令时同步更新 `docs/usage/` 对应文档与本 `AGENTS.md`
   - 保持 `AGENTS.md` 命令层级与实际 `cmd/` / `internal/` 实现一致
   - 文档主要为中文 UI；命令行/代码标识符保持英文
