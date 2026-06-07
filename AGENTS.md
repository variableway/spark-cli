# AGENTS.md

本文档记录了 AI 助手在本项目中执行的关键任务、系统集成工作以及完整的功能说明。

## 项目概述

**Spark** 是一个 CLI 工具，用于管理多个 Git 仓库。它提供以下核心功能：

1. **多仓库更新** - 批量更新多个 Git 仓库到最新版本
2. **Submodule 管理** - 将本地仓库或远程 URL 添加为子模块
3. **子模块同步** - 同步 Mono 仓库中的所有子模块
4. **Git 用户配置** - 配置仓库的 Git 用户信息
5. **任务管理** - 任务分发、同步和 GitHub 仓库创建
6. **Gitcode 远程管理** - 为仓库添加 Gitcode 远程地址
7. **系统工具** - DNS 缓存刷新、包管理器镜像源切换、项目目录清理
8. **文档管理** - 初始化文档结构和 docmd 站点配置
9. **进程诊断** - 检查进程或端口为何在运行（witr）

## 技术栈

- **语言**: Go 1.24+
- **CLI 框架**: [Cobra](https://github.com/spf13/cobra) + [Viper](https://github.com/spf13/viper)
- **终端 UI**: [pterm](https://github.com/pterm/pterm) + 自定义 TUI 组件
- **测试框架**: [Ginkgo](https://github.com/onsi/ginkgo) + [Gomega](https://github.com/onsi/gomega) (BDD 风格)
- **构建系统**: Makefile (跨平台支持)

## 项目结构

```
spark/
├── cmd/                    # CLI 命令定义
│   ├── root.go            # 根命令和全局配置
│   ├── task.go            # 任务管理命令
│   └── git/               # Git 相关命令
│       ├── git.go         # Git 父命令
│       ├── config.go      # Git 用户配置
│       ├── update.go      # 仓库更新命令
│       ├── submodule.go   # 子模块管理命令
│       ├── sync.go        # 子模块同步命令
│       └── gitcode.go     # Gitcode 远程管理
├── internal/              # 内部业务逻辑
│   ├── config/            # 配置管理
│   ├── git/               # Git 操作封装
│   ├── task/              # 任务管理器
│   └── tui/               # 终端 UI 组件
├── docs/                  # 文档
│   ├── usage/             # 使用说明文档
│   └── tasks/             # 任务相关文档
├── .vscode/               # VS Code 配置
├── Makefile               # 构建脚本
└── main.go                # 入口文件
```

## 自动化任务记录

### 1. BDD 测试集成 (2026-02-26)
- **任务**: 为 `internal` 包添加 BDD 风格的单元测试。
- **工具**: 引入了 `Ginkgo` 和 `Gomega` 框架。
- **覆盖范围**: `internal/config` 和 `internal/git`。
- **验证**: 所有测试已通过 `make test-bdd` 验证。

### 2. 跨平台 Makefile 构建 (2026-02-26)
- **任务**: 创建支持 Windows, Linux, Mac 的构建系统。
- **功能**:
    - 自动 OS 检测。
    - 交叉编译支持 (`build-linux`, `build-darwin`)。
    - 统一的清理和测试接口。

### 3. VS Code 环境标准化 (2026-02-26)
- **任务**: 优化 `.vscode` 目录配置。
- **成果**:
    - `tasks.json`: 与 Makefile 深度绑定。
    - `launch.json`: 提供标准化的调试模板。
    - `settings.json`: 统一 Go 语言开发规范。

## CLI 命令完整列表

### 全局选项

| 选项 | 说明 |
|------|------|
| `--config` | 指定配置文件 (默认: `$HOME/.spark.yaml`) |
| `-p, --path` | 指定要扫描的目录路径 (可多次使用) |

### Git 仓库管理

#### `spark git`
Git 仓库管理命令的父命令，包含以下子命令：

```bash
spark git update       # 更新多个仓库
spark git clone        # 克隆 GitHub 仓库（默认 SSH）
spark git submodule add     # 添加现有仓库为子模块
spark git sync    # 同步子模块
spark git gitcode      # 添加 Gitcode 远程
spark git config       # 配置 Git 用户
spark git url          # 获取仓库 URL
spark git init         # 初始化仓库并创建 GitHub 远程
spark git batch-clone  # 克隆用户/组织所有仓库
spark git issues       # 从 Markdown 文档/任务创建 GitHub Issue
spark git push-all     # 提交并推送所有仓库的更改
```

#### `spark git clone`
使用 `gh repo clone` 克隆 GitHub 仓库，默认走 SSH 协议。

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

#### `spark git update`
扫描指定目录中的所有 Git 仓库并更新到最新版本。

```bash
spark git update -p /path/to/repos
spark git update -p ~/workspace -p ~/projects
```

详细文档: [docs/usage/update.md](docs/usage/update.md)

#### `spark git submodule`
将本地 Git 仓库添加为子模块，或克隆远程仓库并添加为子模块。

**本地模式**：
```bash
spark git submodule add                    # 添加当前目录下的仓库
spark git submodule add -p /path/to/repos  # 添加指定目录下的仓库
```

**远程模式**：
```bash
spark git submodule add https://github.com/user/repo           # 添加远程仓库
spark git submodule add https://github.com/user/repo --name my-submodule  # 指定路径名
spark git submodule add git@github.com:user/repo.git           # 使用 SSH URL
```

| 选项 | 说明 |
|------|------|
| `-n, --name` | 子模块路径名称 (默认: 仓库名) |

#### `spark git sync`
同步当前仓库中所有子模块到最新版本。

```bash
spark git sync ./my-repo
```

#### `spark git gitcode`
为 GitHub 仓库添加 Gitcode 作为远程地址。

```bash
spark git gitcode -p /path/to/repos
spark git gitcode -p ~/workspace --url https://custom.gitcode.url
```

详细文档: [docs/usage/gitcode.md](docs/usage/gitcode.md)

#### `spark git init`
初始化当前目录为 Git 仓库并创建 GitHub 远程仓库。

```bash
spark git init --owner variableway              # 初始化并创建远程仓库
spark git init --owner variableway --private    # 创建私有仓库
spark git init --skip-gh --owner variableway    # 仅本地初始化，跳过 GitHub
```

| 选项 | 说明 |
|------|------|
| `--owner` | GitHub 所有者 (默认: 从配置文件读取) |
| `-r, --repo` | 仓库名称 (默认: 当前目录名) |
| `--private` | 创建私有仓库 |
| `--skip-gh` | 跳过创建 GitHub 远程仓库 |

#### `spark git config`
配置当前仓库的 Git 用户信息。

```bash
spark git config                              # 查看当前配置
spark git config --username foo --email bar   # 设置用户信息
```

| 选项 | 说明 |
|------|------|
| `--username` | Git 用户名 (默认: 从配置文件读取) |
| `--email` | Git 邮箱 (默认: 从配置文件读取) |

配置优先级：
1. 命令行参数 (`--username`, `--email`)
2. 配置文件 (`~/.spark.yaml` 中的 `git.username` 和 `git.email`)

#### `spark git url`
获取当前仓库的 Git 远程 URL。

```bash
spark git url              # 当前目录
spark git url /path/to/repo
```

#### `spark git batch-clone`
克隆 GitHub 组织或个人账号的所有仓库到本地。

```bash
spark git batch-clone variableway                    # 使用组织名
spark git batch-clone https://github.com/variableway # 使用 URL
spark git batch-clone variableway --ssh              # 使用 SSH
spark git batch-clone variableway -o ./repos         # 指定输出目录
```

| 选项 | 说明 |
|------|------|
| `--ssh` | 使用 SSH URL 而非 HTTPS |
| `--include` | 只克隆匹配模式的仓库 (逗号分隔) |
| `--exclude` | 排除匹配模式的仓库 (逗号分隔) |
| `--include-forks` | 包含 fork 的仓库 |
| `-o, --output` | 输出目录 (默认: 当前目录) |

#### `spark git issues`
从 Markdown 创建 GitHub Issue，支持目录模式和任务文件模式。

```bash
# 目录模式：目录下每个 .md 文件创建一个 Issue
spark git issues -d ./docs -r owner/repo

# 任务模式：按 # Task / ## Task 分段创建 Issue
spark git issues -f tasks/issues/task-bug-fix.md -r owner/repo

# 自动从当前仓库解析 owner/repo
spark git issues -f tasks/issues/task-bug-fix.md --dry-run
```

| 选项 | 说明 |
|------|------|
| `-r, --repo` | 目标仓库（`owner/repo`），未指定时自动解析 |
| `-d, --dir` | Markdown 目录（目录模式） |
| `-f, --file` | 任务文件（任务模式） |
| `-l, --labels` | Issue 标签（逗号分隔） |
| `--dry-run` | 仅预览，不创建 Issue |

#### `spark git update-org-status`
获取 GitHub 组织的所有仓库信息，按 star 数量排序，并更新到 README.md。

```bash
spark git update-org-status variableway                    # 更新本地 .github/README.md
spark git update-org-status variableway --update-dot-github # 更新 .github 仓库
spark git update-org-status https://github.com/variableway # 使用 URL
spark git update-org-status variableway --dry-run          # 预览输出，不写入文件
spark git update-org-status variableway -o ./docs/README.md # 指定输出路径
spark git update-org-status variableway --section "Projects" # 指定 section 名称
spark git update-org-status variableway --skip-push        # 跳过 git push
```

| 选项 | 说明 |
|------|------|
| `--dry-run` | 预览内容，不写入文件 |
| `-o, --output` | 本地模式输出路径 (默认: `.github/README.md`) |
| `--update-dot-github` | 直接更新组织的 .github 仓库 |
| `--section` | 要更新的 section 名称 (默认: "Project List") |
| `--skip-push` | 跳过 git commit 和 push |

**特性：**
- 默认更新本地 `.github/README.md` 文件
- 使用 `--update-dot-github` 直接更新组织的 `.github` 仓库
- 只更新指定的 section，保留其他所有内容不变
- 自动克隆、修改、提交并推送更改

#### `spark git push-all`
扫描指定目录中的所有 Git 仓库，自动提交并推送所有更改。

```bash
spark git push-all                           # 推送所有更改
spark git push-all -p ~/workspace            # 指定目录
```

- 跳过非 GitHub 仓库和无更改的仓库
- 自动 `git add -A` → `git commit` → `git push`
- 遇到冲突时提示并继续处理下一个仓库

### 脚本管理

#### `spark script`
管理和执行自定义脚本。

```bash
spark script list                    # 列出所有可用脚本
spark script run <script-name>       # 执行指定脚本
```

#### `spark script list`
列出所有可用的脚本。

```bash
spark script list
```

脚本来源：
1. `~/.spark.yaml` 中的 `spark.scripts` 配置
2. 当前目录下 `scripts/` 文件夹中的脚本文件

#### `spark script run`
执行指定名称的脚本。

```bash
spark script run hello               # 执行 hello 脚本
spark script run deploy prod         # 执行 deploy 脚本，传入参数 prod
spark script run copy-template my-feature  # 复制模板文件
```

**配置文件示例** (`~/.spark.yaml`):

```yaml
spark:
  scripts_dir: "scripts"  # 脚本目录，默认为 scripts/
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

**支持的脚本类型**:
- Shell: `.sh`, `.bash`, `.zsh`
- Python: `.py`
- Ruby: `.rb`
- Perl: `.pl`
- PowerShell: `.ps1`
- Batch: `.bat`, `.cmd`

**跨平台支持**: Mac、Linux、Windows

### 任务管理

#### `spark task`
任务管理和 issue 实现命令。

```bash
# 初始化任务目录结构
spark task init                    # 创建 tasks/ 目录结构

# 列出所有任务和 issue
spark task list                    # 列出任务目录和 issue 文件

# 创建新 issue
spark task create my-feature       # 创建 tasks/issues/my-feature.md
spark task create my-feature --content "Custom description"

# 删除 issue
spark task delete my-feature       # 删除 issue 文件
spark task delete my-feature --force  # 强制删除不提示

# 实现 issue（使用 kimi CLI）
spark task impl my-feature         # 执行 issue 实现

# 分发和同步任务
spark task dispatch my-task --dest ./workspace
spark task sync my-task --work-path ./workspace
```

| 子命令 | 说明 |
|--------|------|
| `init` | 初始化任务目录结构 |
| `list` | 列出所有任务和 issue |
| `create` | 创建新 issue 文件（文件名空格自动转换为 `-`）|
| `delete` | 删除 issue 文件 |
| `impl` | 实现 issue（使用 kimi CLI）|
| `dispatch` | 分发任务到新目录 |
| `sync` | 同步任务回任务目录 |

**Issue 文件创建说明**:
- 文件名中的空格和下划线会自动转换为 `-`
- `--content` 参数的内容会写入 `## 描述` section

**任务目录结构**:
```
tasks/
├── issues/                # issue 文件目录
├── config/                # 配置任务目录
├── analysis/              # 分析任务目录
├── mindstorm/             # 头脑风暴目录
├── planning/              # 规划任务目录
└── prd/                   # PRD 文档目录
```

支持 `--tui` 标志启用交互式终端 UI。

详细文档: [docs/usage/task.md](docs/usage/task.md)

### 系统工具

#### `spark magic`
系统实用工具命令组。

```bash
spark magic flush-dns              # 刷新 DNS 缓存
spark magic clean                  # 清理 node_modules 和 .venv
spark magic pip list               # 列出 pip 镜像源
spark magic pip use tsinghua       # 切换 pip 镜像源
spark magic pip current            # 查看当前 pip 源
spark magic go list                # 列出 Go module proxy
spark magic go use goproxy         # 切换 Go proxy
spark magic go current             # 查看当前 Go proxy
spark magic node list              # 列出 npm registry
spark magic node use taobao        # 切换 npm registry
spark magic node current           # 查看当前 npm registry
```

#### `spark magic flush-dns`
刷新系统 DNS 缓存，支持 macOS、Windows、Linux。

#### `spark magic clean`
递归清理项目目录中的 `node_modules` 和 `.venv`。

```bash
spark magic clean                  # 清理两者
spark magic clean -m node          # 只清理 node_modules
spark magic clean -m python        # 只清理 .venv
```

| 选项 | 说明 |
|------|------|
| `-m, --mode` | 清理模式：`node`、`python`（默认两者） |

### 文档管理

#### `spark docs`
文档管理命令组。

```bash
spark docs init                    # 创建文档目录结构
spark docs site                    # 初始化 docmd 站点配置
```

#### `spark docs init`
创建标准文档目录结构（`analysis/`、`features/`、`index.md`、`quick-start/`、`README.md`、`spec/`、`tips/`、`usage/`）。

#### `spark docs site`
初始化 docmd 文档站点配置，自动从 git remote 检测项目名称和 GitHub Pages URL，生成 `docmd.config.js`。

### 进程诊断

#### `spark witr`
进程诊断工具（Why Is This Running），检查进程或端口为何在运行。

```bash
spark witr nginx                   # 按名称检查进程
spark witr --pid 1234              # 按 PID 检查
spark witr --port 8080             # 按端口查找进程
spark witr --file /path/to/lock    # 查找占用文件的进程
spark witr --container redis       # 检查容器
spark witr nginx --tree            # 显示进程树
spark witr nginx --env             # 显示环境变量
spark witr nginx --json            # JSON 输出
```

| 选项 | 说明 |
|------|------|
| `--pid` | 按 PID 查找（可多次使用） |
| `--port` / `-o` | 按端口查找（可多次使用） |
| `--file` / `-f` | 按文件查找（可多次使用） |
| `--container` / `-c` | 按容器查找（可多次使用） |
| `--tree` / `-t` | 显示进程祖先树 |
| `--env` | 显示环境变量 |
| `--json` | JSON 格式输出 |
| `--short` / `-s` | 简短输出 |
| `--warnings` | 仅显示警告 |
| `--verbose` | 扩展信息 |
| `--exact` / `-x` | 精确匹配 |
| `--no-color` | 禁用颜色 |

## Spark Skills

个人 Skill 集合仓库，用于增强 spark-cli 的功能。

**仓库地址**: `variableway/spark-cli` 中的 `spark-skills/` 目录

### 已包含 Skills

| Skill | 描述 | 路径 |
|-------|------|------|
| `github-task-workflow` | GitHub 任务工作流管理 | `spark-skills/github-task-workflow/` |
| `spark-task-init` | spark task 初始化 | `spark-skills/spark-task-init-skill/` |

### 使用方式

```bash
# 安装 skills 到各 Agent
cd spark-skills
./install.sh kimi
./install.sh claude-code

# 项目级一键配置
bash spark-skills/setup-project.sh
```

### Skill 目录结构

```
spark-skills/
├── github-task-workflow/     # GitHub 任务工作流 Skill
├── spark-task-init-skill/    # Task 初始化 Skill
├── install.sh                # 安装脚本
└── README.md                 # 说明文档
```

详细文档: [spark-skills/README.md](spark-skills/README.md)

## 构建与测试

### 构建命令

```bash
make build          # 为当前系统编译 (Windows 生成 .exe)
make build-linux    # 交叉编译 Linux 版
make build-darwin   # 交叉编译 macOS 版
make clean          # 清理构建产物
```

### 测试命令

```bash
make test           # 运行所有单元测试
make test-bdd       # 以 BDD 风格运行测试
make lint           # 运行静态检查 (go vet)
```

## 配置文件

配置文件位于 `~/.spark.yaml`，支持以下配置项：

```yaml
repo-path:
  - /path/to/repos
  - /another/path

task-dir: /path/to/tasks
github-owner: your-username
work-dir: ./workspace

git:
  username: your-name      # 默认 Git 用户名
  email: your@email.com    # 默认 Git 邮箱
```

## 助手指令参考

本项目旨在保持高内聚、低耦合的 Go 代码风格。在进行后续开发时，请务必：

1. **代码风格**
   - 遵循 Go 标准代码规范
   - 不添加注释（除非明确要求）
   - 使用现有的库和工具模式

2. **测试要求**
   - 新功能必须添加 BDD 风格测试
   - 测试文件以 `_test.go` 结尾
   - 使用 Ginkgo/Gomega 框架

3. **构建一致性**
   - 优先更新 `Makefile` 以保持构建一致性
   - 确保 `.vscode` 配置的通用性
   - 提交前运行 `make lint` 和 `make test`

4. **文档更新**
   - 新增命令时更新 `docs/usage/` 目录
   - 保持 AGENTS.md 与功能同步
