# spark task — Task Management

Create, dispatch, sync, and implement development tasks.

## Quick Reference

```bash
spark task init                               # Initialize the task directory structure
spark task list [--task-dir <dir>]            # List every task and issue
spark task create <name> [--content <text>]   # Create an issue file
spark task delete <name> [--force]            # Delete an issue file
spark task impl <name>                        # Implement an issue
spark task dispatch <name> [--dest <path>]    # Dispatch a task
spark task sync <name> [--work-path <path>]   # Sync a task back
spark version [--version|-v]                  # Print spark version / commit / build date
```

Global flags: `--task-dir`, `--owner`, `--work-dir`, `--tui`

---

## spark task init

Initialize the task directory structure (creates `tasks/issues/` and friends).

```bash
spark task init                               # Initialize in the current directory
spark task init --task-dir /path/to/tasks     # Specify the task directory
```

---

## spark task list

List every task and issue file in the task directory.

```bash
spark task list                               # List the current directory's tasks
spark task list --task-dir ./my-tasks         # Specify a directory
```

---

## spark task create

Create a new issue file under `tasks/issues/`. Spaces and underscores in the name are converted to `-`.

| Flag | Default | Description |
|------|---------|-------------|
| `--content` | | Custom content for the issue |

```bash
spark task create my-feature                  # Create tasks/issues/my-feature.md
spark task create "my feature"                # Filename: my-feature.md
spark task create my-feature --content "Description here"
```

---

## spark task delete

Delete an issue file.

| Flag | Default | Description |
|------|---------|-------------|
| `--force` | `false` | Skip the confirmation prompt |

```bash
spark task delete my-feature                  # Delete (with confirmation)
spark task delete my-feature --force          # Force delete
```

---

## spark task impl

Implement an issue via the `kimi` CLI.

```bash
spark task impl my-feature                    # Implement the issue
spark task impl my-feature --tui              # Interactive mode
```

---

## spark task dispatch

Dispatch a task to a new working directory, initialize Git, and create the GitHub repository.

| Flag | Default | Description |
|------|---------|-------------|
| `--dest` | `<work-dir>/<name>` | Destination path |

```bash
spark task dispatch my-feature                # Dispatch to the default path
spark task dispatch my-feature --dest ./ws    # Specify a destination path
spark task dispatch --tui                     # Interactive selection
```

---

## spark task sync

Sync the implementation from the working directory back to the task directory.

| Flag | Default | Description |
|------|---------|-------------|
| `--work-path` | `<work-dir>/<name>` | Working path |

```bash
spark task sync my-feature                    # Sync the default path
spark task sync my-feature --work-path ./ws   # Specify the working path
spark task sync --tui                         # Interactive selection
```

## Workflow

```
create → impl → dispatch → (develop) → sync
  ↑                                        ↓
  └──────── tasks/issues/*.md ←────────────┘
```

## Related

- [Git Management](./git)
