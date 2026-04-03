# GitHub Task Workflow 自动化方案

本文档介绍如何将 `github-task-workflow` 从"对话触发"升级为"事件自动触发"。

## Skill vs CLI：本质区别

| | CLI | Skill (当前) | Skill + Hook (自动化) |
|---|---|---|---|
| **触发方式** | 人手动敲命令 | 人在对话中要求 AI 执行 | 事件自动触发 |
| **决策主体** | 人 | AI 根据上下文判断 | 脚本根据规则执行 |
| **适用场景** | 明确知道要做什么 | 不确定怎么做，让 AI 帮你整理 | 重复性流程，无需人工干预 |

**结论**：如果你已经明确知道"现在就要创建 Issue"，那直接跑 CLI 和让 AI 跑脚本确实差别不大。Skill 的优势在于**AI 帮你做前置整理**（读文件、总结标题、选标签）。

想要让它真正"自动"，就必须绑定到**事件（Event）**上。

---

## 自动化方案总览

| 方案 | 触发事件 | 难度 | 最佳场景 |
|---|---|---|---|
| **Git Hooks** | `pre-commit`, `post-commit`, `prepare-commit-msg` | 低 | 本地开发时自动关联/更新 Issue |
| **GitHub Actions** | `push`, `pull_request`, `schedule` | 中 | 团队协作，PR 合并后自动关闭 Issue |
| **文件系统 Watcher** | `tasks/` 目录新建/修改 `.md` 文件 | 中 | 个人工作流，写 task 即自动同步到 GitHub |

---

## 方案 1：Git Hooks（本地自动化）

将脚本绑定到 Git 生命周期事件，适合个人开发者快速落地。

### 1.1 prepare-commit-msg：自动插入 Issue 编号

在提交代码时，如果当前分支名是 `feature/42-login`，自动在 commit message 中插入 `#42`。

```bash
# .git/hooks/prepare-commit-msg
#!/bin/sh
COMMIT_MSG_FILE=$1
SOURCE=$2

# 从分支名提取 issue 编号
ISSUE=$(git branch --show-current | grep -oE '^[0-9]+' | head -n 1)

if [ -n "$ISSUE" ] && [ "$SOURCE" != "commit" ]; then
    echo "\nRefs: #$ISSUE" >> "$COMMIT_MSG_FILE"
fi
```

```bash
chmod +x .git/hooks/prepare-commit-msg
```

### 1.2 post-commit：提交后自动评论到 Issue

每次提交后，自动在对应 Issue 下添加一条评论，记录本次提交信息。

```bash
# .git/hooks/post-commit
#!/bin/sh

ISSUE=$(git branch --show-current | grep -oE '^[0-9]+' | head -n 1)
if [ -z "$ISSUE" ]; then
    exit 0
fi

COMMIT_MSG=$(git log -1 --pretty=format:"%s")
REPO_URL=$(git remote get-url origin)

cd $(git rev-parse --show-toplevel)

python .claude/skills/github-task-workflow/scripts/update_issue.py \
  --issue "$ISSUE" \
  --comment "### New Commit\n\n- **Message**: $COMMIT_MSG\n- **Branch**: $(git branch --show-current)" \
  > /dev/null 2>&1
```

> 注意：路径 `python .claude/skills/...` 需要根据你的 skill 实际安装位置调整，或改用全局可访问的脚本路径。

---

## 方案 2：GitHub Actions（云端自动化）

适合团队协作，无需每个成员本地配置。

### 2.1 PR 合并后自动关闭关联 Issue

```yaml
# .github/workflows/close-issue-on-merge.yml
name: Close Linked Issue

on:
  pull_request:
    types: [closed]

jobs:
  close-issue:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - name: Extract issue number from branch
        id: extract
        run: |
          ISSUE=$(echo "${{ github.head_ref }}" | grep -oE '^[0-9]+' | head -n 1)
          echo "issue=$ISSUE" >> $GITHUB_OUTPUT

      - name: Close issue via API
        if: steps.extract.outputs.issue != ''
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ISSUE: ${{ steps.extract.outputs.issue }}
          REPO: ${{ github.repository }}
        run: |
          curl -X PATCH \
            -H "Authorization: Bearer $GH_TOKEN" \
            -H "Accept: application/vnd.github+json" \
            "https://api.github.com/repos/$REPO/issues/$ISSUE" \
            -d '{"state":"closed","body":"Closed by PR #${{ github.event.number }}"}'
```

