# spark git — 命令规格

Git 仓库管理命令组。

## 父命令

```
spark git
```

无参数，无标志。

---

## spark git update

更新所有 Git 仓库到最新版本。扫描配置中 `repo-path` 下的所有仓库，对每个仓库执行 `git fetch --all`，再执行 `git pull origin <当前分支>`。

```
spark git update [-p <path>] [--ssh]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `-p, --path` | stringSlice | `["."]` | 否 | 包含 Git 仓库的目录路径 |
| `--ssh` | bool | `false` | 否 | 强制通过 SSH 更新（临时将 HTTPS GitHub URL 改写为 SSH，不修改仓库配置） |

无参数。

---

## spark git clone

使用 GitHub CLI（`gh repo clone`）克隆单个 GitHub 仓库，默认使用 SSH。

```
spark git clone <url-or-slug> [directory] [-- <git-args>]
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `url-or-slug` | string | 是 | 仓库 URL 或 `owner/repo` 简写 |
| `directory` | string | 否 | 本地克隆目录名 |

无标志。

**行为**：
- 支持的输入格式：`https://github.com/owner/repo.git`、`git@github.com:owner/repo.git`、`github.com/owner/repo`、`owner/repo`
- 输入被解析为 `owner/repo` 后执行 `gh repo clone owner/repo [directory] [-- <git-args>...]`，`gh` 默认使用 SSH URL
- `--` 之后的参数原样透传给 `git clone`

---

## spark git gitcode

为仓库添加 Gitcode 远程仓库。自动将 GitHub URL 转换为 Gitcode URL。

```
spark git gitcode [--url <url>] [-p <path>]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--url` | string | 自动转换 | 否 | 自定义 Gitcode URL |
| `-p, --path` | stringSlice | `["."]` | 否 | 包含 Git 仓库的目录路径 |

无参数。

---

## spark git config

配置当前仓库的 Git 用户信息。

```
spark git config [--username <name>] [--email <email>] [repo-path]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--username` | string | 配置文件值 | 否 | Git 用户名 |
| `--email` | string | 配置文件值 | 否 | Git 邮箱 |

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `repo-path` | string | 否 | 仓库路径，默认 `.` |

---

## spark git url

获取仓库的 Git 远程 URL。

```
spark git url [repo-path]
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `repo-path` | string | 否 | 仓库路径，默认 `.` |

无标志。

---

## spark git batch-clone

根据输入自动识别 GitHub 或 GitLab，克隆组织/用户/群组下的所有仓库。GitHub 走 API 分页；GitLab 优先走 REST API v4（有 token 时），回退到 `glab`，最后再试无凭证 API。

```
spark git batch-clone <account-name-or-url> [--ssh] [--include <pattern>] [--exclude <pattern>] [--include-forks] [-o <dir>] [--token <token>]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--ssh` | bool | `false` | 否 | 使用 SSH URL 克隆 |
| `--include` | string | | 否 | 仅包含匹配的仓库（逗号分隔） |
| `--exclude` | string | | 否 | 排除匹配的仓库（逗号分隔） |
| `--include-forks` | bool | `false` | 否 | 包含 fork 的仓库 |
| `-o, --output` | string | `.` | 否 | 克隆输出目录 |
| `--token` | string | | 否 | GitLab 私有 Token（也可由 `GITLAB_TOKEN` / `GITLAB_PRIVATE_TOKEN` 环境变量或 `~/.spark.yaml` 的 `gitlab.token` 提供）；显式指定时不受 `gitlab.host` 作用域限制 |

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `account-name-or-url` | string | 是 | 组织名、用户名或 URL（GitLab 支持群组/子群组路径，可省略 `https://`） |

**GitLab 实现要点**：

- 群组路径调用 API v4 时必须 URL 编码（`group/sub` → `group%2Fsub`），否则嵌套群组会 404；`include_subgroups=true` 递归拉取
- 私有实例/私有群组未认证时返回 **404 而非 401**，因此错误信息区分「未提供凭证」/「凭证无效或无权访问」/「路径不存在」
- 克隆落盘路径按命名空间相对路径展开（`observability/tenant-observability/argocd-tenant-plugin`），避免子群组同名项目互相覆盖
- Token 优先级：`--token` > `gitlab.token`（`~/.spark.yaml`）> `GITLAB_TOKEN` > `GITLAB_PRIVATE_TOKEN`
- `gitlab.host`（可选）把自动发现的凭证限定到该实例，避免自托管实例的 token 被发往 `gitlab.com`

