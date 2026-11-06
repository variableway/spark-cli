---
name: spark-cli
description: spark 命令行工具的使用说明。当用户需要批量更新/克隆 Git 仓库、管理 GitHub Issue、管理项目 registry、扫描并同步 AI Skill、初始化文档站、排查端口占用，或提到 spark / spark-cli / spark git / spark repo / spark skill / spark hub / spark docs / spark magic / spark witr 时使用。
---

# spark CLI 使用说明

`spark` 是一个 Go 写的日常开发自动化 CLI（Cobra + Viper + PTerm），单二进制，
跨平台（macOS / Windows / Linux）。它把「重复、确定、不需要推理」的操作固化成命令，
让 AI 助手用一次命令调用替代反复的 token 消耗。

---

## 0. 先确认二进制可用

```bash
spark version     # -> spark v0.3.2 / commit <sha> / build date <date>
```

没有安装时，从源码构建：

```bash
make build          # 构建 + 安装到 ~/.local/bin/spark
make verify-install # 校验安装的二进制与源码一致
make test           # 跑全部单测
make lint           # go vet 静态检查
```

Windows 上用 `task` 代替 `make`（见 `Taskfile.yml`）：
`task build` / `task build:windows` / `task install`。

## 1. 全局标志与配置

| 标志 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--config` | | `~/.spark.yaml` | 配置文件路径 |
| `--path` | `-p` | `.` | 目标目录（可重复指定） |

配置文件 `~/.spark.yaml`（模板见仓库 `.spark.yaml.example`）：

```yaml
repo-path:              # 批量操作的仓库根目录
  - ~/workspace
git:
  username: your-name
  email: you@example.com
  scanner:
    db: ~/.innate/feeds.db
gitlab:
  host: gitlab.example.com   # 可选：把 token 限定到该实例
  token: glpat-xxxx
github-owner: your-username  # spark git init --owner 的默认值
```

---

## 2. 命令地图：什么场景用哪条命令

```
spark
├── version                  版本信息
├── git                      Git 仓库管理（12 个子命令）
├── repo                     registry 文件驱动的多仓库管理
├── skill                    AI Skill 发现与同步
├── hub                      本地项目注册表（registry/apps.json）
├── script                   自定义脚本
├── magic                    系统工具（DNS / 清理 / 镜像源 / dotfiles）
├── docs                     文档站脚手架
└── witr                     进程/端口占用诊断
```

| 用户想要 | 用这条命令 |
|----------|------------|
| 把一堆仓库更新到最新 | `spark git update` |
| 克隆某个 GitHub 仓库 | `spark git clone <slug-or-url> [dir]` |
| 克隆某组织/用户下所有仓库 | `spark git batch-clone <org-or-user>` |
| 建仓 + 关联 GitHub 远程 | `spark git init --owner <owner>` |
| 用本地仓库/URL 当子模块 | `spark git submodule add ...` |
| 批量提交推送所有仓库 | `spark git push-all` |
| 从 Markdown/任务文件建 Issue | `spark git issues -d <dir>` |
| 更新 profile README 的项目清单 | `spark git update-org-status <org>` |
| 管理一个目录下的多个仓库（不用 submodule） | `spark repo scan` / `clone` / `list` |
| 把本地项目登记进 registry | `spark hub scan` |
| 找到散落各处的 SKILL.md | `spark skill list` / `sync` |
| 搭一个文档站 | `spark docs init` / `spark docs site` |
| 刷 DNS、清 node_modules、切镜像源 | `spark magic ...` |
| 这个端口/进程是谁在跑 | `spark witr --port <port>` |

---

## 3. 常用工作流

### 3.1 批量更新本地仓库

```bash
spark git update -p ~/workspace          # 更新该目录下所有仓库
spark git update -p ~/workspace --ssh    # 强制用 SSH 远程
```

### 3.2 克隆组织下的所有仓库

```bash
spark git batch-clone qdriven                      # 克隆组织全部仓库
spark git batch-clone qdriven --include foo --exclude bar
spark git batch-clone qdriven --include-forks -o ./repos
```

GitLab 群组（支持嵌套子群组，子群组结构会保留）：

```bash
spark git batch-clone https://gitlab.example.com/myorg/mygroup --token glpat-xxxx
```

Token 优先级：`--token` > `~/.spark.yaml` 的 `gitlab.token` > `GITLAB_TOKEN` >
`GITLAB_PRIVATE_TOKEN`。配置了 `gitlab.host` 后，凭证只会发往该实例。

### 3.3 用 registry 管理一个目录下的多个仓库

```bash
spark repo scan ~/workspace                       # 生成 registry_workspace.yaml
spark repo list -f registry_workspace.yaml
spark repo clone -f registry_workspace.yaml       # 克隆全部
spark repo clone -r spark-cli -f registry_workspace.yaml   # 只克隆一个
```

### 3.4 建 Issue

```bash
spark git issues -d ./docs/tasks                  # 每个 .md 一个 Issue
spark git issues -f ./tasks.md                     # 按 "## Task <id>" 分段建多个
spark git issues -f ./tasks.md --dry-run           # 先预览
spark git issues -f ./tasks.md -l bug,feature      # 打标签
```

未指定 `-r owner/repo` 时自动从当前仓库 `origin` 解析。

### 3.5 文档站脚手架

```bash
spark docs init    # 生成 docs/{usage,spec,features,quick-start,tips,analysis} 结构
spark docs site    # 生成 docmd.config.js，装 docmd 依赖
npm run dev        # 本地预览
npm run build      # 产出 site/
```

### 3.6 Skill 管理

```bash
spark skill list                    # 列出发现的 skill（含来源与路径）
spark skill list --json             # 机器可读
spark skill sync ./skills           # 汇总复制到一个目录
spark skill sync ./skills --clear   # 先清空再复制
```

发现位置：`.mimocode/skills/`、`.agents/skills/`、`~/.claude/skills/`、
`~/.agents/skills/`、`~/.mimocode/skills/`、`~/.local/share/mimocode/builtin_skills/<version>/skills/`。
同名去重顺序：项目级 > 全局 > builtin，builtin 多版本时取最新。

---

## 4. 如何获取 GitHub 仓库项目列表

这是最常见的三条路径，**按需选**：

### 路径 A：`spark git update-org-status` —— 写进 README 的项目清单

拉取某组织（或用户）下的仓库，按 star 排序，生成 Markdown 表格写进 README 的
`## <section>` 段落（默认 section 名 `Project List`）。