### 2.2 定时扫描 `tasks/` 目录自动创建 Issue

```yaml
# .github/workflows/sync-tasks.yml
name: Sync Tasks to Issues

on:
  schedule:
    - cron: '0 9 * * 1'  # 每周一早 9 点
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Sync tasks
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          for task in tasks/*.md; do
            title=$(head -n 1 "$task" | sed 's/^# //')
            body=$(cat "$task")
            python scripts/create_issue.py --title "$title" --body "$body" || true
          done
```

---

## 方案 3：文件系统 Watcher（真正的"写 task 即同步"）

如果你想实现：在 `tasks/` 目录新建一个 `.md` 文件，**立刻**自动创建 GitHub Issue。

### 3.1 使用 Python `watchdog` 实现 Daemon

```python
# scripts/task_watcher.py
#!/usr/bin/env python3
"""Watch tasks/ directory and auto-create GitHub issues for new .md files."""

import os
import sys
import time
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Adjust import path if needed
sys.path.insert(0, str(Path(__file__).parent))
from create_issue import create_issue, get_git_remote
from config_loader import get_github_token


TASKS_DIR = Path("tasks")
PROCESSED_LOG = Path(".github-task-workflow.processed")


def load_processed() -> set:
    if not PROCESSED_LOG.exists():
        return set()
    return set(PROCESSED_LOG.read_text().strip().split("\n"))


def save_processed(filename: str):
    with open(PROCESSED_LOG, "a") as f:
        f.write(filename + "\n")


class TaskHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix != ".md":
            return

        processed = load_processed()
        if path.name in processed:
            return

        print(f"[WATCHER] Detected new task: {path.name}")

        title = path.read_text().split("\n")[0].lstrip("# ").strip()
        body = path.read_text()
        repo = get_git_remote()
        token = get_github_token()

        if not repo or not token:
            print("[WATCHER] Skip: repo or token not found")
            return

        try:
            issue = create_issue(repo, title, body, token=token)
            print(f"[WATCHER] Created issue #{issue['number']}: {issue['html_url']}")
            save_processed(path.name)
        except Exception as e:
            print(f"[WATCHER] Error: {e}")


def main():
    TASKS_DIR.mkdir(exist_ok=True)
    observer = Observer()
    observer.schedule(TaskHandler(), str(TASKS_DIR), recursive=False)
    observer.start()
    print(f"[WATCHER] Watching {TASKS_DIR.absolute()} for new tasks...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
```

### 3.2 安装依赖并运行

```bash
pip install watchdog
python scripts/task_watcher.py
```

运行后，只要你在 `tasks/` 下新建 `.md` 文件，就会自动触发 `create_issue.py`。

---

## 如何选择？

| 你的需求 | 推荐方案 |
|---|---|
| 提交代码后自动记录到 Issue | **Git Hooks** (`post-commit`) |
| PR 合并后自动关闭 Issue | **GitHub Actions** |
| 写 task 文件就自动创建 Issue | **文件 Watcher** (`task_watcher.py`) |
| 团队统一规范，无需每个人配置 | **GitHub Actions** |

---

## 方案 4：Kimi CLI Hooks（原生集成）

如果你使用 **Kimi CLI**，可以直接利用其内置的 **Hooks (Beta)** 机制，将自动化逻辑绑定到 AI 的生命周期事件上。

> 这是目前与 AI Agent 结合最紧密的方案：不需要额外的守护进程，也不需要 Git 事件触发，**直接监听 AI 的行为**（如写入文件、会话结束）。

### 4.1 能做什么和不能做什么

| 能做到 | 做不到 |
|---|---|
| AI 写完 `tasks/*.md` 后 **自动** 创建 GitHub Issue | Hook 没有 AI 的理解能力，无法"优化"标题或内容 |
| 会话结束时自动给 Issue 添加评论 | 无法直接在对话中向用户确认"是否创建 Issue" |
| 阻止某些危险操作并给出替代建议 | 无法中断 Kimi 的思考过程 |

