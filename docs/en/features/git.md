# Git Repository Management

## Overview

`spark git` provides multi-repository Git management: batch updates, Gitcode remotes, and organization-wide cloning. A directory of repositories is managed with `spark hub registry`.

## Core Capabilities

### Multi-Repo Batch Update

Scans every Git repository under the configured directories and runs `git fetch --all && git pull` in bulk. Perfect for the day-to-day chore of maintaining many repos at once. When HTTPS is unreliable, add `--ssh` to force SSH for the run (the override applies only for the duration of the command; configured remote URLs are not modified).

```bash
spark git update -p ~/workspace
spark git update -p ~/workspace --ssh
```

### Gitcode Remote Integration

Automatically adds a Gitcode (https://gitcode.com) remote to each repo, enabling GitHub ↔ Gitcode two-way sync.

```bash
spark git gitcode -p ~/workspace
```

### Batch Cloning

Auto-detects GitHub or GitLab from the input and clones every repo for an organization, user, or group, or refreshes the repo status list in the README.

```bash
# Clone a GitHub organization's repos
spark git batch-clone variableway -o ./repos

# Clone a GitHub user's repos
spark git batch-clone jackwener -o ./repos

# Clone a GitLab group (nested subgroups supported, https:// optional)
spark git batch-clone gitlab.com/gitlab-com/gl-infra -o ./repos
spark git batch-clone https://gitlab.example.com/myorg/mygroup --token glpat-xxxx

# Only clone repos whose names match the given patterns
spark git batch-clone variableway --include cli,tool --exclude docs

# Refresh org status
spark git update-org-status variableway --update-dot-github
```

**Key improvements**:

- GitLab group paths are URL-encoded as API v4 requires, and nested subgroups are walked recursively (`include_subgroups=true`)
- Clone paths expand the namespace-relative path (e.g. `observability/tenant-observability/argocd-tenant-plugin`), so same-named projects in different subgroups never collide
- Token precedence: `--token` > `gitlab.token` (`~/.spark.yaml`) > `GITLAB_TOKEN` > `GITLAB_PRIVATE_TOKEN`
- `gitlab.host` scopes auto-discovered credentials to that instance, so a self-hosted token is never sent to `gitlab.com`

### Create Issues from Markdown

The unified `spark git issues` command creates GitHub issues from Markdown. Two input modes:

- **Directory mode**: every Markdown file under the directory becomes one issue.
- **Task mode**: a single task file is split by `# Task <id>` / `## Task <id>` headings into multiple issues.

```bash
# Directory mode
spark git issues -d ./docs -r variableway/spark-cli

# Task mode
spark git issues -f ./issues/task-bug-fix.md -r variableway/spark-cli

# Auto-detect current repo + dry run
spark git issues -f ./issues/task-bug-fix.md --dry-run
```

### Batch Push

Scans every GitHub repository, automatically committing and pushing any uncommitted changes.

```bash
spark git push-all -p ~/workspace
```

- Skips non-GitHub repos and repos with no changes
- Continues with the next repo on error

### Git Repository Scanning

Recursively scans directories for Git repositories, enriches from the API (stars, forks, language, etc.), and persists results to a SQLite database.

```bash
spark git scan ~/workspace
spark git scan . --skip-api --db ~/.innate/feeds.db
```

- Default database path: `~/.innate/feeds.db`
- Override via `--db` or the `git.scanner.db` config key
- Set `GITHUB_TOKEN` to raise the GitHub API rate limit

## Parameters

| Parameter | Description |
|-----------|-------------|
| `-p, --path` | Directory containing Git repositories (repeatable), default `["."]` |
| `-o, --output` | Output path |
| `--ssh` | Use SSH for cloning (`batch-clone`) |
| `--include` / `--exclude` | Include/exclude match patterns (`batch-clone`) |
| `--include-forks` | Include forked repos (`batch-clone`) |
| `--token` | GitLab private token (`batch-clone`); also via `GITLAB_TOKEN` / `GITLAB_PRIVATE_TOKEN` or `gitlab.token` |
| `-r, --repo` | Target repo (`owner/repo`); auto-resolved from current repo if omitted |
| `-d, --dir` | Document directory (directory mode) |
| `-f, --file` | Task file (task mode) |
| `-l, --labels` | Issue labels (comma-separated) |
| `--dry-run` | Preview only; do not create issues |
| `-d, --db` | SQLite database path (`scan`), default `~/.innate/feeds.db` |
| `--skip-api` | Skip API calls (`scan`) |

## Dependencies

- The `git` command-line tool
- The `gh` CLI (`issues`, GitHub `batch-clone`, `update-org-status` need GitHub API access)
- GitLab `batch-clone` needs the `glab` CLI, or a `--token` / `gitlab.token` / `GITLAB_TOKEN` (the token needs `read_api`, plus `read_repository` to clone private repos)

## Related

- [Git Command Spec](/en/spec/git)
- [Git Usage Guide](/en/usage/git)
