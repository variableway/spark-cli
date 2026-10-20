# Git Worktree 开发指南

`git worktree` 允许同一份仓库检出到多个目录，每个目录绑定独立分支。适合需要同时维护多个功能分支、又不想反复 `git stash` 或来回切换的场景。

## 什么时候用

- 一个功能开发到一半，需要紧急切到另一个分支修 bug
- 长时间运行的构建/测试占用某个目录，同时又想在新分支上继续开发
- 为某个任务（如 Windows 专项修复）创建隔离工作区，完成后整体清理

## 常用命令

```bash
# 查看现有 worktree
git worktree list

# 为 new-feature 分支创建新工作目录
git worktree add ../spark-cli-new-feature -b new-feature

# 基于远程已有分支创建
git worktree add ../spark-cli-hotfix hotfix/xxx

# 完成后删除（目录必须干净，无未提交改动）
git worktree remove ../spark-cli-new-feature

# 目录已被手动删除时，清理元数据
git worktree prune

# 锁定/解锁（防止被 remove 或 prune 误删）
git worktree lock ../spark-cli-long-task
git worktree unlock ../spark-cli-long-task
```

## 典型工作流

```bash
# 1. 从 main 拉一个任务分支的 worktree
git worktree add ../spark-cli-windows-build -b qdriven/windows-build main

# 2. 在新目录中开发、提交、推送
cd ../spark-cli-windows-build
# ... 开发 ...
git push -u origin qdriven/windows-build

# 3. 通过 PR 合并到 main（推荐，避免本地直接 merge）

# 4. 合并后清理：先删 worktree，再删已合并的分支
git worktree remove ../spark-cli-windows-build
git branch -d qdriven/windows-build
```

## 注意事项

- **同一分支不能同时在两个 worktree 检出**——第二个会报 `fatal: 'main' is already used by worktree`。所以合并到 `main` 时用 PR，而不是在 worktree 里 checkout main。
- `git worktree remove` 要求目录内没有未提交改动，否则会拒绝；确认不要的内容用 `git worktree remove --force`（谨慎）。
- worktree 与主仓库**共享 object 数据库和本地配置**（`.git` 里的内容），但不共享未提交的 working tree 状态。
- 手动 `rm -rf` 删除目录后，记得 `git worktree prune`，否则 `git worktree list` 里会残留。
- 每个 worktree 记得单独安装依赖（如 `go mod download`、`npm install`）。
