# Git 仓库管理

## 功能概述

`spark git` 提供多仓库 Git 管理能力，涵盖批量更新、仓库初始化、子模块管理、Gitcode 远程配置、组织仓库克隆等功能。

## 核心能力

### 多仓库批量更新

扫描配置目录下所有 Git 仓库，执行批量 `git pull`。适合同时维护多个仓库的日常更新。

```bash
spark git update -p ~/workspace
```

### Submodule 管理

将本地 GitHub 仓库或远程 URL 添加为 Submodule，支持初始化、状态查看、URL 重写、批量同步。

```bash
# 添加现有本地仓库为子模块
spark git submodule add ./path/to/repos

# 添加远程仓库为子模块
spark git submodule add https://github.com/user/repo
spark git submodule add https://github.com/user/repo --name custom-folder

# 初始化所有未克隆的子模块
spark git submodule init
spark git submodule init -j 4             # 4 路并行初始化
spark git submodule init --recursive      # 含嵌套子模块
spark git submodule init --name spark-cli # 仅初始化指定子模块

# 查看子模块状态
spark git submodule status

# HTTPS -> SSH URL 转换
spark git submodule ensure-ssh

# 同步所有 Submodule 到最新
spark git sync ./my-mono
spark git sync --recursive
```

**核心改进**：

- `init` 分离了初始化和远程更新，不强行 merge。支持 `-j` 并行克隆
- `status` 用表格展示每个子模块的初始化状态、commit、分支
- `ensure-ssh` 一键将 `.gitmodules` 中所有 HTTPS URL 替换为 SSH
- `git init` 递归扫描嵌套目录（如 `projects/innate-ai-art`），最深 3 层

### Gitcode 远程集成

为仓库自动添加 Gitcode（https://gitcode.com）远程仓库，实现 GitHub ↔ Gitcode 双向同步。

```bash
spark git gitcode -p ~/workspace
```

### 仓库初始化

一键初始化 Git 仓库并创建 GitHub 远程：`git init` → 配置用户 → 递归扫描子目录（最深 3 层）添加 submodule → 生成 `.gitignore` → 初始提交 → `gh repo create --push`。

```bash
spark git init --owner variableway              # 初始化并创建远程仓库
spark git init --owner variableway --private    # 创建私有仓库
spark git init --skip-gh --owner variableway    # 仅本地初始化
```

### 批量克隆

克隆 GitHub 组织或用户下所有仓库，或更新 README 中的仓库状态列表。

```bash
# 克隆组织仓库
spark git batch-clone variableway -o ./repos

# 克隆用户仓库
spark git batch-clone jackwener -o ./repos

# 更新组织状态
spark git update-org-status variableway --update-dot-github
```

### Markdown 创建 Issue

统一使用 `spark git issues` 命令创建 GitHub Issue，支持两种输入模式：

- 目录模式：读取目录下所有 Markdown 文件，每个文件创建一个 Issue
- 任务模式：读取单个任务文件，按 `# Task <id>` / `## Task <id>` 分段创建多个 Issue

```bash
# 目录模式
spark git issues -d ./docs -r variableway/spark-cli

# 任务模式
spark git issues -f tasks/issues/task-bug-fix.md -r variableway/spark-cli

# 自动识别当前仓库 + 预览
spark git issues -f tasks/issues/task-bug-fix.md --dry-run
```

## 使用参数

| 参数 | 说明 |
|------|------|
| `-p, --path` | 指定扫描目录（支持多个），默认 `["."]` |
| `-p, --path` | 包含 Git 仓库的目录，默认 `.` |
| `-n, --name` | 子模块路径名称（远程模式），默认仓库名 |
| `-o, --output` | 输出路径 |
| `--ssh` | 使用 SSH 克隆（batch-clone） |
| `--owner` | GitHub 所有者（init），默认从配置文件读取 |
| `--private` | 创建私有仓库（init） |
| `--skip-gh` | 跳过 GitHub 远程创建（init） |
| `--include` / `--exclude` | 包含/排除匹配模式（batch-clone） |
| `-r, --repo` | 目标仓库（未指定时自动从当前仓库解析） |
| `-d, --dir` | 文档目录（目录模式） |
| `-f, --file` | 任务文件（任务模式） |
| `-l, --labels` | Issue 标签（逗号分隔） |
| `--dry-run` | 仅预览，不创建 Issue |

## 依赖

- `git` 命令行工具
- `gh` CLI（issues、batch-clone、update-org-status 需要 GitHub API 访问）

## 相关文档

- [Git 命令规格](../spec/git.md)
- [Git 使用指南](../usage/git.md)
