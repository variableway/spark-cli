# Task Management

## Status: ✅ Implemented

## 前提条件

实现这个功能前请先完成这个项目的：
1. AGENTS.md文件的阅读
2. 整个项目的代码阅读

## 任务总体功能

背景:
想要实现一个golang cli 任务管理功能，主要管理如下场景:
1. 同时可能会有很多很多想法记录，这个想法记录就变成一个todo，或者任务
2. 这些任务都会在一个目录中分列别记录
3. 每一个任务记录都意味这想要做一个小应用或者skill
4. 通过cli命令把已经记录好的一个任务，复制到一个新的目录中
5. 最后在新的目录中，修改相关的代码，实现这个任务，这个不需要代码实现
6. 通过命令行再把这个任务实现的内容复制回原来任务目录中
7. 可以通过配置设定哪个目录是任务总目录，而当前的目录是任务目录

功能实现:
1. 在当前目录中复制指定目录中的文件到一个新的目录，如果这个目录不存在则创建,如果存在就复制到task目录中
2. 这个新的目录需要中需要完成git初始化，同时使用gh 命令创建一个新的github仓库，github仓库的owner可以配置

验证：
1. 通过一个简单的任务分发，确认在新的github仓库生成
2. 测试owner使用qdriven
3. 测试repo名称为: setup

---

## 实现说明

### 已实现功能

| 功能 | 命令 | 状态 |
|------|------|------|
| 列出任务 | `monolize task list` | ✅ |
| 分发任务 | `monolize task dispatch` | ✅ |
| 同步任务 | `monolize task sync` | ✅ |
| TUI 交互模式 | `--tui` 标志 | ✅ |

### 使用方法

#### CLI 模式（默认）

```bash
# 列出所有任务
monolize task list --task-dir ./tasks

# 分发任务到新目录并创建 GitHub 仓库
monolize task dispatch my-task --task-dir ./tasks --owner qdriven

# 同步任务回原目录
monolize task sync my-task --task-dir ./tasks
```

#### TUI 模式（交互式）

```bash
# 交互式列表
monolize task list --task-dir ./tasks --tui

# 交互式分发（使用方向键选择任务）
monolize task dispatch --task-dir ./tasks --owner qdriven --tui

# 交互式同步
monolize task sync --task-dir ./tasks --tui
```

### 配置文件

创建 `~/.spark.yaml`:

```yaml
task_dir: /path/to/tasks
github_owner: qdriven
work_dir: /path/to/workspace
```

### 架构文档

详细架构说明请参阅: [ARCHITECTURE.md](./ARCHITECTURE.md)

### 验证结果

- ✅ GitHub 仓库 https://github.com/qdriven/setup 创建成功
- ✅ 代码成功推送到远程仓库
- ✅ `task list` 命令正常工作
- ✅ `task dispatch` 命令正常工作
- ✅ TUI 模式正常工作
