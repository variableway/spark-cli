# Spark

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
spark git update -p /path/to/repos

# 创建 Mono 仓库
spark git create -p /path/to/repos -n my-mono-repo -o ./output

# 同步子模块
spark git sync /path/to/mono-repo

# 添加 Gitcode 远程
spark git gitcode -p /path/to/repos

# 配置 Git 用户
spark git config --username foo --email bar@example.com

# 获取仓库 URL
spark git url

# 克隆 GitHub 组织的所有仓库
spark git clone-org variableway -o ./repos

# 更新组织项目列表到 .github/README.md
spark git update-org-status variableway

# 直接更新 .github 仓库的 README.md
spark git update-org-status variableway --update-dot-github

# 预览更新内容（不写入文件）
spark git update-org-status variableway --dry-run

# 只更新指定 section
spark git update-org-status variableway --section "My Projects"
```

### 脚本执行

```bash
# 列出所有可用脚本
spark script list

# 执行脚本
spark script run list-dirs

# 执行脚本并传递参数
spark script run copy-template my-new-feature
```

### 任务管理

```bash
# 初始化任务目录结构
spark task init

# 列出所有任务和特性
spark task list

# 创建新特性文件（文件名中的空格会自动转换为 -）
spark task create my-feature
spark task create "my feature name"  # 将创建 my-feature-name.md

# 创建带内容的特性文件（内容将写入 ## 描述 section）
spark task create my-feature --content "Custom description"

# 删除特性文件
spark task delete my-feature

# 强制删除（不提示）
spark task delete my-feature --force

# 实现特性（使用 kimi CLI）
spark task impl my-feature

# 分发任务到新目录
spark task dispatch my-feature --dest ./workspace

# 同步任务回任务目录
spark task sync my-feature --work-path ./workspace
```
```

---
Following is not fully tested,under testing now.
---


### AI Agent 配置

```bash
# 列出所有支持的 Agent
spark agent list

# 查看配置
spark agent view claude-code

# 编辑配置
spark agent edit kimi

# Profile 配置模板管理
spark agent profile list
spark agent profile add my-glm --type glm
spark agent use my-glm
```

### 任务管理

```bash
# 列出任务
spark task list --task-dir ./tasks

# 分发任务
spark task dispatch my-task --task-dir ./tasks --owner myuser

# 同步任务
spark task sync my-task --task-dir ./tasks --work-path ./workspace
```

## 配置

配置文件位于 `~/.spark.yaml`：

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
```
  Configuration sections:
   Section        Options                             Used By
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   repo-path      List of paths to scan for repos     git update, git create, git gitcode
   git            username, email                     git config
   task_dir       Task templates directory            task commands
   github_owner   GitHub username for repo creation   task dispatch
   work_dir       Working directory for tasks         task commands
   General        path, default_branch, auto_commit   Various commands
  Usage:
```
ßß
## 开发

```bash
make test           # 运行所有单元测试
make test-bdd       # 以 BDD 风格运行测试
make lint           # 运行静态检查
```

## 文档

详细文档请参见 [AGENTS.md](AGENTS.md) 和 [docs/usage/](docs/usage/) 目录。
