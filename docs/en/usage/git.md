# spark git — Git Repository Management

Manage multiple Git repositories. A directory of repositories uses `spark hub registry`, not submodules.

## Quick Reference

```bash
spark git update                              # Update all repositories
spark git clone <url-or-slug> [dir] [-- <git-args>] # Clone a GitHub repo (SSH by default)
spark git gitcode                             # Add the Gitcode remote
spark git config [--username --email]         # Configure git user
spark git url [repo-path]                     # Show the remote URL
spark git batch-clone <account-or-url> [-o <dir>] # Clone every repo from a GitHub/GitLab account
spark git update-org-status <account> [--dry-run] # Update the account's profile README project list
spark git issues [-r <owner/repo>] (-d <dir> | -f <file>) # Create issues from docs/tasks
spark git push-all                            # Commit and push every repo
spark git scan [folder-path] [--db <path>]    # Scan repos and persist to SQLite
```

---

## spark git clone

Uses the GitHub CLI (`gh repo clone`) to clone a single GitHub repository. SSH is the default, which avoids the failure modes that come with flaky HTTPS.

| Input format | Example |
|---|---|
| HTTPS URL | `https://github.com/owner/repo.git` |
| SSH URL | `git@github.com:owner/repo.git` |
| Short domain | `github.com/owner/repo` |
| owner/repo | `Nutlope/pdf-to-interactive-lesson` |

```bash
# Clone from an HTTPS URL
spark git clone https://github.com/Nutlope/pdf-to-interactive-lesson.git

# Use the owner/repo shorthand
spark git clone Nutlope/pdf-to-interactive-lesson

# Specify a local directory name
spark git clone Nutlope/pdf-to-interactive-lesson my-lesson

# Forward extra arguments to git clone (use -- as the separator)
spark git clone https://github.com/owner/repo.git -- --branch main --depth 1
spark git clone https://github.com/owner/repo.git my-dir -- --branch main --depth 1
```

**Implementation**: the command parses the input into `owner/repo`, then runs `gh repo clone owner/repo [directory] [-- <git-args>...]`. `gh` falls back to the SSH URL by default once you are logged in.

---

## spark git update

Batch-update every Git repository under a directory to the latest commit.

```bash
spark git update                              # Update every repo in the current directory
spark git update -p ~/workspace               # Update a specific directory
spark git update -p ~/ws -p ~/projects        # Multiple directories
spark git update --ssh                        # Force SSH for the update
```

**Flow**: scan the directory → locate `.git` → run `git fetch --all && git pull` per repo → print results.

`--ssh` temporarily rewrites HTTPS GitHub remotes to their SSH form (`git@github.com:...`) via `url.insteadOf` for the duration of the update — useful when HTTPS is unstable. The override applies only while the command runs; the configured remote URL is not modified.

---

## spark git gitcode

Add a Gitcode remote to every GitHub repository.

| Flag | Default | Description |
|------|---------|-------------|
| `--url` | auto-converted | Custom Gitcode URL |

```bash
spark git gitcode                             # Auto-convert GitHub → Gitcode
spark git gitcode --url https://gitcode.com/user/repo
```

---

## spark git config

Configure the git user for a repository.

| Flag | Default | Description |
|------|---------|-------------|
| `--username` | value from config | Git user name |
| `--email` | value from config | Git email |

```bash
spark git config                              # Use the values from the config file
spark git config --username "John" --email "john@example.com"
spark git config /path/to/repo                # Configure a specific repo
```

---

## spark git url

Print the remote URL of a repository.

```bash
spark git url                                 # Current directory
spark git url /path/to/repo                   # Specific repo
```

---

## spark git batch-clone

Auto-detect GitHub or GitLab from the input and clone every repository for the given org/user/group.

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--ssh` | | `false` | Use SSH URLs |
| `--include` | | | Only include matching repos (comma-separated) |
| `--exclude` | | | Exclude matching repos (comma-separated) |
| `--include-forks` | | `false` | Include forked repos |
| `--output` | `-o` | `.` | Output directory |
| `--token` | | | GitLab private token (or `GITLAB_TOKEN` / `GITLAB_PRIVATE_TOKEN` env var, or `gitlab.token` in `~/.spark.yaml`) |

```bash
# GitHub
spark git batch-clone qdriven                    # Clone every repo for an account
spark git batch-clone jackwener                  # Clone every repo for a user
spark git batch-clone https://github.com/qdriven
spark git batch-clone qdriven --ssh             # Use SSH
spark git batch-clone qdriven --include spark --exclude test
spark git batch-clone qdriven -o ./repos        # Specify the output directory

