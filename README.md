# Monolize

一个用于管理多个 Git 仓库的 CLI 工具。

## 功能特性

1. **多仓库更新** - 批量更新多个 Git 仓库到最新版本
2. **Mono-repo 创建** - 将多个仓库整合为一个带有子模块的 Mono 仓库
3. **子模块同步** - 同步 Mono 仓库中的所有子模块
4. **Git 用户配置** - 配置仓库的 Git 用户信息
5. **AI Agent 配置管理** - 管理多种 AI Agent（Claude Code、Codex、Kimi、GLM）的配置文件
6. **任务管理** - 任务分发、同步和 GitHub 仓库创建
7. **Gitcode 远程管理** - 为仓库添加 Gitcode 远程地址

## 安装

```bash
make build          # 为当前系统编译
make build-linux    # 交叉编译 Linux 版
make build-darwin   # 交叉编译 macOS 版
```

## 快速开始

### Git 仓库管理

```bash
# 更新多个仓库
monolize git update -p /path/to/repos

# 创建 Mono 仓库
monolize git create -p /path/to/repos -n my-mono-repo -o ./output

# 同步子模块
monolize git sync /path/to/mono-repo

# 添加 Gitcode 远程
monolize git gitcode -p /path/to/repos

# 配置 Git 用户
monolize git config --username foo --email bar@example.com

# 获取仓库 URL
monolize git url

# 克隆 GitHub 组织的所有仓库
monolize git clone-org variableway -o ./repos
```

### AI Agent 配置

```bash
# 列出所有支持的 Agent
monolize agent list

# 查看配置
monolize agent view claude-code

# 编辑配置
monolize agent edit kimi

# Profile 配置模板管理
monolize agent profile list
monolize agent profile add my-glm --type glm
monolize agent use my-glm
```

### 任务管理

```bash
# 列出任务
monolize task list --task-dir ./tasks

# 分发任务
monolize task dispatch my-task --task-dir ./tasks --owner myuser

# 同步任务
monolize task sync my-task --task-dir ./tasks --work-path ./workspace
```

## 配置

配置文件位于 `~/.monolize.yaml`：

```yaml
path:
  - /path/to/repos
  - /another/path

task-dir: /path/to/tasks
github-owner: your-username
work-dir: ./workspace

git:
  username: your-name      # 默认 Git 用户名
  email: your@email.com    # 默认 Git 邮箱
```

## 开发

```bash
make test           # 运行所有单元测试
make test-bdd       # 以 BDD 风格运行测试
make lint           # 运行静态检查
```

## 文档

详细文档请参见 [AGENTS.md](AGENTS.md) 和 [docs/usage/](docs/usage/) 目录。
