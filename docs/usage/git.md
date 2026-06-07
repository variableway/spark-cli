# spark git — Git 仓库管理

管理多个 Git 仓库、初始化项目、同步子模块。

## 命令速查

```bash
spark git update                              # 更新所有仓库
spark git clone <url-or-slug> [dir] [-- <git-args>] # 克隆 GitHub 仓库（默认 SSH）
spark git submodule add [-p <path>]                # 添加现有仓库为子模块
spark git submodule add <repo-url> [-n <name>]     # 添加远程仓库为子模块
spark git submodule init [-j <n>] [-r]             # 初始化（克隆）所有子模块
spark git submodule status                         # 查看子模块状态
spark git submodule ensure-ssh                     # HTTPS → SSH URL 转换
spark git sync [./repo]                   # 同步子模块
spark git gitcode                             # 添加 Gitcode 远程
spark git init [--owner <owner>] [--skip-gh]   # 初始化仓库并创建 GitHub 远程
spark git config [--username --email]         # 配置 Git 用户
spark git url [repo-path]                     # 查看远程 URL
spark git batch-clone <account> [-o <dir>]    # 克隆用户/组织所有仓库
spark git update-org-status <org> [--dry-run] # 更新组织 README
spark git issues [-r <owner/repo>] (-d <dir> | -f <file>) # 从文档/任务创建 Issue
spark git push-all                            # 提交并推送所有仓库的更改
```

---

## spark git clone

使用 GitHub CLI (`gh repo clone`) 克隆单个 GitHub 仓库，默认通过 SSH 连接，可减少 HTTPS 被干扰或不稳定导致的失败。

| 输入格式 | 示例 |
|---|---|
| HTTPS URL | `https://github.com/owner/repo.git` |
| SSH URL | `git@github.com:owner/repo.git` |
| 简写域名 | `github.com/owner/repo` |
| owner/repo | `Nutlope/pdf-to-interactive-lesson` |

```bash
# 从 HTTPS URL 克隆
spark git clone https://github.com/Nutlope/pdf-to-interactive-lesson.git

# 使用 owner/repo 简写
spark git clone Nutlope/pdf-to-interactive-lesson

# 指定本地目录名
spark git clone Nutlope/pdf-to-interactive-lesson my-lesson

# 透传额外参数给 git clone（需用 -- 分隔）
spark git clone https://github.com/owner/repo.git -- --branch main --depth 1
spark git clone https://github.com/owner/repo.git my-dir -- --branch main --depth 1
```

**实现细节**：命令会把输入解析为 `owner/repo`，然后执行 `gh repo clone owner/repo [directory] [-- <git-args>...]`。`gh` 在已登录状态下默认使用 SSH URL。

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

## spark git submodule add

将本地 Git 仓库添加为子模块，或将远程仓库克隆为子模块。

### 模式 1：添加本地仓库为子模块

扫描指定目录中的 Git 仓库，将它们添加为子模块，无需重新克隆。

| 标志 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `-p, --path` | | `.` | 包含 Git 仓库的目录路径 |

```bash
spark git submodule add ./repos                       # 将本地文件夹中所有 GitHub 仓库添加为 submodule
spark git submodule add ./spark-cli                  # 将指定目录作为子模块添加
```

**智能检测行为**：

| 场景 | 输出 |
|------|------|
| 目标已是 submodule（160000） | `Skipping <name>: already as submodule` |
| 目标与父仓库 URL 相同（worktree） | `Skipping <name>: already as submodule` |
| 目录存在但不是 submodule | `Skipping <name>: directory already exists (use 'git submodule add' manually)` |
| 正常添加 | `Adding submodule: <name> (<url>)` |

### 模式 2：添加远程仓库为子模块

克隆远程 Git 仓库并将其添加为子模块。

| 标志 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `-n, --name` | string | repo 名 | 子模块路径名称（远程模式） |

```bash
# 添加远程仓库（使用默认路径名）
spark git submodule add https://github.com/user/repo

# 添加远程仓库并指定路径名
spark git submodule add https://github.com/user/repo --name my-submodule

# 使用 SSH URL
spark git submodule add git@github.com:user/repo.git

# 使用简写格式（GitHub）
spark git submodule add user/repo
```

