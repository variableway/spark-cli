# Git 仓库管理

## 功能概述

`spark git` 提供多仓库 Git 管理能力，涵盖批量更新、Mono-repo 创建与同步、Gitcode 远程配置、组织仓库克隆等功能。

## 核心能力

### 多仓库批量更新

扫描配置目录下所有 Git 仓库，执行批量 `git pull`。适合同时维护多个仓库的日常更新。

```bash
spark git update -p ~/workspace
```

### Mono-repo 管理

将多个独立仓库作为 Submodule 合并为一个 Mono-repo，方便统一管理和版本控制。

```bash
# 添加现有本地仓库为子模块
spark git mono add -p /path/to/repos

# 添加远程仓库为子模块
spark git mono add https://github.com/user/repo
spark git mono add https://github.com/user/repo --name custom-folder

# 同步所有 Submodule 到最新
spark git mono sync ./my-mono
```

### Gitcode 远程集成

为仓库自动添加 Gitcode（https://gitcode.com）远程仓库，实现 GitHub ↔ Gitcode 双向同步。

```bash
spark git gitcode -p ~/workspace
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
