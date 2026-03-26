# Task Management TUI Architecture

## Overview

This document describes the architecture of the Task Management CLI with TUI (Terminal User Interface) support.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           cmd/task.go                               │
│  --tui flag  →  Mode Detection  →  CLI or TUI Implementation        │
│                                                                     │
│  Commands:                                                          │
│    • task list      - List all tasks                               │
│    • task dispatch  - Dispatch task to new directory + GitHub      │
│    • task sync      - Sync task back to task directory             │
└─────────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  internal/tui   │  │  internal/task  │  │  internal/git   │
│                 │  │                 │  │                 │
│  • ui.go        │  │  • task.go      │  │  • finder.go    │
│  • selector.go  │  │    - Manager    │  │  • updater.go   │
│  • confirm.go   │  │    - Dispatch   │  │                 │
│                 │  │    - SyncBack   │  │                 │
│  Dependencies:  │  │    - ListTasks  │  │                 │
│  • pterm        │  │                 │  │                 │
│  • bubbletea    │  │                 │  │                 │
│  • lipgloss     │  │                 │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## Module Descriptions

### 1. internal/tui Package

Provides TUI components for interactive CLI experience.

| File | Description |
|------|-------------|
| `ui.go` | Core UI class with logging, spinners, tables, and styled output |
| `selector.go` | Interactive task selector using bubbletea (arrow key navigation) |
| `confirm.go` | Confirmation dialog with Yes/No selection |

#### UI Methods

```go
type UI struct {
    useTUI bool
}

// Output methods
func (u *UI) Info(msg string)
func (u *UI) Success(msg string)
func (u *UI) Error(msg string)
func (u *UI) Warning(msg string)
func (u *UI) Printf(format string, args ...interface{})

// Progress methods
func (u *UI) Spinner(message string, action func() error) error

// Display methods
func (u *UI) Header(title string)
func (u *UI) Table(headers []string, rows [][]string)
func (u *UI) BulletList(items []string)
```

### 2. internal/task Package

Business logic for task management operations.

```go
type Manager struct {
    TaskDir     string      // Directory containing all tasks
    GitHubOwner string      // GitHub owner for repository creation
    WorkDir     string      // Working directory for dispatched tasks
    UI          *tui.UI     // UI instance for output
}

// Operations
func (m *Manager) Dispatch(taskName, destPath string) error
func (m *Manager) SyncBack(taskName, workPath string) error
func (m *Manager) ListTasks() ([]string, error)
```

### 3. cmd/task.go

CLI command definitions with dual-mode support.

## Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| github.com/pterm/pterm | v0.12.83 | Styled terminal output, spinners, tables |
| github.com/charmbracelet/bubbletea | v1.3.10 | Interactive TUI framework |
| github.com/charmbracelet/bubbles | v1.0.0 | TUI components (lists, inputs) |
| github.com/charmbracelet/lipgloss | v1.1.0 | Terminal styling |

## Usage

### CLI Mode (Default)

```bash
# List tasks
monolize task list --task-dir ./tasks

# Dispatch a task
monolize task dispatch my-task --task-dir ./tasks --owner qdriven

# Sync back changes
monolize task sync my-task --task-dir ./tasks
```

### TUI Mode (Interactive)

```bash
# Interactive task list
monolize task list --task-dir ./tasks --tui

# Interactive dispatch (select task with arrow keys)
monolize task dispatch --task-dir ./tasks --owner qdriven --tui

# Interactive sync
monolize task sync --task-dir ./tasks --tui
```

## Configuration

Create `~/.monolize.yaml` for default settings:

```yaml
task_dir: /path/to/tasks
github_owner: qdriven
work_dir: /path/to/workspace
```

## Flow Diagrams

### Dispatch Flow

```
┌─────────────────┐
│   CLI/TUI Mode  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  Select Task    │────▶│  Confirm Action │
│  (TUI: arrows)  │     │  (TUI: y/n)     │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │   Copy Task Files     │
         │   (Spinner Progress)  │
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │   git init            │
         │   git add .           │
         │   git commit          │
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │   gh repo create      │
         │   --public --push     │
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │   Success Message     │
         │   + GitHub URL        │
         └───────────────────────┘
```

### Sync Flow

```
┌─────────────────┐
│   CLI/TUI Mode  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  Select Task    │────▶│  Confirm Action │
│  (TUI: arrows)  │     │  (TUI: y/n)     │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │   Copy from Work Dir  │
         │   to Task Dir         │
         │   (Spinner Progress)  │
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │   Success Message     │
         └───────────────────────┘
```

## File Structure

```
monolize/
├── cmd/
│   └── task.go           # Task CLI commands
├── internal/
│   ├── task/
│   │   └── task.go       # Task business logic
│   └── tui/
│       ├── ui.go         # UI output helpers
│       ├── selector.go   # Interactive selector
│       └── confirm.go    # Confirmation dialog
└── go.mod
```

## Changelog

### 2026-03-15: TUI Support Added

**New Files:**
- `internal/tui/ui.go` - UI output wrapper with pterm
- `internal/tui/selector.go` - Interactive task selector
- `internal/tui/confirm.go` - Confirmation dialog

**Modified Files:**
- `internal/task/task.go` - Added UI support, spinner progress
- `cmd/task.go` - Added --tui flag, dual-mode support

**New Dependencies:**
- github.com/pterm/pterm v0.12.83
- github.com/charmbracelet/bubbletea v1.3.10
- github.com/charmbracelet/bubbles v1.0.0

**Features:**
- Interactive task selection with arrow keys
- Confirmation dialogs before operations
- Progress spinners during file operations
- Styled output with colors and formatting
- Dual mode: CLI (default) and TUI (--tui flag)