### 4.2 配置示例

在 `~/.kimi/config.toml` 中添加：

```toml
# AI 写入 task 文件后，自动创建 GitHub Issue
[[hooks]]
event = "PostToolUse"
matcher = "WriteFile|StrReplaceFile"
command = "bash /path/to/spark-skills/github-task-workflow/hooks/kimi-auto-issue.sh"
timeout = 30

# 会话结束时，自动更新活跃 Issue
[[hooks]]
event = "Stop"
command = "bash /path/to/spark-skills/github-task-workflow/hooks/kimi-stop-update.sh"
timeout = 30
```

### 4.3 Hook 脚本：`kimi-auto-issue.sh`

```bash
#!/bin/bash
# Kimi CLI Hook: Auto-create GitHub issue when a task file is written.

read JSON

# Extract file path from the JSON context
FILE=$(echo "$JSON" | python3 -c "
import sys, json
data = json.load(sys.stdin)
inp = data.get('tool_input', {})
path = inp.get('file_path') or inp.get('path') or ''
print(path)
")

# Only trigger for .md files in tasks/ directory
if [[ ! "$FILE" =~ /tasks/ ]] || [[ ! "$FILE" =~ \.md$ ]]; then
    exit 0
fi

# Must be in a git repo
REPO_DIR=$(git -C "$(dirname "$FILE")" rev-parse --show-toplevel 2>/dev/null)
if [ -z "$REPO_DIR" ]; then
    exit 0
fi

# Path to the skill scripts (adjust to your actual installation)
SKILL_DIR="$REPO_DIR/.kimi/skills/github-task-workflow"
if [ ! -d "$SKILL_DIR" ]; then
    SKILL_DIR="$HOME/.kimi/skills/github-task-workflow"
fi
if [ ! -d "$SKILL_DIR" ]; then
    SKILL_DIR="$HOME/.claude/skills/github-task-workflow"
fi

TITLE=$(head -n 1 "$FILE" | sed 's/^# //')
BODY=$(cat "$FILE")

cd "$REPO_DIR" || exit 0

# Create issue silently
python3 "$SKILL_DIR/scripts/create_issue.py" \
  --title "$TITLE" \
  --body "$BODY" \
  --labels "task" \
  > /dev/null 2>&1

exit 0
```

**这个脚本在做什么？**

- 监听 Kimi 每次调用 `WriteFile` 或 `StrReplaceFile`
- 如果写入的文件路径包含 `/tasks/` 且以 `.md` 结尾
- 自动提取文件第一行作为标题，全文作为 body
- 调用 `create_issue.py` 静默创建 GitHub Issue

### 4.4 Hook 脚本：`kimi-stop-update.sh`

```bash
#!/bin/bash
# Kimi CLI Hook: Auto-update the active issue when the session ends.

read JSON

# Check if stop hook is already active (prevents infinite loops)
IS_ACTIVE=$(echo "$JSON" | python3 -c "
import sys, json
print(json.load(sys.stdin).get('stop_hook_active', False))
")

if [ "$IS_ACTIVE" = "True" ]; then
    exit 0
fi

REPO_DIR=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$REPO_DIR" ]; then
    exit 0
fi

SKILL_DIR="$REPO_DIR/.kimi/skills/github-task-workflow"
if [ ! -d "$SKILL_DIR" ]; then
    SKILL_DIR="$HOME/.kimi/skills/github-task-workflow"
fi
if [ ! -d "$SKILL_DIR" ]; then
    SKILL_DIR="$HOME/.claude/skills/github-task-workflow"
fi

# Find the most recently created issue number from a local marker file
ISSUE_FILE="$REPO_DIR/.github-task-workflow.active-issue"
if [ ! -f "$ISSUE_FILE" ]; then
    exit 0
fi

ISSUE=$(cat "$ISSUE_FILE")
rm -f "$ISSUE_FILE"

cd "$REPO_DIR" || exit 0

python3 "$SKILL_DIR/scripts/update_issue.py" \
  --issue "$ISSUE" \
  --comment "### Session Completed\n\nAssociated Kimi CLI session has ended. Implementation may be complete." \
  > /dev/null 2>&1

exit 0
```

