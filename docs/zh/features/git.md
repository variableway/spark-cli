# Git 仓库管理

## 功能概述

`spark git` 提供多仓库 Git 管理能力，涵盖批量更新、Gitcode 远程配置、组织仓库克隆等功能。一个目录下的多个仓库用 `spark hub registry` 管理。

## 核心能力

### 多仓库批量更新

扫描配置目录下所有 Git 仓库，执行批量 `git fetch --all && git pull`。适合同时维护多个仓库的日常更新。当 HTTPS 连接不稳定时，可加 `--ssh` 强制通过 SSH 更新（仅本次有效，不修改仓库配置的远程地址）。

```bash
spark git update -p ~/workspace
spark git update -p ~/workspace --ssh
```

### Gitcode 远程集成

为仓库自动添加 Gitcode（https://gitcode.com）远程仓库，实现 GitHub ↔ Gitcode 双向同步。

```bash
spark git gitcode -p ~/workspace
```

### 批量克隆

根据输入自动识别 GitHub 或 GitLab，克隆组织/用户/群组下所有仓库，或更新 README 中的仓库状态列表。

```bash
# 克隆 GitHub 组织仓库
spark git batch-clone variableway -o ./repos

# 克隆 GitHub 用户仓库
spark git batch-clone jackwener -o ./repos

# 克隆 GitLab 群组（支持嵌套子群组，可省略 https://）
spark git batch-clone gitlab.com/gitlab-com/gl-infra -o ./repos
spark git batch-clone https://gitlab.example.com/myorg/mygroup --token glpat-xxxx

# 仅克隆名称含指定模式的仓库
spark git batch-clone variableway --include cli,tool --exclude docs

# 更新组织状态
spark git update-org-status variableway --update-dot-github
```

**核心改进**：

- GitLab 群组路径按 API v4 要求 URL 编码，嵌套子群组递归拉取（`include_subgroups=true`）
- 克隆落盘路径按命名空间相对路径展开（如 `observability/tenant-observability/argocd-tenant-plugin`），避免子群组同名项目互相覆盖
- Token 来源优先级：`--token` > `gitlab.token`（`~/.spark.yaml`）> `GITLAB_TOKEN` > `GITLAB_PRIVATE_TOKEN`
- `gitlab.host` 可把自动发现的凭证限定到该实例，避免自托管实例的 token 被发往 `gitlab.com`

### Markdown 创建 Issue

统一使用 `spark git issues` 命令创建 GitHub Issue，支持两种输入模式：

- 目录模式：读取目录下所有 Markdown 文件，每个文件创建一个 Issue
- 任务模式：读取单个任务文件，按 `# Task <id>` / `## Task <id>` 分段创建多个 Issue

```bash
# 目录模式
spark git issues -d ./docs -r variableway/spark-cli

# 任务模式
spark git issues -f ./issues/task-bug-fix.md -r variableway/spark-cli

# 自动识别当前仓库 + 预览
spark git issues -f ./issues/task-bug-fix.md --dry-run
```

### 批量推送更改

扫描所有 GitHub 仓库，自动提交并推送未提交的更改。

```bash
spark git push-all -p ~/workspace
```

- 跳过非 GitHub 仓库和无更改的仓库
- 遇到错误继续处理下一个仓库

### Git 仓库扫描

递归扫描目录中的 Git 仓库，从 API 获取 stars、forks、语言等信息，并保存到 SQLite 数据库。

```bash
spark git scan ~/workspace
spark git scan . --skip-api --db ~/.innate/feeds.db
```

- 默认数据库路径：`~/.innate/feeds.db`
- 可通过 `--db` 或配置项 `git.scanner.db` 自定义
- 设置 `GITHUB_TOKEN` 可提高 GitHub API 速率限制

## 使用参数

| 参数 | 说明 |
|------|------|
| `-p, --path` | 包含 Git 仓库的目录（支持多个），默认 `["."]` |
| `-o, --output` | 输出路径 |
| `--ssh` | 使用 SSH 克隆（batch-clone） |
| `--include` / `--exclude` | 包含/排除匹配模式（batch-clone） |
| `--include-forks` | 包含 fork 仓库（batch-clone） |
| `--token` | GitLab 私有 Token（batch-clone），也可用 `GITLAB_TOKEN` / `GITLAB_PRIVATE_TOKEN` 或 `gitlab.token` |
| `-r, --repo` | 目标仓库（未指定时自动从当前仓库解析） |
| `-d, --dir` | 文档目录（目录模式） |
| `-f, --file` | 任务文件（任务模式） |
| `-l, --labels` | Issue 标签（逗号分隔） |
| `--dry-run` | 仅预览，不创建 Issue |
| `-d, --db` | SQLite 数据库路径（scan），默认 `~/.innate/feeds.db` |
| `--skip-api` | 跳过 API 调用（scan） |

## 依赖

- `git` 命令行工具
- `gh` CLI（issues、GitHub batch-clone、update-org-status 需要 GitHub API 访问）
- GitLab batch-clone 需要 `glab` CLI，或提供 `--token` / `gitlab.token` / `GITLAB_TOKEN`（Token 需 `read_api`，克隆私有仓库还需 `read_repository`）

## 相关文档

- [Git 命令规格](../spec/git.md)
- [Git 使用指南](../usage/git.md)
