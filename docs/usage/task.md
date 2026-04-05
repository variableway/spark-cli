# spark task — 任务管理

管理开发任务的创建、分发、同步和实现。

## 命令速查

```bash
spark task init                               # 初始化任务目录结构
spark task list [--task-dir <dir>]            # 列出所有任务和特性
spark task create <name> [--content <text>]   # 创建特性文件
spark task delete <name> [--force]            # 删除特性文件
spark task impl <name>                        # 实现特性
spark task dispatch <name> [--dest <path>]    # 分发任务
spark task sync <name> [--work-path <path>]   # 同步任务
```

全局标志: `--task-dir`, `--owner`, `--work-dir`, `--tui`

---

## spark task init

初始化任务目录结构，创建 `tasks/features/` 等目录。

```bash
spark task init                               # 在当前目录初始化
spark task init --task-dir /path/to/tasks     # 指定任务目录
```

---

## spark task list

列出任务目录中的所有任务和特性文件。

```bash
spark task list                               # 列出当前目录的任务
spark task list --task-dir ./my-tasks         # 指定目录
```

---

## spark task create

在 `tasks/features/` 下创建新的特性文件。文件名中的空格自动转为 `-`。

| 标志 | 默认值 | 说明 |
|------|--------|------|
| `--content` | | 自定义内容 |

```bash
spark task create my-feature                  # 创建 tasks/features/my-feature.md
spark task create "my feature"                # 文件名: my-feature.md
spark task create my-feature --content "Description here"
```

---

## spark task delete

删除特性文件。

| 标志 | 默认值 | 说明 |
|------|--------|------|
| `--force` | `false` | 跳过确认直接删除 |

```bash
spark task delete my-feature                  # 删除（需确认）
spark task delete my-feature --force          # 强制删除
```

---

## spark task impl

使用 `kimi` CLI 实现特性。

```bash
spark task impl my-feature                    # 实现 my-feature
spark task impl my-feature --tui              # 交互模式
```

---

## spark task dispatch

将任务分发到新的工作目录，初始化 Git 并创建 GitHub 仓库。

| 标志 | 默认值 | 说明 |
|------|--------|------|
| `--dest` | `<work-dir>/<name>` | 目标路径 |

```bash
spark task dispatch my-feature                # 分发到默认路径
spark task dispatch my-feature --dest ./ws    # 指定目标路径
spark task dispatch --tui                     # 交互选择
```

---

## spark task sync

将工作目录中的实现同步回任务目录。

| 标志 | 默认值 | 说明 |
|------|--------|------|
| `--work-path` | `<work-dir>/<name>` | 工作路径 |

```bash
spark task sync my-feature                    # 同步默认路径
spark task sync my-feature --work-path ./ws   # 指定工作路径
spark task sync --tui                         # 交互选择
```

## 工作流程

```
create → impl → dispatch → (开发) → sync
  ↑                                        ↓
  └──────── tasks/features/*.md ←──────────┘
```

## 相关命令

- [Git 管理](./git.md)
- [Agent 配置](./agent.md)