**配套修改：`create_issue.py` 创建 Issue 后写入标记文件**

为了让 `Stop` hook 知道哪个 Issue 是当前活跃的，可以在 `create_issue.py` 创建成功后追加一行：

```bash
# In create_issue.py main(), after successful creation:
# Path(".github-task-workflow.active-issue").write_text(str(issue['number']))
```

（你可以手动修改 `scripts/create_issue.py`，或者在调用脚本后单独处理。）

### 4.5 如何查看 Hooks 是否生效

在 Kimi CLI 的 Shell 模式下输入：

```
/hooks
```

你应该能看到：

```
Configured Hooks:
  PostToolUse: 1 hook(s)
  Stop: 1 hook(s)
```

### 4.6 限制说明

Kimi CLI 的 Hooks 是 **Beta 功能**，有以下已知限制：

1. **上下文有限**：Hook 通过 stdin 接收 JSON，只能看到工具输入/输出，看不到 AI 的推理过程
2. **Fail-open**：Hook 超时或崩溃不会阻塞 Agent
3. **无交互能力**：Hook 无法向用户发起二次确认
4. **并行执行**：同一事件的多个 hook 是并行的

所以 **Kimi Hooks 适合"规则明确的自动化"**，而不适合需要复杂判断或用户确认的决策。

---

## 方案对比与选择建议

| 你的主要工具 | 推荐方案 | 效果 |
|---|---|---|
| **Kimi CLI** | **Kimi Hooks** | 最原生，监听 AI 写文件和会话结束事件 |
| **通用/多 Agent** | **Git Hooks** | 不依赖特定 Agent，提交代码时触发 |
| **团队协作** | **GitHub Actions** | 云端统一执行，无需本地配置 |
| **个人本地自动化** | **文件 Watcher** | 不启动 Kimi 也能监控 task 目录 |

---

## 最佳组合：Kimi Hooks + Git Hooks + GitHub Actions

最完整的工作流是三者组合：

1. **Kimi Hook (`PostToolUse`)**：Kimi 写完 `tasks/*.md` → 自动创建 GitHub Issue
2. **Git Hook (`post-commit`)**：开发过程中提交代码 → 自动评论到 Issue
3. **GitHub Actions**：PR 合并 → 自动关闭 Issue 并添加完成总结

这样 Skill 就从"AI 帮你手动操作"进化成了**全自动化流水线**。

## 方案 5：跨 Agent 编排器 `orchestrate.py`（推荐）

对于**不支持 Flow Skill**的 Agent（如 Claude Code、Codex、OpenCode），或当你希望有一个"状态机"来确保工作流不被遗忘时，可以使用 `scripts/orchestrate.py`。

### 5.1 核心设计

`orchestrate.py` 把工作流拆成了两个明确的"人工+AI 协作"阶段：

```bash
# Stage 1: 创建 Issue 并保存状态
python scripts/orchestrate.py init tasks/login.md "使用 JWT 实现"

# -> 输出 Issue 编号，并写入 .github-task-workflow.state.json

# Stage 2: AI 实现完成后，一键收尾
python scripts/orchestrate.py finish

# -> 自动：添加完成评论 + 关闭 Issue + git commit/push + 清理状态
```

中间阶段（AI 实现代码修改）仍然由 Agent 完成，因为代码修改需要 LLM 的推理能力，脚本无法替代。

### 5.2 为什么需要编排器？

在 Claude Code 等不支持 Flow 的 Agent 中，你直接说"执行 task"，AI 可能：
- 只创建 Issue 就停了
- 改了代码但忘了更新 Issue
- 更新了 Issue 但忘了提交代码

`orchestrate.py` 通过**持久化状态文件**解决了这个问题：
- `init` 成功后，状态文件记录了 Issue 编号
- Agent 看到 `init` 的输出提示，知道必须继续实现
- `finish` 读取状态文件，确保 Issue 被正确关闭，代码被提交

