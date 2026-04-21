# 任务管理

## 功能概述

`spark task` 提供任务的全生命周期管理：创建、实现、分发、同步。支持通过 AI Agent（kimi CLI）自动实现 issue，并将任务分发到独立工作目录进行开发。

## 核心能力

### 任务初始化

在项目中创建标准的任务目录结构（`tasks/issues/`）。

```bash
spark task init
```

### Issue 文件管理

创建、列出、删除 issue 描述文件。issue 文件是 Markdown 格式的任务描述。

```bash
spark task create my-feature                     # 创建 issue
spark task create my-feature --content "描述"    # 带内容创建
spark task list                                  # 列出
spark task delete my-feature                     # 删除
```

### AI 实现

通过 `kimi` CLI 自动实现 issue 描述中的任务。

```bash
spark task impl my-feature
spark task impl my-feature --tui    # 交互模式
```

### 任务分发与同步

将任务分发到独立工作目录，开发完成后同步回来。

```bash
# 分发到工作目录（自动初始化 Git、创建 GitHub 仓库）
spark task dispatch my-feature

# 开发完成后同步回任务目录
spark task sync my-feature
```

## 工作流程

```
create → impl → dispatch → (开发) → sync
  ↑                                      ↓
  └────── tasks/issues/*.md ←───────────┘
```

## 使用参数

| 参数 | 说明 |
|------|------|
| `--task-dir` | 任务目录路径 |
| `--owner` | GitHub owner |
| `--work-dir` | 工作目录，默认 `.` |
| `--dest` | dispatch 目标路径 |
| `--work-path` | sync 工作路径 |
| `--tui` | 交互式 TUI 模式 |
| `--force` | 跳过确认（delete） |
| `--content` | 自定义内容（create） |

## 依赖

- `git` 和 `gh` CLI（dispatch 需要 GitHub API）
- `kimi` CLI（impl 需要）

## 相关文档

- [Task 命令规格](../spec/task.md)
- [Task 使用指南](../usage/task.md)