---

## spark git update-org-status

更新账号 README 中的仓库状态列表。账号既可以是组织，也可以是用户，类型由 GitHub API 自动识别。

```
spark git update-org-status <account-name-or-url> [--dry-run] [--update-dot-github] [--section <name>] [-o <path>] [--skip-push]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `-o, --output` | string | `.github/README.md` | 否 | 输出文件路径 |
| `--dry-run` | bool | `false` | 否 | 仅打印不写入 |
| `--update-dot-github` | bool | `false` | 否 | 直接更新账号的 profile 仓库 |
| `--section` | string | `Project List` | 否 | README 中更新的章节名 |
| `--skip-push` | bool | `false` | 否 | 跳过 git commit 和 push |

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `account-name-or-url` | string | 是 | 账号名或 URL（组织名或用户名，如 `qdriven`） |

**行为**：
- 账号类型通过 GitHub API 自动识别：组织 → profile 仓库为 `<org>/.github`（写入 `README.md` 与 `profile/README.md`）；用户 → profile 仓库为 `<user>/<user>`（写入仓库根目录的 `README.md`）
- 仓库列表分页获取（每页 100 个），因此不受单页数量限制
- 设置 `GITHUB_TOKEN` 可提升 API 速率限制（匿名访问为 60 次/小时）
- fork 仓库不写入表格，也不计入统计
- `--update-dot-github` 会把账号的 profile 仓库克隆到 `$TMPDIR/github-repo-<account>-<ts>`，改写 README 后 commit 并 push

---

## spark git issues

从 Markdown 文档或任务文件创建 GitHub Issue，支持两种模式：

- 目录模式（`-d`）：目录下每个 `.md` 文件创建一个 Issue
- 任务模式（`-f`）：单个文件按 `# Task <id>` / `## Task <id>` 分段，每个分段创建一个 Issue

```
spark git issues [-r <owner/repo>] (-d <dir> | -f <file>) [-l <labels>] [--dry-run]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `-r, --repo` | string | 当前仓库的 `origin` | 否 | 目标仓库（`owner/repo`）；省略时自动从当前仓库的 `origin` 解析 |
| `-d, --dir` | string | | 否 | 目录模式：包含 Markdown 文档的目录 |
| `-f, --file` | string | | 否 | 任务模式：包含任务分段的 Markdown 文件 |
| `-l, --labels` | stringSlice | `[]` | 否 | 为所有 Issue 添加的标签（逗号分隔） |
| `--dry-run` | bool | `false` | 否 | 预览，不创建 Issue |

无参数。`-d` 与 `-f` 互斥，必须且只能指定其一。

---

## spark git push-all

扫描目录中的所有 Git 仓库，自动提交并推送所有更改。

```
spark git push-all [-p <path>]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `-p, --path` | stringSlice | `["."]` | 否 | 包含 Git 仓库的目录路径 |

无参数。

**行为**：
- 跳过非 GitHub 仓库
- 跳过无更改的仓库
- 自动 `git add -A` → `git commit` → `git push`
- 遇到错误打印提示并继续下一个仓库

---

## spark git scan

递归扫描目录中的 Git 仓库，可选从 GitHub/GitLab API 获取元数据，并保存到 SQLite 数据库。

```
spark git scan [folder-path] [-d <db-path>] [--skip-api]
```

| 参数 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `folder-path` | string | `.` | 否 | 要扫描的目录路径 |

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `-d, --db` | string | `~/.innate/feeds.db` | 否 | SQLite 数据库路径 |
| `--skip-api` | bool | `false` | 否 | 跳过 API 调用，仅扫描本地仓库 |

配置项 `git.scanner.db`（`~/.spark.yaml`）可覆盖默认数据库路径。

**行为**：
- 递归查找 `.git` 目录，解析 `origin` 远程 URL
- 支持 GitHub、GitLab、Bitbucket
- 按 `path` upsert 到 SQLite 表 `repos`
- 环境变量 `GITHUB_TOKEN` 用于 GitHub API 认证
