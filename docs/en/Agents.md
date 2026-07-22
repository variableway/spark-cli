# AGENTS.md

This document records the key tasks that AI assistants have executed in this project, the system integration work, and the complete feature reference.

## Project Overview

**Spark** is a CLI tool for managing multiple Git repositories. Its core capabilities:

1. **Multi-repo update** — batch-update multiple Git repositories to the latest version
2. **Submodule management** — add local repos or remote URLs as submodules
3. **Submodule sync** — sync every submodule in a Mono repo
4. **Git user configuration** — configure the Git user for a repository
5. **Task management** — task dispatch, sync, and GitHub repository creation
6. **Gitcode remote management** — add a Gitcode remote to a repository

## Tech Stack

- **Language**: Go 1.24+
- **CLI framework**: [Cobra](https://github.com/spf13/cobra) + [Viper](https://github.com/spf13/viper)
- **Terminal UI**: [pterm](https://github.com/pterm/pterm) + custom TUI components
- **Testing**: [Ginkgo](https://github.com/onsi/ginkgo) + [Gomega](https://github.com/onsi/gomega) (BDD style)
- **Build system**: Makefile (cross-platform)

## Project Structure

```
spark/
├── cmd/                    # CLI command definitions
│   ├── root.go            # Root command and global config
│   ├── task.go            # Task management commands
│   └── git/               # Git-related commands
│       ├── git.go         # Git parent command
│       ├── config.go      # Git user config
│       ├── update.go      # Repo update command
│       ├── submodule.go   # Submodule management
│       ├── sync.go        # Submodule sync
│       └── gitcode.go     # Gitcode remote management
├── internal/              # Internal business logic
│   ├── config/            # Configuration management
│   ├── git/               # Git operation wrappers
│   ├── task/              # Task manager
│   └── tui/               # Terminal UI components
├── docs/                  # Documentation
│   ├── usage/             # User-facing docs
│   └── tasks/             # Task-related docs
├── .vscode/               # VS Code configuration
├── Makefile               # Build scripts
└── main.go                # Entry point
```

## Automation Task Log

### 1. BDD test integration (2026-02-26)
- **Task**: add BDD-style unit tests for the `internal` packages.
- **Tools**: introduced the `Ginkgo` and `Gomega` frameworks.
- **Coverage**: `internal/config` and `internal/git`.
- **Verification**: all tests pass via `make test-bdd`.

### 2. Cross-platform Makefile build (2026-02-26)
- **Task**: create a build system that supports Windows, Linux, and macOS.
- **Features**:
  - Automatic OS detection.
  - Cross-compilation support (`build-linux`, `build-darwin`).
  - Unified clean and test entry points.

### 3. VS Code environment standardization (2026-02-26)
- **Task**: improve the `.vscode` directory configuration.
- **Deliverables**:
  - `tasks.json`: deeply bound to the Makefile.
  - `launch.json`: standardized debug templates.
  - `settings.json`: consistent Go development settings.

## Complete CLI Command List

### Global options

| Option | Description |
|--------|-------------|
| `--config` | Config file (default: `$HOME/.spark.yaml`) |
| `-p, --path` | Directory to scan (repeatable) |

### Git repository management

#### `spark git`
Parent command for the Git management subcommands:

```bash
spark git update       # Update multiple repos
spark git submodule add     # Add existing repos as submodules
spark git sync    # Sync submodules
spark git gitcode      # Add the Gitcode remote
spark git config       # Configure Git user
spark git url          # Get the repo URL
spark git init         # Initialize a repo and create the GitHub remote
spark git batch-clone  # Clone every repo for a user/org
spark git issues       # Create GitHub Issues from Markdown docs/tasks
```

#### `spark git update`
Scans every Git repository under the given directories and updates them to the latest version.

```bash
spark git update -p /path/to/repos
spark git update -p ~/workspace -p ~/projects
spark git update --ssh                       # Force SSH (when HTTPS is unstable)
```

Detailed docs: [docs/usage/git.md](docs/usage/git.md)

#### `spark git submodule`
Add a local Git repository as a submodule, or clone a remote repository as a submodule.

**Local mode**:
```bash
spark git submodule add                    # Add repos under the current directory
spark git submodule add -p /path/to/repos  # Add repos under a specific directory
spark git submodule add ./spark-cli        # Add a specific directory as a submodule
```

| Option | Description |
|--------|-------------|
| `-n, --name` | Submodule path name (default: repo name) |

**Smart detection behavior**:

| Scenario | Output |
|----------|--------|
| Target is already a submodule (160000) | `Skipping <name>: already as submodule` |
| Target shares the parent repo URL (worktree) | `Skipping <name>: already as submodule` |
| Directory exists but is not a submodule | `Skipping <name>: directory already exists (use 'git submodule add' manually)` |
| Normal add | `Adding submodule: <name> (<url>)` |

#### `spark git sync`
Sync every submodule in the current repo to the latest version. Includes `git submodule update --init` so missing submodules are cloned too.

```bash
spark git sync ./my-repo
```

#### `spark git gitcode`
Add Gitcode as a remote for a GitHub repository.

```bash
spark git gitcode -p /path/to/repos
spark git gitcode -p ~/workspace --url https://custom.gitcode.url
```

Detailed docs: [docs/usage/gitcode.md](docs/usage/gitcode.md)

#### `spark git init`
Initialize the current directory as a Git repository and create the GitHub remote.

```bash
spark git init --owner variableway              # Initialize and create the remote
spark git init --owner variableway --private    # Create a private repo
spark git init --skip-gh --owner variableway    # Local init only, skip GitHub
```

| Option | Description |
|--------|-------------|
| `--owner` | GitHub owner (default: from config) |
| `-r, --repo` | Repository name (default: current directory name) |
| `--private` | Create a private repo |
| `--skip-gh` | Skip creating the GitHub remote |

#### `spark git config`
Configure the Git user for the current repository.

```bash
spark git config                              # Show current config
spark git config --username foo --email bar   # Set user info
```

| Option | Description |
|--------|-------------|
| `--username` | Git user name (default: from config) |
| `--email` | Git email (default: from config) |

Precedence:
1. Command-line flags (`--username`, `--email`)
2. Config file (`git.username` and `git.email` in `~/.spark.yaml`)

#### `spark git url`
Print the Git remote URL of the current repository.

```bash
spark git url              # Current directory
spark git url /path/to/repo
```

#### `spark git batch-clone`
Clone every repository of a GitHub organization or user to local.

```bash
spark git batch-clone variableway                    # Use the org name
spark git batch-clone https://github.com/variableway # Use the URL
spark git batch-clone variableway --ssh              # Use SSH
spark git batch-clone variableway -o ./repos         # Specify output directory
```

| Option | Description |
|--------|-------------|
| `--ssh` | Use SSH URLs instead of HTTPS |
| `--include` | Only clone matching repos (comma-separated) |
| `--exclude` | Exclude matching repos (comma-separated) |
| `--include-forks` | Include forked repos |
| `-o, --output` | Output directory (default: current directory) |

#### `spark git issues`
Create GitHub Issues from Markdown. Supports both directory and task-file modes.

```bash
# Directory mode: one Issue per .md file
spark git issues -d ./docs -r owner/repo

# Task mode: split by # Task / ## Task headings
spark git issues -f tasks/issues/task-bug-fix.md -r owner/repo

# Auto-resolve owner/repo from the current repo
spark git issues -f tasks/issues/task-bug-fix.md --dry-run
```

| Option | Description |
|--------|-------------|
| `-r, --repo` | Target repo (`owner/repo`); auto-resolved if omitted |
| `-d, --dir` | Markdown directory (directory mode) |
| `-f, --file` | Task file (task mode) |
| `-l, --labels` | Issue labels (comma-separated) |
| `--dry-run` | Preview only, do not create Issues |

#### `spark git update-org-status`
Fetch every repo for a GitHub org, sort by star count, and update the README.md.

```bash
spark git update-org-status variableway                    # Update local .github/README.md
spark git update-org-status variableway --update-dot-github # Update the .github repo
spark git update-org-status https://github.com/variableway # Use the URL
spark git update-org-status variableway --dry-run          # Preview, no write
spark git update-org-status variableway -o ./docs/README.md # Specify output path
spark git update-org-status variableway --section "Projects" # Specify section name
spark git update-org-status variableway --skip-push        # Skip git push
```

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview the content; do not write |
| `-o, --output` | Local mode output path (default: `.github/README.md`) |
| `--update-dot-github` | Update the org's `.github` repo directly |
| `--section` | Section name to update (default: "Project List") |
| `--skip-push` | Skip `git commit` and `git push` |

**Features**:
- Default target is the local `.github/README.md` file.
- Use `--update-dot-github` to update the org's `.github` repo directly.
- Only updates the named section; everything else is preserved.
- Automatically clones, edits, commits, and pushes the change.

### Script management

#### `spark script`
Manage and run custom scripts.

```bash
spark script list                    # List every available script
spark script run <script-name>       # Run a named script
```

#### `spark script list`
List every available script.

```bash
spark script list
```

Sources:
1. The `spark.scripts` setting in `~/.spark.yaml`.
2. Executable files in the `scripts/` directory.

#### `spark script run`
Run a named script.

```bash
spark script run hello               # Run the hello script
spark script run deploy prod         # Run the deploy script with arg `prod`
spark script run copy-template my-feature  # Copy a template file
```

**Config example** (`~/.spark.yaml`):

```yaml
spark:
  scripts_dir: "scripts"  # Script directory, default scripts/
  scripts:
    - name: hello
      content: |
        #!/bin/bash
        echo "Hello, World!"
    - name: deploy
      content: |
        #!/bin/bash
        echo "Deploying to $1 environment..."
```

**Supported script types**:
- Shell: `.sh`, `.bash`, `.zsh`
- Python: `.py`
- Ruby: `.rb`
- Perl: `.pl`
- PowerShell: `.ps1`
- Batch: `.bat`, `.cmd`

**Cross-platform**: macOS, Linux, Windows

### Task management

#### `spark task`
Task management and issue implementation commands.

```bash
# Initialize the task directory structure
spark task init                    # Create the tasks/ directory structure

# List every task and issue
spark task list                    # List the task directory and issue files

# Create a new issue
spark task create my-feature       # Create tasks/issues/my-feature.md
spark task create my-feature --content "Custom description"

# Delete an issue
spark task delete my-feature       # Delete the issue file
spark task delete my-feature --force  # Force-delete without confirmation

# Implement an issue (via the kimi CLI)
spark task impl my-feature         # Run issue implementation

# Dispatch and sync tasks
spark task dispatch my-task --dest ./workspace
spark task sync my-task --work-path ./workspace
```

| Subcommand | Description |
|------------|-------------|
| `init` | Initialize the task directory structure |
| `list` | List every task and issue |
| `create` | Create a new issue file (spaces in the file name are converted to `-`) |
| `delete` | Delete an issue file |
| `impl` | Implement the issue (via the kimi CLI) |
| `dispatch` | Dispatch a task to a new directory |
| `sync` | Sync the task back to the task directory |

**Issue file creation notes**:
- Spaces and underscores in the file name are automatically converted to `-`.
- The `--content` argument is written into the `## 描述` (Description) section.

**Task directory structure**:
```
tasks/
├── issues/                # Issue files
├── config/                # Configuration tasks
├── analysis/              # Analysis tasks
├── mindstorm/             # Brainstorming
├── planning/              # Planning tasks
└── prd/                   # PRD documents
```

Use the `--tui` flag to enable the interactive terminal UI.

Detailed docs: [docs/usage/task.md](docs/usage/task.md)

## Spark Skills

A personal skill collection that augments spark-cli.

**Repository**: the `spark-skills/` directory inside `variableway/spark-cli`.

### Included Skills

| Skill | Description | Path |
|-------|-------------|------|
| `github-task-workflow` | GitHub task workflow management | `spark-skills/github-task-workflow/` |
| `spark-task-init` | spark task initialization | `spark-skills/spark-task-init-skill/` |

### Usage

```bash
# Install skills into each agent
cd spark-skills
./install.sh kimi
./install.sh claude-code

# One-shot project-level setup
bash spark-skills/setup-project.sh
```

### Skill Directory Structure

```
spark-skills/
├── github-task-workflow/     # GitHub task workflow skill
├── spark-task-init-skill/    # Task initialization skill
├── install.sh                # Installer
└── README.md                 # Documentation
```

Detailed docs: [spark-skills/README.md](spark-skills/README.md)

## Build and Test

### Build commands

```bash
make build          # Build for the current system (Windows produces .exe)
make build-linux    # Cross-compile for Linux
make build-darwin   # Cross-compile for macOS
make clean          # Clean build artifacts
```

### Test commands

```bash
make test           # Run all unit tests
make test-bdd       # Run tests in BDD style
make lint           # Run static checks (go vet)
```

## Config File

The config file lives at `~/.spark.yaml` and supports the following settings:

```yaml
repo-path:
  - /path/to/repos
  - /another/path

task-dir: /path/to/tasks
github-owner: your-username
work-dir: ./workspace

git:
  username: your-name      # Default Git user name
  email: your@email.com    # Default Git email
```

## Assistant Reference

This project aims for a highly cohesive, low-coupling Go style. For future development:

1. **Code style**
   - Follow standard Go conventions
   - Do not add comments unless explicitly requested
   - Reuse existing libraries and patterns

2. **Testing**
   - New features must include BDD-style tests
   - Test files end in `_test.go`
   - Use the Ginkgo/Gomega framework

3. **Build consistency**
   - Prefer updating the `Makefile` to keep build behavior consistent
   - Keep `.vscode` configuration general-purpose
   - Run `make lint` and `make test` before committing

4. **Documentation**
   - Update `docs/usage/` when adding new commands
   - Keep AGENTS.md in sync with the features
