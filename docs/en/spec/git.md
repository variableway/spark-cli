# spark git — Command Spec

Git repository management command group.

## Parent

```
spark git
```

No arguments, no flags.

---

## spark git update

Update every Git repository to the latest version. Scans every repo under the `repo-path` entries in the config and runs `git fetch --all && git pull`.

```
spark git update [-p <path>] [--ssh]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `-p, --path` | stringSlice | `["."]` | No | Directory containing Git repositories |
| `--ssh` | bool | `false` | No | Force SSH for the update (temporarily rewrites HTTPS GitHub URLs to SSH; does not modify repo config) |

No arguments.

---

## spark git init

Initialize the current directory as a Git repository and create the GitHub remote.

```
spark git init [--owner <owner>] [--repo <name>] [--private] [--skip-gh]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--owner` | string | `github-owner` from config | Yes* | GitHub owner |
| `-r, --repo` | string | current directory name | No | Repository name |
| `--private` | bool | `false` | No | Create a private repo |
| `--skip-gh` | bool | `false` | No | Skip `gh repo create` |

\* `--owner` can be read from the `github-owner` setting in `~/.spark.yaml`.

**Flow**: `git init` → `git config` → submodule scan (up to 3 levels) → `.gitignore` → `git commit` → `gh repo create --push`

---

## spark git submodule init

Initialize (clone) every registered submodule that has not been checked out yet.

```
spark git submodule init [-j <n>] [-r] [--name <name>]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `-j, --parallel` | int | `1` | No | Number of parallel clone workers (parallel when > 1) |
| `-r, --recursive` | bool | `false` | No | Also initialize nested submodules |
| `--name` | string | | No | Initialize only the named submodule |

No arguments.

**Flow**:
1. When `parallel == 1`: run `git submodule update --init [--recursive]` directly.
2. When `parallel > 1`: parse `git submodule status` to find un-initialized submodules, clone them concurrently with a semaphore, then run `--recursive` (if requested).

---

## spark git submodule status

Show every submodule's init state, commit, and branch.

```
spark git submodule status
```

No flags, no arguments.

**Output**: a table with the columns `PATH`, `INIT` (✅/❌), `COMMIT`, `BRANCH`.

---

## spark git submodule ensure-ssh

Replace every HTTPS GitHub URL in `.gitmodules` with the SSH form. Also updates the parent repo's `origin` remote.

```
spark git submodule ensure-ssh
```

No flags, no arguments.

**Conversion rule**: `https://github.com/<owner>/<repo>.git` → `git@github.com:<owner>/<repo>.git`

---

## spark git submodule add

Add a Git repository as a submodule. Two modes are supported:

1. Local mode: add Git repositories under a directory as submodules, no re-clone.
2. Remote mode: clone a remote Git repository and add it as a submodule.

### Local mode

```
spark git submodule add [-p <path>]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `-p, --path` | string | `.` | No | Directory containing Git repositories |

No arguments.

**Smart detection behavior**:

| Scenario | Output |
|----------|--------|
| Target is already a submodule (160000) | `Skipping <name>: already as submodule` |
| Target shares the parent repo URL (worktree) | `Skipping <name>: already as submodule` |
| Directory exists but is not a submodule | `Skipping <name>: directory already exists (use 'git submodule add' manually)` |
| Normal add | `Adding submodule: <name> (<url>)` |

### Remote mode

```
spark git submodule add <repo-url> [-n <name>] [-p <path>]
```

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `repo-url` | string | Yes | Remote repository URL (HTTPS or SSH) |

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `-n, --name` | string | repo name | No | Submodule path name |

---

## spark git sync

Sync every submodule in the current repository to the latest commit.

```
spark git sync [repo-path] [-r]
```

| Argument | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `repo-path` | string | `.` | No | Repository path |

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `-r, --recursive` | bool | `false` | No | Recursively sync nested submodules |

**Flow**:
1. `git fetch --all` — fetch the latest from every remote
2. `InitAllSubmodules` — initialize missing submodules (read from `.gitmodules`; failures do not abort)
3. `git submodule update --remote --merge` — update and merge every submodule to latest

---

## spark git gitcode

Add a Gitcode remote to a repository. Automatically converts the GitHub URL to a Gitcode URL.

```
spark git gitcode [--url <url>] [-p <path>]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--url` | string | auto-converted | No | Custom Gitcode URL |
| `-p, --path` | stringSlice | `["."]` | No | Directory containing Git repositories |

No arguments.

---

## spark git config

Configure the Git user for the current repository.

```
spark git config [--username <name>] [--email <email>] [repo-path]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--username` | string | value from config | No | Git user name |
| `--email` | string | value from config | No | Git email |

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `repo-path` | string | No | Repository path, default `.` |

---

## spark git url

Get the Git remote URL of a repository.

```
spark git url [repo-path]
```

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `repo-path` | string | No | Repository path, default `.` |

No flags.

---

## spark git batch-clone

Clone every repository under a GitHub organization or user. Auto-detects the account type.

```
spark git batch-clone <account-name-or-url> [--ssh] [--include <pattern>] [--exclude <pattern>] [-o <dir>]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--ssh` | bool | `false` | No | Use SSH URLs for cloning |
| `--include` | string | | No | Only include matching repos (comma-separated) |
| `--exclude` | string | | No | Exclude matching repos (comma-separated) |
| `--include-forks` | bool | `false` | No | Include forked repos |
| `-o, --output` | string | `.` | No | Clone output directory |

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `account-name-or-url` | string | Yes | Organization name, username, or URL |

---

## spark git update-org-status

Update the repository status list in the organization's README.

```
spark git update-org-status <org-name-or-url> [--dry-run] [--update-dot-github] [--section <name>] [-o <path>] [--skip-push]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `-o, --output` | string | `.github/README.md` | No | Output file path |
| `--dry-run` | bool | `false` | No | Print only, do not write |
| `--update-dot-github` | bool | `false` | No | Update the org's `.github` repo directly |
| `--section` | string | `Project List` | No | Section name to update in the README |
| `--skip-push` | bool | `false` | No | Skip `git commit` and `git push` |

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `org-name-or-url` | string | Yes | Organization name or URL |

---

## spark git push-all

Scan a directory for Git repositories, automatically commit and push every change.

```
spark git push-all [-p <path>]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `-p, --path` | stringSlice | `["."]` | No | Directory containing Git repositories |

No arguments.

**Behavior**:
- Skips non-GitHub repos
- Skips repos with no changes
- Automatically `git add -A` → `git commit` → `git push`
- On error, prints a notice and continues with the next repo

---

## spark git scan

Recursively scan a directory for Git repositories, optionally enrich from the GitHub/GitLab API, and persist to a SQLite database.

```
spark git scan [folder-path] [-d <db-path>] [--skip-api]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `folder-path` | string | `.` | No | Directory to scan |
| `-d, --db` | string | `~/.innate/feeds.db` | No | SQLite database path |
| `--skip-api` | bool | `false` | No | Skip API calls; local scan only |

The `git.scanner.db` setting in `~/.spark.yaml` overrides the default database path.

**Behavior**:
- Recursively locates `.git` directories and parses the `origin` remote URL
- Supports GitHub, GitLab, Bitbucket
- Upserts into the `repos` SQLite table by `path`
- `GITHUB_TOKEN` is used for GitHub API authentication
