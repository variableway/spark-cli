# spark git — Command Spec

Git repository management command group.

## Parent

```
spark git
```

No arguments, no flags.

---

## spark git update

Update every Git repository to the latest version. Scans every repo under the `repo-path` entries in the config and, for each repo, runs `git fetch --all` followed by `git pull origin <current-branch>`.

```
spark git update [-p <path>] [--ssh]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `-p, --path` | stringSlice | `["."]` | No | Directory containing Git repositories |
| `--ssh` | bool | `false` | No | Force SSH for the update (temporarily rewrites HTTPS GitHub URLs to SSH; does not modify repo config) |

No arguments.

---

## spark git clone

Clone a single GitHub repository with the GitHub CLI (`gh repo clone`); SSH is the default.

```
spark git clone <url-or-slug> [directory] [-- <git-args>]
```

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `url-or-slug` | string | Yes | Repository URL or `owner/repo` shorthand |
| `directory` | string | No | Local clone directory name |

No flags.

**Behavior**:
- Accepted input formats: `https://github.com/owner/repo.git`, `git@github.com:owner/repo.git`, `github.com/owner/repo`, `owner/repo`
- The input is parsed into `owner/repo` and then `gh repo clone owner/repo [directory] [-- <git-args>...]` runs; `gh` uses the SSH URL by default
- Arguments after `--` are forwarded to `git clone` unchanged

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
spark git submodule status [-r] [-j <n>]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `-r, --recursive` | bool | `false` | No | Show nested submodules |
| `-j, --parallel` | int | `1` | No | The command help text reads `Not used for status` (the value is unused for status) |

No arguments.

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

Add a Git repository as a submodule. Exactly **one positional argument** is required; the mode is selected from its shape:

1. Folder mode: the argument is a directory — scan the Git repositories already under it and add them as submodules, no re-clone.
2. URL mode: the argument is a Git URL — clone the remote repository and add it as a submodule.

The current directory must be a Git repository, otherwise the command asks you to run `spark git init` first.

### Folder mode

```
spark git submodule add <path>
```

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `path` | string | Yes | Directory to scan; if that directory is itself a Git repository, only that single repository is added |

No flags. The root command's `-p, --path` has no effect here — the parent repo path is hardcoded to the current directory.

**Smart detection behavior**:

| Scenario | Output |
|----------|--------|
| Target is already a submodule (160000) | `Skipping <name>: already as submodule` |
| Target shares the parent repo URL (worktree) | `Skipping <name>: already as submodule` |
| Directory exists but is not a submodule | `Adding existing repo as submodule: <name> (<url>)` |
| Normal add (URL mode) | `Adding submodule: <name> (<url>)` |

### URL mode

```
spark git submodule add <repo-url> [-n <name>]
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

Auto-detects GitHub or GitLab from the input and clones every repository under an organization, user, or group. GitHub goes through the API with pagination; GitLab prefers the REST API v4 (when a token is present), falls back to `glab`, and finally tries the unauthenticated API.

```
spark git batch-clone <account-name-or-url> [--ssh] [--include <pattern>] [--exclude <pattern>] [--include-forks] [-o <dir>] [--token <token>]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--ssh` | bool | `false` | No | Use SSH URLs for cloning |
| `--include` | string | | No | Only include matching repos (comma-separated) |
| `--exclude` | string | | No | Exclude matching repos (comma-separated) |
| `--include-forks` | bool | `false` | No | Include forked repos |
| `-o, --output` | string | `.` | No | Clone output directory |
| `--token` | string | | No | GitLab private token (also via the `GITLAB_TOKEN` / `GITLAB_PRIVATE_TOKEN` environment variables or `gitlab.token` in `~/.spark.yaml`); when passed explicitly it is not scoped by `gitlab.host` |

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `account-name-or-url` | string | Yes | Organization name, username, or URL (GitLab accepts group/subgroup paths, with or without the `https://` prefix) |

**GitLab implementation notes**:

- Group paths must be URL-encoded when calling API v4 (`group/sub` → `group%2Fsub`), otherwise nested groups 404; `include_subgroups=true` walks them recursively
- Private instances and private groups return **404 rather than 401** when unauthenticated, so errors distinguish "no credentials provided" / "credentials rejected or lack access" / "path not found"
- Clone paths expand the namespace-relative path (`observability/tenant-observability/argocd-tenant-plugin`) so same-named projects in different subgroups never collide
- Token precedence: `--token` > `gitlab.token` (`~/.spark.yaml`) > `GITLAB_TOKEN` > `GITLAB_PRIVATE_TOKEN`
- `gitlab.host` (optional) scopes auto-discovered credentials to that instance, so a self-hosted token is never sent to `gitlab.com`

---

## spark git update-org-status

Update the repository status list in the account's README. The account can be an organization or a user; the type is detected automatically via the GitHub API.

```
spark git update-org-status <account-name-or-url> [--dry-run] [--update-dot-github] [--section <name>] [-o <path>] [--skip-push]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `-o, --output` | string | `.github/README.md` | No | Output file path |
| `--dry-run` | bool | `false` | No | Print only, do not write |
| `--update-dot-github` | bool | `false` | No | Update the account's profile repo directly |
| `--section` | string | `Project List` | No | Section name to update in the README |
| `--skip-push` | bool | `false` | No | Skip `git commit` and `git push` |

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `account-name-or-url` | string | Yes | Account name or URL (organization name or username, e.g. `qdriven`) |

**Behavior**:
- The account type is detected through the GitHub API: organization → profile repo `<org>/.github` (writes `README.md` and `profile/README.md`); user → profile repo `<user>/<user>` (writes `README.md` at the repo root)
- The repository list is fetched with pagination (100 per page), so it is not capped at a single page
- `GITHUB_TOKEN` raises the API rate limit (60 requests/hour when anonymous)
- Forked repositories are not listed in the table and are excluded from the statistics
- `--update-dot-github` clones the account's profile repository into `$TMPDIR/github-repo-<account>-<ts>`, rewrites the README, then commits and pushes

---

## spark git issues

Create GitHub issues from Markdown documents or task files. Two modes are supported:

- Directory mode (`-d`): one issue per `.md` file in the directory
- Task mode (`-f`): one issue per `# Task <id>` / `## Task <id>` section of a single file

```
spark git issues [-r <owner/repo>] (-d <dir> | -f <file>) [-l <labels>] [--dry-run]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `-r, --repo` | string | current repo's `origin` | No | Target repository (`owner/repo`); auto-detected from the current repo's `origin` when omitted |
| `-d, --dir` | string | | No | Directory mode: directory containing the Markdown documents |
| `-f, --file` | string | | No | Task mode: Markdown file containing the task sections |
| `-l, --labels` | stringSlice | `[]` | No | Labels applied to every issue (comma-separated) |
| `--dry-run` | bool | `false` | No | Preview without creating issues |

No arguments. `-d` and `-f` are mutually exclusive — exactly one of them is required.

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

| Argument | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `folder-path` | string | `.` | No | Directory to scan |

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `-d, --db` | string | `~/.innate/feeds.db` | No | SQLite database path |
| `--skip-api` | bool | `false` | No | Skip API calls; local scan only |

The `git.scanner.db` setting in `~/.spark.yaml` overrides the default database path.

**Behavior**:
- Recursively locates `.git` directories and parses the `origin` remote URL
- Supports GitHub, GitLab, Bitbucket
- Upserts into the `repos` SQLite table by `path`
- `GITHUB_TOKEN` is used for GitHub API authentication
