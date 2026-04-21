# spark git — Git 仓库管理

管理多个 Git 仓库、创建 Mono-repo、同步子模块。

## 命令速查

```bash
spark git update                              # 更新所有仓库
spark git mono add [-p <path>]                # 添加现有仓库为子模块
spark git mono add <repo-url> [-n <name>]     # 添加远程仓库为子模块
spark git mono sync <mono-path>               # 同步子模块
spark git gitcode                             # 添加 Gitcode 远程
spark git config [--username --email]         # 配置 Git 用户
spark git url [repo-path]                     # 查看远程 URL
spark git batch-clone <account> [-o <dir>]    # 克隆用户/组织所有仓库
spark git update-org-status <org> [--dry-run] # 更新组织 README
spark git issues [-r <owner/repo>] (-d <dir> | -f <file>) # 从文档/任务创建 Issue
```

---

## spark git update

批量更新指定目录下的所有 Git 仓库到最新版本。

```bash
spark git update                              # 更新当前目录下所有仓库
spark git update -p ~/workspace               # 更新指定目录
spark git update -p ~/ws -p ~/projects        # 多个目录
```

**流程**: 扫描目录 → 查找 `.git` → 逐个 `git pull --rebase` → 输出结果

---

## spark git mono add

将本地 Git 仓库添加为子模块，或将远程仓库克隆为子模块。

### 模式 1：添加本地仓库为子模块

扫描指定目录中的 Git 仓库，将它们添加为子模块，无需重新克隆。

| 标志 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--path` | `-p` | `.` | 包含 Git 仓库的目录 |

```bash
spark git mono add                              # 添加当前目录下的仓库
spark git mono add -p /path/to/repos            # 添加指定目录下的仓库
```

### 模式 2：添加远程仓库为子模块

克隆远程 Git 仓库并将其添加为子模块。

| 标志 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--path` | `-p` | `.` | Mono-repo 目录（默认当前目录） |
| `--name` | `-n` | 仓库名 | 子模块路径名称 |

```bash
# 添加远程仓库（使用默认路径名）
spark git mono add https://github.com/user/repo

# 添加远程仓库并指定路径名
spark git mono add https://github.com/user/repo --name my-submodule

# 使用 SSH URL
spark git mono add git@github.com:user/repo.git

# 使用简写格式（GitHub）
spark git mono add user/repo
```

---

## spark git mono sync

同步 Mono 仓库中所有子模块到最新版本。

```bash
spark git mono sync ./my-mono-repo                 # 同步指定 Mono 仓库
```

---

## spark git gitcode

为 GitHub 仓库自动添加 Gitcode 远程地址。

| 标志 | 默认值 | 说明 |
|------|--------|------|
| `--url` | 自动转换 | 自定义 Gitcode URL |

```bash
spark git gitcode                             # 自动转换 GitHub → Gitcode
spark git gitcode --url https://gitcode.com/user/repo
```

---

## spark git config

配置仓库的 Git 用户信息。

| 标志 | 默认值 | 说明 |
|------|--------|------|
| `--username` | 配置文件值 | Git 用户名 |
| `--email` | 配置文件值 | Git 邮箱 |

```bash
spark git config                              # 使用配置文件中的值
spark git config --username "John" --email "john@example.com"
spark git config /path/to/repo                # 配置指定仓库
```

---

## spark git url

获取仓库的远程 URL。

```bash
spark git url                                 # 当前目录
spark git url /path/to/repo                   # 指定仓库
```

---

## spark git batch-clone

克隆 GitHub 组织或用户的所有仓库。自动检测账号类型（组织或用户）。

| 标志 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--ssh` | | `false` | 使用 SSH URL |
| `--include` | | | 仅包含匹配的仓库（逗号分隔） |
| `--exclude` | | | 排除匹配的仓库（逗号分隔） |
| `--include-forks` | | `false` | 包含 fork 仓库 |
| `--output` | `-o` | `.` | 输出目录 |

```bash
spark git batch-clone variableway               # 克隆组织所有仓库
spark git batch-clone jackwener                 # 克隆用户所有仓库
spark git batch-clone variableway --ssh         # 使用 SSH
spark git batch-clone variableway --include spark --exclude test
spark git batch-clone variableway -o ./repos    # 指定输出目录
```

---

## spark git update-org-status

获取组织仓库列表并更新 README.md。

| 标志 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--output` | `-o` | `.github/README.md` | 输出文件路径 |
| `--dry-run` | | `false` | 预览不写入 |
| `--update-dot-github` | | `false` | 直接更新组织的 .github 仓库 |
| `--section` | | `Project List` | 更新的 section 名称 |
| `--skip-push` | | `false` | 跳过 git push |

```bash
spark git update-org-status variableway                    # 更新本地 README
spark git update-org-status variableway --dry-run          # 预览
spark git update-org-status variableway --update-dot-github # 直接推送
spark git update-org-status variableway --section "My Projects"
```

---

## spark git issues

从 Markdown 文档创建 GitHub Issue，支持两种模式：

- 目录模式：`-d` 指定目录，目录下每个 `.md` 文件创建一个 Issue
- 任务模式：`-f` 指定单文件，按 `# Task <id>` 或 `## Task <id>` 分段创建多个 Issue

仓库参数可通过 `-r` 显式指定；未指定时自动从当前仓库 `origin` 解析 `owner/repo`。

| 标志 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--repo` | `-r` | 自动检测 | 目标仓库（`owner/repo`） |
| `--dir` | `-d` | | Markdown 目录（目录模式） |
| `--file` | `-f` | | 任务文件（任务模式） |
| `--labels` | `-l` | | 为所有 Issue 添加标签（逗号分隔） |
| `--dry-run` | | `false` | 预览，不创建 Issue |

```bash
# 目录模式：每个 Markdown 文件创建一个 Issue
spark git issues -d ./docs -r variableway/spark-cli

# 任务模式：从任务文件按 Task 段落创建 Issue
spark git issues -f tasks/issues/task-bug-fix.md -r variableway/spark-cli

# 自动从当前仓库解析 owner/repo
spark git issues -f tasks/issues/task-bug-fix.md --dry-run
```

## 相关命令

- [Agent 配置](./agent.md)
- [任务管理](./task.md)
