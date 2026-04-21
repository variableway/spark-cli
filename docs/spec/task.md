# spark task — 命令规格

任务管理命令组。

## 父命令

```
spark task [--task-dir <dir>] [--owner <owner>] [--work-dir <dir>] [--tui]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--task-dir` | string | | 否 | 任务目录路径 |
| `--owner` | string | | 否 | GitHub owner |
| `--work-dir` | string | `.` | 否 | 工作目录 |
| `--tui` | bool | `false` | 否 | 启用交互式 TUI 模式 |

---

## spark task init

初始化任务目录结构，创建 `tasks/issues/` 等目录，并生成 `tasks/example-issue.md`。

```
spark task init
```

无标志，无参数。

---

## spark task list

列出任务目录中的所有任务和特性文件。

```
spark task list [--task-dir <dir>]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--task-dir` | string | | 否 | 任务目录路径 |

无参数。

---

## spark task create

在 `tasks/issues/` 下创建新的 issue 文件。文件名中的空格和下划线自动转为 `-`。

```
spark task create <feature-name> [--content <text>]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--content` | string | | 否 | 自定义内容 |

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `feature-name` | string | 是 | issue 名称（作为文件名） |

---

## spark task delete

删除 issue 文件。

```
spark task delete <feature-name> [--force]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--force` | bool | `false` | 否 | 跳过确认直接删除 |

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `feature-name` | string | 是 | issue 名称 |

---

## spark task impl

使用 `kimi` CLI 实现 issue。

```
spark task impl <feature-name>
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `feature-name` | string | 是 | issue 名称 |

无标志（除父命令 `--tui`）。

---

## spark task dispatch

将任务分发到新的工作目录，初始化 Git 并创建 GitHub 仓库。

```
spark task dispatch [task-name] [--dest <path>]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--dest` | string | `<work-dir>/<name>` | 否 | 目标路径 |

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task-name` | string | 否 | 任务名称 |

---

## spark task sync

将工作目录中的实现同步回任务目录。

```
spark task sync [task-name] [--work-path <path>]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--work-path` | string | `<work-dir>/<name>` | 否 | 工作路径 |

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task-name` | string | 否 | 任务名称 |
