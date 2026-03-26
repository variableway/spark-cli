# AGENTS.md

本文档记录了 AI 助手在本项目中执行的关键任务、系统集成工作以及完整的功能说明。

## 项目概述

**Monolize** 是一个 CLI 工具，用于管理多个 Git 仓库。它提供以下核心功能：

1. **多仓库更新** - 批量更新多个 Git 仓库到最新版本
2. **Mono-repo 创建** - 将多个仓库整合为一个带有子模块的 Mono 仓库
3. **子模块同步** - 同步 Mono 仓库中的所有子模块
4. **AI Agent 配置管理** - 管理多种 AI Agent（Claude Code、Codex、Kimi、GLM）的配置文件
5. **任务管理** - 任务分发、同步和 GitHub 仓库创建
6. **Gitcode 远程管理** - 为仓库添加 Gitcode 远程地址

## 技术栈

- **语言**: Go 1.24+
- **CLI 框架**: [Cobra](https://github.com/spf13/cobra) + [Viper](https://github.com/spf13/viper)
- **终端 UI**: [pterm](https://github.com/pterm/pterm) + 自定义 TUI 组件
- **测试框架**: [Ginkgo](https://github.com/onsi/ginkgo) + [Gomega](https://github.com/onsi/gomega) (BDD 风格)
- **构建系统**: Makefile (跨平台支持)

## 项目结构

```
monolize/
├── cmd/                    # CLI 命令定义
│   ├── root.go            # 根命令和全局配置
│   ├── create.go          # mono-repo 创建命令
│   ├── update.go          # 仓库更新命令
│   ├── sync.go            # 子模块同步命令
│   ├── agent.go           # AI Agent 配置管理
│   ├── task.go            # 任务管理命令
│   └── gitcode.go         # Gitcode 远程管理
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
| `--config` | 指定配置文件 (默认: `$HOME/.monolize.yaml`) |
| `-p, --path` | 指定要扫描的目录路径 (可多次使用) |

### 核心命令

#### `monolize update`
扫描指定目录中的所有 Git 仓库并更新到最新版本。

```bash
monolize update -p /path/to/repos
monolize update -p ~/workspace -p ~/projects
```

详细文档: [docs/usage/update.md](docs/usage/update.md)

#### `monolize create`
创建一个 Mono 仓库，将所有找到的仓库作为子模块添加。

```bash
monolize create -p /path/to/repos -n my-mono-repo -o ./output
```

| 选项 | 说明 |
|------|------|
| `-n, --name` | Mono 仓库名称 (默认: `mono-repo`) |
| `-o, --output` | 输出路径 (默认: 当前目录) |

详细文档: [docs/usage/create.md](docs/usage/create.md)

#### `monolize sync`
同步 Mono 仓库中的所有子模块到最新版本。

```bash
monolize sync /path/to/mono-repo
```

详细文档: [docs/usage/sync.md](docs/usage/sync.md)

### AI Agent 管理

#### `monolize agent`
管理多种 AI Agent 的配置文件。

支持的 Agent:
- **claude-code** - Claude Code CLI
- **codex** - OpenAI Codex
- **kimi** - Kimi CLI
- **glm** - GLM (智谱 AI)

```bash
monolize agent list                    # 列出所有支持的 Agent
monolize agent view claude-code        # 查看配置
monolize agent edit kimi               # 编辑配置
monolize agent edit claude-code --tui  # TUI 模式选择配置文件
```

详细文档: [docs/usage/agent.md](docs/usage/agent.md)

### 任务管理

#### `monolize task`
任务分发和同步管理。

```bash
monolize task list --task-dir ./tasks
monolize task dispatch my-task --task-dir ./tasks --owner myuser
monolize task sync my-task --task-dir ./tasks --work-path ./workspace
```

支持 `--tui` 标志启用交互式终端 UI。

详细文档: [docs/usage/task.md](docs/usage/task.md)

### Gitcode 管理

#### `monolize gitcode`
为 GitHub 仓库添加 Gitcode 作为远程地址。

```bash
monolize gitcode -p /path/to/repos
monolize gitcode -p ~/workspace --url https://custom.gitcode.url
```

详细文档: [docs/usage/gitcode.md](docs/usage/gitcode.md)

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

配置文件位于 `~/.monolize.yaml`，支持以下配置项：

```yaml
path:
  - /path/to/repos
  - /another/path

task-dir: /path/to/tasks
github-owner: your-username
work-dir: ./workspace
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
