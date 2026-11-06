# Spark CLI Usage Guide

Spark is a CLI tool for daily dev automation and AI skill integration.

## Command Overview

| Group | Description |
|-------|-------------|
| `spark git` | Git repository management (clone, update, submodules, Gitcode, batch-clone, issues, push, scan) |
| `spark repo` | Repository management (registry-file driven scan / clone / list) |
| `spark script` | Custom script management |
| `spark skill` | AI skill management (discover, list, sync `SKILL.md` directories) |
| `spark hub` | Project hub (scan git repos, emit innate-apps registry info) |
| `spark magic` | System utilities (DNS flush, directory cleaning, dotfile deploy, mirror switching) |
| `spark docs` | Documentation management (init structure, site config) |
| `spark witr` | Process diagnostics (Why Is This Running) |
| `spark version` | Print version / commit / build date |

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
  scanner:
    db: ~/.innate/feeds.db
gitlab:
  host: gitlab.example.com   # optional: scope the token to this instance
  token: glpat-xxxx
github-owner: your-username  # default for spark git init --owner
```

## Detailed Usage

- [Git Repository Management](./git.md)
- [Repository Management](./repo.md)
- [Skill Management](./skill.md)
- [Project Hub](./hub.md)
- [System Utilities](./magic.md)
- [Script Management](./script.md)
- [Docs Management](./docs-cmd.md)
- [Process Diagnostics](./witr.md)

## Getting Started

| Goal | Start here |
|------|------------|
| Try one command first | `spark magic flush-dns` (zero config), `spark version` |
| Teach an AI assistant to use spark | [spark-cli Skill](https://github.com/variableway/spark-cli/blob/main/skills/spark-cli/SKILL.md) |
| Learn to write a Go CLI | [Golang CLI Essentials · Lesson 1](../quick-start/golang-cli-101.md) |
| Learn to write a Node/TS tool | [Node + TypeScript Essentials · Lesson 1](../quick-start/nodejs-typescript-101.md) |
| Build a docs site | [Docs Site from Scratch](../quick-start/docs-site-from-scratch.md) |
| Full command reference | [Command specs](../spec/git.md) and the [AGENTS.md mirror](../Agents.md) |
