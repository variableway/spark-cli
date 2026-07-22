# Spark CLI Usage Guide

Spark is a CLI tool for daily dev automation and AI skill integration.

## Command Overview

| Group | Description |
|-------|-------------|
| `spark git` | Git repository management (clone, update, submodules, Gitcode, batch-clone, push, scan) |
| `spark task` | Task management (create, dispatch, sync, implement) |
| `spark script` | Custom script management |
| `spark magic` | System utilities (DNS flush, directory cleaning, dotfile deploy, mirror switching) |
| `spark docs` | Documentation management (init structure, site config) |
| `spark witr` | Process diagnostics (Why Is This Running) |

## Global Flags

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--config` | | `~/.spark.yaml` | Config file path |
| `--path` | `-p` | `.` | Directory to scan (repeatable) |

## Configuration

The config file lives at `~/.spark.yaml`:

```yaml
repo-path:
  - ~/workspace
  - ~/projects
git:
  username: your-name
  email: your@email.com
task_dir: ./tasks
github_owner: your-username
work_dir: ./workspace
```

## Detailed Usage

- [Git Repository Management](./git)
- [Task Management](./task)
- [System Utilities](./magic)
- [Script Management](./script)
- [Docs Management](./docs-cmd)
- [Process Diagnostics](./witr)