# GitLab (self-hosted or gitlab.com, supports subgroups at any depth)
spark git batch-clone https://gitlab.example.com/myorg/mygroup
spark git batch-clone https://gitlab.com/gitlab-com/gl-infra
spark git batch-clone https://gitlab.example.com/myorg --token <token>
spark git batch-clone gitlab.com/gitlab-com/gl-infra   # https:// may be omitted
```

Nested groups (e.g. `gitlab-com/gl-infra`) are fetched recursively, including all
subgroups. Each project is cloned to `<output>/<namespace-relative-path>`, for example
`archiver` or `observability/tenant-observability/argocd-tenant-plugin`, so the subgroup
layout is preserved and same-named projects in different subgroups never overwrite each other.

### Credentials for private instances

Self-hosted instances and private groups return 404 (not 401) when unauthenticated, so a
token must be configured first. Create a Personal Access Token on that instance (needs the
`read_api` scope, plus `read_repository` to clone private repositories):
`https://<your-gitlab-host>/-/user_settings/personal_access_tokens`

Four sources, highest precedence first:
`--token` > `gitlab.token` in `~/.spark.yaml` > `GITLAB_TOKEN` > `GITLAB_PRIVATE_TOKEN`.

```bash
# 1) Per invocation
spark git batch-clone https://gitlab.example.com/myorg/mygroup --token glpat-xxxx

# 2) Environment variable (add to ~/.zshrc to persist)
export GITLAB_TOKEN=glpat-xxxx
# GITLAB_PRIVATE_TOKEN is also supported

# 3) ~/.spark.yaml (recommended: configure once, works everywhere)
```

```yaml
gitlab:
  host: gitlab.example.com   # optional: scope the credentials to this instance
  token: glpat-xxxx
```

`gitlab.host` scopes the automatically discovered credentials (config file and env vars)
to that instance: once `host` is set, another instance (e.g. the public `gitlab.com`) is
queried anonymously and spark reports `Ignoring ...: it is scoped to ...`. `--token` is an
explicit credential and is never scoped. Without `host` the previous behavior applies and
the credentials are sent to any target instance.

Note: a token in `~/.spark.yaml` takes precedence over environment variables. A revoked
`gitlab.token` left in the config file keeps authentication failing even when a valid
`GITLAB_TOKEN` is exported. The command prints `Using token from: ...` and the error names
the source of the rejected token, so the origin is easy to trace.

You can also reuse `glab` credentials: `glab auth login --hostname gitlab.example.com`,
then verify with `glab auth status`.

Cloning private repositories additionally requires git-side credentials: prefer `--ssh`
(using your SSH key), otherwise let git remember HTTPS credentials
(e.g. `git config --global credential.helper osxkeychain`).

---

## spark git update-org-status

Fetch the repository list of a GitHub account and update the project-list
section in `README.md`.

The argument accepts an **account name** (`qdriven`) or an **account URL**
(`https://github.com/qdriven`) — the account name is parsed out of the URL.

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--output` | `-o` | `.github/README.md` | Output file path |
| `--dry-run` | | `false` | Preview without writing |
| `--update-dot-github` | | `false` | Update the account's profile repo directly |
| `--section` | | `Project List` | Section name to update |
| `--skip-push` | | `false` | Skip `git push` |

```bash
spark git update-org-status qdriven                    # Update the local README
spark git update-org-status qdriven --dry-run          # Preview
spark git update-org-status qdriven --update-dot-github # Push to the profile repo
spark git update-org-status qdriven --section "Featured Projects"
spark git update-org-status https://github.com/qdriven # A URL works too
```

### Account type is detected automatically

The command asks the GitHub API whether the account is an **organization** or a
**user**, then picks the matching profile repository:

| Account type | Profile repository | README location |
|--------------|-------------------|-----------------|
| Organization `Organization` | `<org>/.github` | `README.md` and `profile/README.md` |
| User `User` | `<user>/<user>` | `README.md` at the repository root |

So refreshing the project list of a personal account (such as `qdriven`) into
`qdriven/qdriven` is the same command:

```bash
spark git update-org-status qdriven --update-dot-github
```

> The command clones the profile repository, rewrites the README and runs
> `git push`. Run `--dry-run` first to see exactly what would be written.

### The generated section

```markdown
## Project List

*Last updated: 2026-11-06 21:28:50*