### 5.3 在任何 Agent 中的使用方式

**Claude Code / Codex / OpenCode 示例**：

```
User: 请执行 tasks/auth-refactor.md，使用 JWT 替代 Session，走完整工作流。
Agent: 好的，我先创建 Issue。
       [Shell] python scripts/orchestrate.py init tasks/auth-refactor.md "使用 JWT 替代 Session"
       -> Created Issue #42
Agent: 现在开始实现代码修改...
       [WriteFile/StrReplaceFile/Shell 执行修改和测试]
Agent: 实现完成，现在收尾。
       [Shell] python scripts/orchestrate.py finish
       -> Issue #42 closed, code pushed.
```

**辅助命令**：

```bash
python scripts/orchestrate.py status   # 查看当前活跃工作流
python scripts/orchestrate.py abort    # 放弃当前工作流（不更新 Issue）
```

## 方案 6：自定义 Kimi Agent（100% 强制工作流）

如果你想让 Kimi CLI **在普通对话中也能 100% 强制**执行 5 步流程（而不仅依赖 Flow Skill），可以使用自定义 Agent。

已提供的配置文件：

```bash
kimi --agent-file github-task-workflow/agent/kimi-agent.yaml
```

该 Agent 继承了默认 Agent，但覆盖了 system prompt，明确写入：

> "当用户要求执行 task 文件时，你必须按 1-2-3-4-5 步执行，不得跳过任何步骤。"

启动后，你跟 Kimi 说：

```
执行 tasks/login-refactor.md，使用 JWT 实现。
```

它就会：
1. 读取文件
2. 运行 `orchestrate.py init`
3. 执行代码修改
4. 运行 `orchestrate.py finish`
5. 报告完成

## 方案对比总结

| 方案 | 触发方式 | 适用 Agent | 自动化程度 | 推荐度 |
|---|---|---|---|---|
| **Flow Skill** | `/flow:github-task-workflow ...` | Kimi CLI | ⭐⭐⭐⭐⭐ | **最推荐** |
| **自定义 Agent** | 普通对话 | Kimi CLI | ⭐⭐⭐⭐☆ | 强制约束 |
| **orchestrate.py** | `init` + `finish` | 所有 Agent | ⭐⭐⭐⭐☆ | **跨 Agent 最佳** |
| **Kimi Hooks** | 事件自动触发 | Kimi CLI | ⭐⭐⭐☆☆ | 补充增强 |
| **Git Hooks** | Git 事件 | 通用 | ⭐⭐⭐☆☆ | 代码提交自动化 |
| **GitHub Actions** | 云端事件 | 团队协作 | ⭐⭐⭐⭐☆ | 团队协作必选 |

## 最佳实践推荐

### 如果你是 Kimi CLI 用户

**主方案**：Flow Skill（`/flow:`）
**备用**：自定义 Agent（不想记 `/flow:` 命令时）
**增强**：Kimi Hooks + Git Hooks

### 如果你是 Claude Code / Codex / OpenCode 用户

**主方案**：`orchestrate.py`（`init` -> AI 实现 -> `finish`）
**增强**：Git Hooks（提交自动评论）+ GitHub Actions（PR 合并自动关闭）

### 最完整的全自动化组合

1. **Kimi CLI**: `/flow:github-task-workflow tasks/xxx.md` 一键触发
2. **Claude Code**: `python scripts/orchestrate.py init tasks/xxx.md` → AI 实现 → `finish`
3. **Kimi Hooks**: 写 task 文件自动创建 Issue；会话结束自动评论
4. **Git Hooks**: `post-commit` 自动记录提交到 Issue
5. **GitHub Actions**: PR 合并自动关闭 Issue

## 结论

- **Kimi CLI 现在可以 100% 自动**：通过 `/flow:` 或自定义 Agent
- **Claude Code / Codex / OpenCode 可以半自动**：通过 `orchestrate.py` 把创建和收尾自动化，中间的 AI 实现仍然由 Agent 完成
- **所有 Agent 都可以增强**：通过 Hooks / Actions / Watcher 补齐特定环节的自动化
