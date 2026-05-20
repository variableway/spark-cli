# spark git — 命令规格

Git 仓库管理命令组。

## 父命令

```
spark git
```

无参数，无标志。

---

## spark git update

更新所有 Git 仓库到最新版本。扫描配置中 `repo-path` 下的所有仓库，执行 `git pull`。

```
spark git update [-p <path>]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `-p, --path` | stringSlice | `["."]` | 否 | 包含 Git 仓库的目录路径 |

无参数。

---

## spark git init

初始化当前目录为 Git 仓库并创建 GitHub 远程。

```
spark git init [--owner <owner>] [--repo <name>] [--private] [--skip-gh]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--owner` | string | 配置文件 `github-owner` | 是* | GitHub 所有者 |
| `-r, --repo` | string | 当前目录名 | 否 | 仓库名称 |
| `--private` | bool | `false` | 否 | 创建私有仓库 |
| `--skip-gh` | bool | `false` | 否 | 跳过 `gh repo create` |

\* `--owner` 可从 `~/.spark.yaml` 中的 `github-owner` 配置读取。

**流程**: `git init` → `git config` → submodule 扫描 → `.gitignore` → `git commit` → `gh repo create --push`

---

## spark git submodule add

添加 Git 仓库为子模块。支持两种模式：

1. 本地模式：将目录下已有的 Git 仓库添加为子模块，无需重新克隆
2. 远程模式：将远程 Git 仓库克隆并添加为子模块

### 本地模式

```
spark git submodule add [-p <path>]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `-p, --path` | string | `.` | 否 | 包含 Git 仓库的目录路径 |

无参数。

**智能检测行为**：

| 场景 | 输出 |
|------|------|
| 目标已是 submodule（160000） | `Skipping <name>: already as submodule` |
| 目标与父仓库 URL 相同（worktree） | `Skipping <name>: already as submodule` |
| 目录存在但不是 submodule | `Skipping <name>: directory already exists (use 'git submodule add' manually)` |
| 正常添加 | `Adding submodule: <name> (<url>)` |

### 远程模式

```
spark git submodule add <repo-url> [-n <name>] [-p <path>]
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `repo-url` | string | 是 | 远程仓库 URL（HTTPS 或 SSH） |

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `-n, --name` | string | 仓库名 | 否 | 子模块路径名称 |
---

## spark git sync

同步当前仓库中所有 Submodule 到最新版本。

```
spark git sync [repo-path]
```

| 参数 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `repo-path` | string | `.` | 否 | 仓库路径 |

**流程**：
1. `git fetch --all` — 获取所有远程最新代码
2. `git submodule update --init` — 初始化缺失的子模块（从 `.gitmodules` 中读取）
3. `git submodule update --remote --merge` — 更新所有子模块到最新版本并合并

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

克隆 GitHub 组织或用户下的所有仓库。自动检测账号类型。

```
spark git batch-clone <account-name-or-url> [--ssh] [--include <pattern>] [--exclude <pattern>] [-o <dir>]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--ssh` | bool | `false` | 否 | 使用 SSH URL 克隆 |
| `--include` | string | | 否 | 仅包含匹配的仓库（逗号分隔） |
| `--exclude` | string | | 否 | 排除匹配的仓库（逗号分隔） |
| `--include-forks` | bool | `false` | 否 | 包含 fork 的仓库 |
| `-o, --output` | string | `.` | 否 | 克隆输出目录 |

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `account-name-or-url` | string | 是 | 组织名、用户名或 URL |

---

## spark git update-org-status

更新组织 README 中的仓库状态列表。

```
spark git update-org-status <org-name-or-url> [--dry-run] [--update-dot-github] [--section <name>] [-o <path>] [--skip-push]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `-o, --output` | string | `.github/README.md` | 否 | 输出文件路径 |
| `--dry-run` | bool | `false` | 否 | 仅打印不写入 |
| `--update-dot-github` | bool | `false` | 否 | 直接更新组织的 .github 仓库 |
| `--section` | string | `Project List` | 否 | README 中更新的章节名 |
| `--skip-push` | bool | `false` | 否 | 跳过 git commit 和 push |

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `org-name-or-url` | string | 是 | 组织名或 URL |