| Name | Description | Stars | Language |
|------|-------------|-------|----------|
| [spark-cli](https://github.com/variableway/spark-cli) | Daily Cli command ideas fired by spark | ⭐ 12 | Go |

**Statistics**: 97 repositories, 37 total stars, 0.4 average
```

Rules:

- Repositories are sorted by **star count, descending**
- **Forked repositories are not listed** in the table and are excluded from the
  statistics
- Empty `description` and `language` render as `-`
- The section title comes from `--section` (default `Project List`)
- If the section does not exist it is inserted before the last `##` section;
  if it exists it is replaced wholesale

### Other behaviour

- The repository list is fetched **page by page** (100 per page), so it is not
  capped at a single page
- Set `GITHUB_TOKEN` to raise the API rate limit (60 requests/hour anonymous)
- The default output is `.github/README.md`; when that path sits in a
  `.github/` directory, `.github/profile/README.md` is updated **as well**
- `--output README.md` writes to the repository root (the usual spot for a
  personal profile repo)
- `--skip-push` only edits the file; `--dry-run` only prints
- In local mode the command runs `git add` → `git commit` → `git push` with the
  message `docs: update <account> project list [skip ci]`

---

## How to get the list of GitHub repository projects

Three paths for the same need — pick by the artifact you want:

### Path A: `spark git update-org-status` — write it straight into the README

The artifact is a Markdown section (table + statistics), described above. Use it
when the project list belongs on a README or a profile repository.

```bash
spark git update-org-status qdriven --section "Featured Projects"
```

### Path B: the `gh` CLI — render it yourself

When you need precise control over format, fields or filtering, fetch the raw
list with `gh`:

```bash
# Repositories of an organization
gh repo list qdriven --limit 200 --json name,description,stargazersCount,isFork,url

# Raw API: organizations use /orgs/, users use /users/
gh api orgs/someorg/repos --jq '.[] | {name, stargazers_count}'
gh api users/qdriven/repos --jq '.[] | {name, stargazers_count}'

# Paginate through everything
gh api --paginate users/qdriven/repos --jq '.[].name'
```

### Path C: `spark hub collections scan` — register apps you develop

For a project registry (JSON) carrying **category / status / visibility /
language**, scan the local repositories with `spark hub collections scan`:

```bash
spark hub collections scan . -o registry/apps.json --merge registry/apps.json
```

See [Project Hub usage](./hub.md).

### Which one to pick

| Artifact you want | Use |
|-------------------|-----|
| A project-list section in a README | Path A |
| The raw repository list, rendered yourself | Path B |
| A registry JSON with categories and status | Path C |

> **Registry vs README**: `registry/apps.json` is the **data source**; the
> project sections in READMEs and profile repositories are its **rendered
> output**. Change the data source and refresh the rendered output.

---

## spark git issues

Create GitHub issues from Markdown documents. Two modes are supported:

- **Directory mode**: `-d` selects a directory; each `.md` file becomes an issue.
- **Task mode**: `-f` selects a file; issues are split by `# Task <id>` or `## Task <id>` headings.

The target repo can be passed via `-r`; if omitted, `owner/repo` is parsed from the current repo's `origin`.

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--repo` | `-r` | auto-detect | Target repo (`owner/repo`) |
| `--dir` | `-d` | | Markdown directory (directory mode) |
| `--file` | `-f` | | Task file (task mode) |
| `--labels` | `-l` | | Apply labels to every issue (comma-separated) |
| `--dry-run` | | `false` | Preview without creating issues |

```bash
# Directory mode: one issue per Markdown file
spark git issues -d ./docs -r variableway/spark-cli

# Task mode: split by Task sections
spark git issues -f ./issues/task-bug-fix.md -r variableway/spark-cli

# Auto-detect owner/repo from the current repo
spark git issues -f ./issues/task-bug-fix.md --dry-run
```

## spark git push-all

Scan a directory for Git repositories, then automatically commit and push every change.

| Flag | Default | Description |
|------|---------|-------------|
| `-p, --path` | `.` | Directory containing Git repositories (repeatable) |

```bash
spark git push-all                            # Push every repository under the path
spark git push-all -p ~/workspace             # Specify the directory
```

**Behavior**:
- Skips non-GitHub repos
- Skips repos with no changes
- Automatically `git add -A` → `git commit` → `git push`
- On conflict, prompts and continues with the next repo

---

## spark git scan

Recursively scan a directory for Git repositories, optionally enrich from the GitHub/GitLab API, and persist results to a SQLite database.

| Flag | Default | Description |
|------|---------|-------------|
| `[folder-path]` | `.` | Directory to scan |
| `-d, --db` | `~/.innate/feeds.db` | SQLite database path |
| `--skip-api` | `false` | Skip API calls; local scan only |

The default database path can also be set in `~/.spark.yaml`:

```yaml
git:
  scanner:
    db: ~/.innate/feeds.db
```

```bash
spark git scan                                # Scan the current directory
spark git scan ~/workspace                    # Scan a specific directory
spark git scan . --skip-api                   # Local-only scan, no API calls
spark git scan . --db ~/data/my-repos.db      # Use a custom database path
```

**Behavior**:
- Recursively locate `.git` directories and parse the `origin` remote URL
- Recognizes GitHub, GitLab, Bitbucket, and other common hosting platforms
- Setting `GITHUB_TOKEN` raises the GitHub API rate limit
- Upserts into SQLite by repo path; repeat scans update existing rows

**Database fields**: `path`, `name`, `remote_url`, `repo_type`, `owner`, `repo`, `description`, `stars`, `forks`, `language`, `updated_at`, `scanned_at`
