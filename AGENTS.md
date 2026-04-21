# AGENTS.md

本文档记录了 AI 助手在本项目中执行的关键任务、系统集成工作以及完整的功能说明。

## 项目概述

**Spark** 是一个 CLI 工具，用于管理多个 Git 仓库。它提供以下核心功能：

1. **多仓库更新** - 批量更新多个 Git 仓库到最新版本
2. **Mono-repo 管理** - 将多个仓库添加为子模块，统一管理
3. **子模块同步** - 同步 Mono 仓库中的所有子模块
4. **Git 用户配置** - 配置仓库的 Git 用户信息
5. **任务管理** - 任务分发、同步和 GitHub 仓库创建
6. **Gitcode 远程管理** - 为仓库添加 Gitcode 远程地址
7. ~~**AI Agent 配置管理** - 管理多种 AI Agent（Claude Code、Codex、Kimi、GLM）的配置文件~~ (已禁用，待重新设计)

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
│   ├── agent.go           # AI Agent 配置管理
│   ├── agent_profile.go   # Agent Profile 管理
│   ├── task.go            # 任务管理命令
│   └── git/               # Git 相关命令
│       ├── git.go         # Git 父命令
│       ├── config.go      # Git 用户配置
│       ├── update.go      # 仓库更新命令
│       ├── mono.go        # mono 子命令组
│       ├── mono_add.go    # mono add 命令
│       ├── sync.go        # 子模块同步命令
│       └── gitcode.go     # Gitcode 远程管理
├── internal/              # 内部业务逻辑
│   ├── agent/             # AI Agent 管理器
│   ├── config/            # 配置管理
│   ├── git/               # Git 操作封装
│   ├── mono/              # Mono-repo 操作
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
spark git mono add     # 添加现有仓库为子模块
spark git mono sync    # 同步子模块
spark git gitcode      # 添加 Gitcode 远程
spark git config       # 配置 Git 用户
spark git url          # 获取仓库 URL
spark git batch-clone  # 克隆用户/组织所有仓库
spark git issues       # 从 Markdown 文档/任务创建 GitHub Issue
```

#### `spark git update`
扫描指定目录中的所有 Git 仓库并更新到最新版本。

```bash
spark git update -p /path/to/repos
spark git update -p ~/workspace -p ~/projects
```

详细文档: [docs/usage/update.md](docs/usage/update.md)

#### `spark git mono add`
将本地 Git 仓库添加为子模块，或克隆远程仓库并添加为子模块。

**本地模式**：
```bash
spark git mono add                    # 添加当前目录下的仓库
spark git mono add -p /path/to/repos  # 添加指定目录下的仓库
```

**远程模式**：
```bash
spark git mono add https://github.com/user/repo           # 添加远程仓库
spark git mono add https://github.com/user/repo --name my-submodule  # 指定路径名
spark git mono add git@github.com:user/repo.git           # 使用 SSH URL
```

| 选项 | 说明 |
|------|------|
| `-p, --path` | Mono-repo 目录 (默认: 当前目录) |
| `-n, --name` | 子模块路径名称 (默认: 仓库名) |

#### `spark git mono sync`
同步 Mono 仓库中的所有子模块到最新版本。

```bash
spark git mono sync /path/to/mono-repo
```

#### `spark git gitcode`
为 GitHub 仓库添加 Gitcode 作为远程地址。

```bash
spark git gitcode -p /path/to/repos
spark git gitcode -p ~/workspace --url https://custom.gitcode.url
```

详细文档: [docs/usage/gitcode.md](docs/usage/gitcode.md)

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

### AI Agent 管理 (已禁用)

> NOTE: 此功能当前已禁用，命令入口已关闭（`cmd/agent.go` 中 `rootCmd.AddCommand(agentCmd)` 已注释）。待后续重新设计后再启用。

#### `spark agent`
管理多种 AI Agent 的配置文件。

支持的 Agent:
- **claude-code** - Claude Code CLI
- **codex** - OpenAI Codex
- **kimi** - Kimi CLI
- **glm** - GLM (智谱 AI)

```bash
spark agent list                    # 列出所有支持的 Agent
spark agent view claude-code        # 查看配置
spark agent edit kimi               # 编辑配置
spark agent edit claude-code --tui  # TUI 模式选择配置文件

# Profile 配置模板管理
spark agent profile list                    # 列出所有配置模板
spark agent profile add my-glm --type glm   # 创建一个 GLM 模板
spark agent profile edit my-glm             # 编辑模板配置
spark agent use my-glm                      # 将模板应用到当前项目
spark agent current                         # 查看当前项目使用的模板
```

详细文档: [docs/usage/agent.md](docs/usage/agent.md)

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
- 如果存在 `example-issue.md`，会将其作为模板

**任务目录结构**:
```
tasks/
├── example-issue.md       # 示例 issue 模板
├── issues/                # issue 文件目录
├── config/                # 配置任务目录
├── analysis/              # 分析任务目录
├── mindstorm/             # 头脑风暴目录
├── planning/              # 规划任务目录
└── prd/                   # PRD 文档目录
```

支持 `--tui` 标志启用交互式终端 UI。

详细文档: [docs/usage/task.md](docs/usage/task.md)

## Spark Skills

个人 Skill 集合仓库，包含多个 AI Agent Skill，用于增强 spark-cli 的功能。

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
