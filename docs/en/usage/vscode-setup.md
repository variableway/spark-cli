# VS Code Setup

The project's `.vscode` directory ships a complete configuration intended to deliver a seamless Go development experience.

## Core Files

### 1. [tasks.json](../.vscode/tasks.json)
Defines the common build and test tasks, deeply integrated with the `Makefile`.
- **Default build task (`Ctrl+Shift+B`)**: runs `make build`.
- **Default test task**: runs `make test`.
- **BDD tests**: runs `make test-bdd`.
- **Clean task**: runs `make clean`.

### 2. [launch.json](../.vscode/launch.json)
Presets a variety of debug scenarios:
- **Debug Main**: debug the main entry point (`main.go`).
- **Debug Current File**: debug the currently selected `.go` file.
- **Debug Test Current File**: debug the currently selected test file.
- **Debug All Tests**: run and debug every test in the project.
- **Attach to Delve**: attach to an already running Delve debugger.

### 3. [settings.json](../.vscode/settings.json)
Tweaks editor behavior:
- **Auto-format**: automatically runs `go fmt` and `goimports` on save.
- **Linting**: enables real-time checks via `golangci-lint`.
- **Code Lens**: surfaces test runner and reference shortcuts inline.

## Requirements
- **VS Code extension**: the [Go for Visual Studio Code](https://marketplace.visualstudio.com/items?itemName=golang.Go) extension is required.
- **Toolchain**: installing `make` is recommended for the best experience.
