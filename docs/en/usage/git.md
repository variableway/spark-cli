# spark git — Git Repository Management

Manage multiple Git repositories, initialize projects, sync submodules.

## Quick Reference

```bash
spark git update                              # Update all repositories
spark git clone <url-or-slug> [dir] [-- <git-args>] # Clone a GitHub repo (SSH by default)
spark git submodule add [-p <path>]                # Add existing repos as submodules
spark git submodule add <repo-url> [-n <name>]     # Add a remote repo as a submodule
spark git submodule init [-j <n>] [-r]             # Initialize (clone) all submodules
spark git submodule status                         # Show submodule status
spark git submodule ensure-ssh                     # Convert HTTPS URLs to SSH
spark git sync [./repo]                   # Sync submodules
spark git gitcode                             # Add the Gitcode remote
spark git init [--owner <owner>] [--skip-gh]   # Initialize a repo and create its GitHub remote
spark git config [--username --email]         # Configure git user
spark git url [repo-path]                     # Show the remote URL
spark git batch-clone <account-or-url> [-o <dir>] # Clone every repo from a GitHub/GitLab account
spark git update-org-status <org> [--dry-run] # Update the org README
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

## spark git submodule add

Add a local Git repository as a submodule, or clone a remote repository as a submodule.

### Mode 1: Add a local repository as a submodule

Scan a directory for Git repositories and add them as submodules without re-cloning.

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `-p, --path` | | `.` | Directory containing Git repositories |

```bash
spark git submodule add ./repos                       # Add every GitHub repo under the local folder as a submodule
spark git submodule add ./spark-cli                  # Add a specific directory as a submodule
```

**Smart detection behavior**:

| Scenario | Output |
|----------|--------|
| Target is already a submodule (160000) | `Skipping <name>: already as submodule` |
| Target shares the parent repo URL (worktree) | `Skipping <name>: already as submodule` |
| Directory exists but is not a submodule | `Adding existing repo as submodule: <name> (<url>)` (writes `.gitmodules` and stages the gitlink, no re-clone) |
| Normal add | `Adding submodule: <name> (<url>)` |

### Mode 2: Add a remote repository as a submodule

Clone a remote Git repository and add it as a submodule.

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `-n, --name` | string | repo name | Submodule path name (remote mode) |

```bash
# Add a remote repo (default path)
spark git submodule add https://github.com/user/repo

# Add a remote repo and specify a path name
spark git submodule add https://github.com/user/repo --name my-submodule

# SSH URL
spark git submodule add git@github.com:user/repo.git

# owner/repo shorthand (GitHub)
spark git submodule add user/repo
```

---

## spark git submodule init

Initialize (clone) every registered submodule that has not been checked out yet.

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `-j, --parallel` | | `1` | Number of parallel clone workers |
| `-r, --recursive` | | `false` | Also initialize nested submodules |
| `--name` | | | Initialize only the named submodule |

```bash
spark git submodule init                         # Initialize every submodule
spark git submodule init -j 4                    # 4-way parallel init
spark git submodule init --recursive             # Include nested submodules
spark git submodule init --name spark-cli        # Only the named submodule
```

**Note**: `init` only clones — it does not merge or switch branches. To bring submodules up to date, use `spark git sync`.

---

## spark git submodule status

Prints the status of every submodule in a table.

```bash
spark git submodule status
```

**Example output**:
```
PATH                           INIT       COMMIT       BRANCH
---------------------------------------------------------------------------
fire-skills-base               ✅         945082af     heads/main
innate-websites                ❌         119324a8         
spark-cli                      ✅         43568d24     heads/main
```

---

## spark git submodule ensure-ssh

Replace every HTTPS GitHub URL in `.gitmodules` with the SSH form. Useful when HTTPS is unreliable.

```bash
spark git submodule ensure-ssh
```

**Effect**:
- `https://github.com/owner/repo.git` → `git@github.com:owner/repo.git`
- The parent repo's `origin` remote URL is also updated
- `.gitmodules` is modified — you still need to commit the change

---

## spark git sync

Sync every submodule in a Mono repo to the latest commit.

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `-r, --recursive` | | `false` | Recursively sync nested submodules |

```bash
spark git sync ./my-repo                       # Sync a specific repo
spark git sync --recursive                     # Include nested submodules
```

**Flow**:
1. `git fetch --all` — fetch the latest from every remote
2. `git submodule update --init` — initialize missing submodules (read from `.gitmodules`)
3. `git submodule update --remote --merge` — update and merge every submodule to latest

**Note**: step 2 uses a parallel init (serial mode); failures do not stop the rest of the run.

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

## spark git init

Initialize the current directory as a Git repository and create the GitHub remote.

**Flow**:
1. `git init` — initialize the local repo
2. `git config user.name/email` — read from `~/.spark.yaml` and apply
3. Scan subdirectories for GitHub repositories, add them automatically as `git submodule`
4. Generate `.gitignore` with common ignore rules
5. `git commit` — create the initial commit (required for `gh repo create --push`)
6. `gh repo create` — create the GitHub remote and push

```bash
spark git init --owner variableway              # Initialize and create the remote
spark git init --owner variableway --private    # Create a private repo
spark git init --skip-gh --owner variableway    # Local init only
```

| Flag | Default | Description |
|------|---------|-------------|
| `--owner` | `github-owner` from config | GitHub owner |
| `-r, --repo` | current directory name | Repository name |
| `--private` | `false` | Create a private repo |
| `--skip-gh` | `false` | Skip `gh repo create` |

**Config file** (`~/.spark.yaml`):

```yaml
github-owner: your-username

git:
  username: Your Name
  email: your@email.com
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
| `--token` | | | GitLab private token (or `GITLAB_TOKEN` / `GITLAB_PRIVATE_TOKEN` env var) |

```bash
# GitHub
spark git batch-clone variableway               # Clone every repo for an org
spark git batch-clone jackwener                 # Clone every repo for a user
spark git batch-clone https://github.com/variableway
spark git batch-clone variableway --ssh         # Use SSH
spark git batch-clone variableway --include spark --exclude test
spark git batch-clone variableway -o ./repos  # Specify the output directory

# GitLab (self-hosted or gitlab.com, supports subgroups)
spark git batch-clone https://gitlab.example.com/myorg/mygroup
spark git batch-clone https://gitlab.com/mygroup/myproject
spark git batch-clone https://gitlab.example.com/myorg --token <token>
```

---

## spark git update-org-status

Fetch the org's repository list and update `README.md`.

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--output` | `-o` | `.github/README.md` | Output file path |
| `--dry-run` | | `false` | Preview without writing |
| `--update-dot-github` | | `false` | Update the org's `.github` repo directly |
| `--section` | | `Project List` | Section name to update |
| `--skip-push` | | `false` | Skip `git push` |

```bash
spark git update-org-status variableway                    # Update the local README
spark git update-org-status variableway --dry-run          # Preview
spark git update-org-status variableway --update-dot-github # Push directly
spark git update-org-status variableway --section "My Projects"
```

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
spark git issues -f tasks/issues/task-bug-fix.md -r variableway/spark-cli

# Auto-detect owner/repo from the current repo
spark git issues -f tasks/issues/task-bug-fix.md --dry-run
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

---

## Related

- [Task Management](./task)