```bash
spark git update-org-status qdriven --dry-run            # 先预览
spark git update-org-status qdriven -o README.md         # 写本地文件
spark git update-org-status qdriven --update-dot-github  # 直接改组织 .github 仓库
spark git update-org-status qdriven --section "Featured Projects"
```

行为要点：

- 仓库列表来自 GitHub API（`/orgs/{org}/repos`），**按 star 倒序**，fork 仓库不计入统计
- 默认输出到 `.github/README.md`；若该路径位于 `.github/` 目录下，会同时更新
  `.github/profile/README.md`（这是组织 profile 仓库的布局）
- `--update-dot-github` 会 clone `<org>/.github` 仓库、改完 commit 并 push
- `--skip-push` 只改文件不提交；`--dry-run` 只打印不写文件
- 段落不存在时插到最后一个 `##` 段落之前；存在则整段替换

> **账号类型**：该命令按「组织」语义取列表。目标若是个人账号（例如用户
> profile 仓库 `<user>/<user>`），先用 `gh` 确认账号类型，必要时改用路径 B
> 或路径 C。

### 路径 B：`gh` CLI —— 需要精确控制时

```bash
gh repo list qdriven --limit 100 --json name,description,stargazersCount,isFork
gh api orgs/qdriven/repos --jq '.[].name'
gh api users/qdriven/repos --jq '.[].name'   # 个人账号用这个端点
```

`gh` 支持 `--json`/`--jq` 过滤与格式化，适合「取列表 → 自己渲染成任意格式」。

### 路径 C：`spark hub scan` —— 从本地目录反推项目注册表

扫本地 Git 仓库，调用 GitHub API 补齐元数据，输出 innate-apps registry 格式
（`registry/apps.json`），供项目聚合站使用。

```bash
spark hub scan . -o registry/apps.json --merge registry/apps.json
spark hub scan . --skip-api           # 离线，只用本地 git 信息
spark hub scan . --deep               # 含嵌套仓库
spark hub scan . --category reference # 指定分类
```

合并时保留手工维护的 `title`/`category`/`status`/`url`/`description`，
刷新自动字段 `repo`/`local_path`/`visibility`/`language`。

### 怎么选

| 你要的结果 | 用 |
|------------|-----|
| README 里的「项目清单」表格 | 路径 A |
| 原始仓库列表，自己渲染 | 路径 B |
| 带分类/状态/可见性的项目注册表 JSON | 路径 C |

---

## 5. 给 AI 助手的执行准则

1. **先 `spark version` 确认环境**，不要假设命令存在。
2. **批量操作前先 `--dry-run` 或小范围试跑**，尤其是 `push-all`、
   `batch-clone`、`update-org-status --update-dot-github` 这类会改远端的命令。
3. **破坏性命令（`--clear`、`push-all`、`update-org-status` 的 push）执行前先向用户确认**。
4. **不要手工编辑** `node_modules/`、`package-lock.json`、`pnpm-lock.yaml`、
   `registry/apps.json` 中由工具生成的字段——它们是运行结果。
5. **注册表类文件的分工**：`apps.json` 是数据源，README / profile 仓库是渲染产物；
   改了数据源要同步刷新渲染产物。
6. **命令失败时看错误信息定位来源**，例如 GitLab token 报错会指明 token 来自
   哪个来源（flag / 配置文件 / 环境变量），按提示排查，不要盲试。
7. **完整命令参考**：仓库 `docs/zh/usage/` 下每个命令组一份说明，
   `AGENTS.md` 是权威的命令树。

---

## 6. 延伸

- 仓库：<https://github.com/variableway/spark-cli>
- 文档站：<https://variableway.github.io/spark-cli/>
- 站内文档：`docs/zh/usage/`（中文）、`docs/en/usage/`（英文）
- 命令树与架构：`AGENTS.md`
- 文档站本身是怎么搭的：`docs/zh/quick-start/docs-site-from-scratch.md`
