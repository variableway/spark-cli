# Git Worktree Development Guide

`git worktree` lets you check out the same repository into multiple directories, each bound to its own branch. It fits scenarios where you maintain several feature branches in parallel without constant `git stash` or context switching.

## When to Use

- A feature is half-done and you need to switch branches for an urgent fix
- A long-running build/test occupies one directory while you keep developing on a new branch
- Create an isolated workspace for a task (e.g. a Windows-specific fix) and clean it up afterwards

## Common Commands

```bash
# List existing worktrees
git worktree list

# Create a new worktree with a new branch
git worktree add ../spark-cli-new-feature -b new-feature

# Create a worktree from an existing remote branch
git worktree add ../spark-cli-hotfix hotfix/xxx

# Remove when done (directory must be clean, no uncommitted changes)
git worktree remove ../spark-cli-new-feature

# Clean up metadata after a manual directory deletion
git worktree prune

# Lock/unlock (prevent accidental removal by remove/prune)
git worktree lock ../spark-cli-long-task
git worktree unlock ../spark-cli-long-task
```

## Typical Workflow

```bash
# 1. Create a worktree with a task branch from main
git worktree add ../spark-cli-windows-build -b qdriven/windows-build main

# 2. Develop, commit and push in the new directory
cd ../spark-cli-windows-build
# ... develop ...
git push -u origin qdriven/windows-build

# 3. Merge to main via a pull request (recommended, instead of merging locally)

# 4. After merging, clean up: remove the worktree, then delete the merged branch
git worktree remove ../spark-cli-windows-build
git branch -d qdriven/windows-build
```

## Caveats

- **The same branch cannot be checked out in two worktrees** — the second attempt fails with `fatal: 'main' is already used by worktree`. Merge via PR instead of checking out `main` inside a worktree.
- `git worktree remove` refuses when the directory has uncommitted changes; use `git worktree remove --force` only when you are sure the content is disposable.
- Worktrees **share the object database and local config** with the main repo, but not uncommitted working-tree state.
- After manually `rm -rf`-ing a worktree directory, run `git worktree prune` so `git worktree list` does not keep stale entries.
- Install dependencies separately in each worktree (e.g. `go mod download`, `npm install`).