---

## spark git submodule init

初始化（克隆）所有已注册但尚未检出的子模块。

| 标志 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `-j, --parallel` | | `1` | 并行克隆 worker 数 |
| `-r, --recursive` | | `false` | 同时初始化嵌套子模块 |
| `--name` | | | 仅初始化指定名称的子模块 |

```bash
spark git submodule init                         # 初始化所有子模块
spark git submodule init -j 4                    # 4 路并行初始化
spark git submodule init --recursive             # 含嵌套子模块
spark git submodule init --name spark-cli        # 仅初始化指定子模块
```

**注意**：`init` 仅负责克隆，不会执行 merge 或分支切换。需要同步到最新用 `spark git sync`。

---

## spark git submodule status

以表格形式展示所有子模块的状态。

```bash
spark git submodule status
```

**输出示例**：
```
PATH                           INIT       COMMIT       BRANCH
---------------------------------------------------------------------------
fire-skills-base               ✅         945082af     heads/main
innate-websites                ❌         119324a8         
spark-cli                      ✅         43568d24     heads/main
```

---

## spark git submodule ensure-ssh

将 `.gitmodules` 中所有 HTTPS GitHub URL 替换为 SSH 格式。适用于 HTTPS 连接不稳定的环境。

```bash
spark git submodule ensure-ssh
```

**效果**：
- `https://github.com/owner/repo.git` → `git@github.com:owner/repo.git`
- 同时更新父仓库的 `origin` remote URL
- 修改 `.gitmodules` 文件，需 commit 保存

---

## spark git sync

同步 Mono 仓库中所有子模块到最新版本。

| 标志 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `-r, --recursive` | | `false` | 递归同步嵌套子模块 |

```bash
spark git sync ./my-repo                       # 同步指定仓库
spark git sync --recursive                     # 含嵌套子模块
```

**流程**：
1. `git fetch --all` — 获取所有远程最新代码
2. `git submodule update --init` — 初始化缺失的子模块（从 `.gitmodules` 中读取）
3. `git submodule update --remote --merge` — 更新所有子模块到最新版本并合并

**注意**：步骤 2 使用并行初始化逻辑（串行模式），失败不中断后续步骤。

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

## spark git init

初始化当前目录为 Git 仓库并创建 GitHub 远程。

**流程**:
1. `git init` — 初始化本地仓库
2. `git config user.name/email` — 从 `~/.spark.yaml` 读取并配置
3. 扫描子目录中的 GitHub 仓库，自动添加为 `git submodule`
4. 生成 `.gitignore` — 包含常见忽略规则
5. `git commit` — 创建初始提交（`gh repo create --push` 需要）
6. `gh repo create` — 创建 GitHub 远程仓库并推送

```bash
spark git init --owner variableway              # 初始化并创建远程仓库
spark git init --owner variableway --private    # 创建私有仓库
spark git init --skip-gh --owner variableway    # 仅本地初始化
```

| 标志 | 默认值 | 说明 |
|------|--------|------|
| `--owner` | 配置文件中的 `github-owner` | GitHub 所有者 |
| `-r, --repo` | 当前目录名 | 仓库名称 |
| `--private` | `false` | 创建私有仓库 |
| `--skip-gh` | `false` | 跳过 `gh repo create` |

**配置文件** (`~/.spark.yaml`):

```yaml
github-owner: your-username

git:
  username: Your Name
  email: your@email.com
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

## spark git push-all

扫描指定目录中的所有 Git 仓库，自动提交并推送所有更改。

| 标志 | 默认值 | 说明 |
|------|--------|------|
| `-p, --path` | `.` | 包含 Git 仓库的目录路径（可多次指定） |

```bash
spark git push-all                            # 推送所有仓库的更改
spark git push-all -p ~/workspace             # 指定目录
```

**行为**：
- 跳过非 GitHub 仓库
- 跳过无更改的仓库
- 自动 `git add -A` → `git commit` → `git push`
- 遇到冲突时提示并继续处理下一个仓库

---

## 相关命令

- [任务管理](./task.md)
