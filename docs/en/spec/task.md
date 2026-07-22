# spark task — Command Spec

Task management command group.

## Parent

```
spark task [--task-dir <dir>] [--owner <owner>] [--work-dir <dir>] [--tui]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--task-dir` | string | | No | Task directory path |
| `--owner` | string | | No | GitHub owner |
| `--work-dir` | string | `.` | No | Working directory |
| `--tui` | bool | `false` | No | Enable the interactive TUI mode |

---

## spark task init

Initialize the task directory structure (creates `tasks/issues/` and friends).

```
spark task init
```

No flags, no arguments.

---

## spark task list

List every task and issue file in the task directory.

```
spark task list [--task-dir <dir>]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--task-dir` | string | | No | Task directory path |

No arguments.

---

## spark task create

Create a new issue file under `tasks/issues/`. Spaces and underscores in the name are automatically converted to `-`.

```
spark task create <feature-name> [--content <text>]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--content` | string | | No | Custom content |

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `feature-name` | string | Yes | Issue name (used as the file name) |

---

## spark task delete

Delete an issue file.

```
spark task delete <feature-name> [--force]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--force` | bool | `false` | No | Skip the confirmation prompt |

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `feature-name` | string | Yes | Issue name |

---

## spark task impl

Implement an issue via the `kimi` CLI.

```
spark task impl <feature-name>
```

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `feature-name` | string | Yes | Issue name |

No flags (besides the parent's `--tui`).

---

## spark task dispatch

Dispatch a task to a new working directory, initialize Git, and create the GitHub repository.

```
spark task dispatch [task-name] [--dest <path>]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--dest` | string | `<work-dir>/<name>` | No | Destination path |

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `task-name` | string | No | Task name |

---

## spark task sync

Sync the implementation from the working directory back to the task directory.

```
spark task sync [task-name] [--work-path <path>]
```

| Flag | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `--work-path` | string | `<work-dir>/<name>` | No | Working path |

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `task-name` | string | No | Task name |
