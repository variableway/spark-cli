# Build a Standard Go CLI Project from Scratch

A hands-on tutorial for absolute beginners: start from zero code, end with a
standard Go CLI project that builds, tests, and ships with a Taskfile.
[Golang CLI Essentials · Lesson 1](golang-cli-101.md) explains the *what*;
this tutorial is the *how* — every command works as-is on Windows, Linux,
and macOS.

Using the spark project as the template, you will walk away with:

1. A proper module with `go.mod` / `go.sum`
2. A CLI powered by the Cobra + Viper + PTerm trio
3. The standard `cmd/` + `internal/` layering
4. A cross-platform `Taskfile.yml`
5. An installable SKILL document for AI assistants

---

## 0. Prerequisites

Install Go (1.22+ is fine; this project uses 1.27) from <https://go.dev/dl/>,
then verify:

```bash
go version
# go version go1.27.0 windows/amd64
```

## 1. Step 1: `go mod init` — where go.mod comes from

A Go project starts not with code but by **declaring a module** — the import
path prefix for everything in the project:

```bash
mkdir mycli && cd mycli
go mod init github.com/yourname/mycli
```

The generated `go.mod` is just two lines:

```
module github.com/yourname/mycli

go 1.27.0
```

| Line | Meaning |
|------|---------|
| `module` | The module path. Every package's import path is prefixed with it; convention is the repository URL (spark just uses `spark` — short local names work too) |
| `go` | The minimum Go language version required |

There is **no** `go.sum` and no `require` block yet — both grow automatically
when you add dependencies:

```bash
go get github.com/spf13/cobra@latest
```

Afterwards `go.mod` gains a dependency entry and `go.sum` appears (per-dependency
hash checksums, like a Node lockfile):

```
module github.com/yourname/mycli

go 1.27.0

require github.com/spf13/cobra v1.10.2
```

> Memory hook: **`go mod init` creates the skeleton, `go get` adds dependencies,
> `go.sum` is the tamper-proof receipt.** Both `go.mod` and `go.sum` must be
> committed to Git, otherwise a fresh clone cannot reproduce the build.

## 2. Step 2: install the CLI trio

A decent CLI needs a few wheels. Here are spark's direct dependencies
(the `require` block of its `go.mod`):

| Dependency | Purpose | Install |
|------------|---------|---------|
| `github.com/spf13/cobra` | Commands / subcommands / flags | `go get github.com/spf13/cobra@latest` |
| `github.com/spf13/viper` | Config loading (yaml + env + flags) | `go get github.com/spf13/viper@latest` |
| `github.com/pterm/pterm` | Pretty terminal output (colors, tables, spinners) | `go get github.com/pterm/pterm@latest` |
| `github.com/charmbracelet/bubbletea` (+ `bubbles` / `lipgloss`) | Interactive TUI | `go get github.com/charmbracelet/bubbletea@latest` |
| `github.com/onsi/ginkgo/v2` + `gomega` | BDD test framework | `go get github.com/onsi/ginkgo/v2@latest` |
| `modernc.org/sqlite` | Pure-Go SQLite driver (used by `spark git scan`) | `go get modernc.org/sqlite@latest` |
| `go.yaml.in/yaml/v3` | YAML parsing (registry files) | `go get go.yaml.in/yaml/v3@latest` |

Once everything is in, tidy up — drop unused deps, fill in missing checksums:

```bash
go mod tidy
```

What installation actually does: sources are downloaded to `GOMODCACHE`
(on C: by default; `go env -w` can move it) and **compiled into your binary**
at `go build` time — no `node_modules`, still a single output file.

## 3. Step 3: the standard directory layout

Compare with spark's real layout (full version in [AGENTS.md](../Agents.md)):

```
mycli/
├── main.go            # Entry point: just calls cmd.Execute(), no business logic
├── cmd/               # "Command layer": one package per command group
│   ├── root.go        #   Root command, global flags, config bootstrap
│   └── magic/         #   Subcommand group (spark has git/ repo/ magic/ script/ docs/)
│       └── flush_dns.go
├── internal/          # "Business layer": the real work; compiler forbids external imports
│   ├── config/        #   Config loading
│   ├── git/           #   Git operation wrappers
│   └── ...
├── pkg/               # "Shared layer": public libraries other projects may import
│   └── witr/model/
├── tools/             # Auxiliary CLIs (spark's test-report renderer)
├── scripts/           # Install/verify scripts (bash + powershell pairs)
├── docs/              # Docs site (see the docs-site tutorial)
├── go.mod / go.sum    # Dependency manifest + checksums (must be committed)
├── Makefile           # Unix build entry
└── Taskfile.yml       # Cross-platform build entry (preferred on Windows)
```

| Directory | Responsibility | In one sentence |
|-----------|----------------|-----------------|
| `main.go` | Program entry | Does exactly one thing: call `cmd.Execute()` |
| `cmd/` | Command definitions | Cobra commands and flag bindings; thin, no business logic |
| `internal/` | Business logic | Go-enforced: other modules cannot import from here |
| `pkg/` | Public libraries | Only put things here if you want them reused |
| `scripts/` | Build helpers | Binary installation, sha256 verification |

The complete `main.go` (spark is exactly this):

```go
package main

import "spark/cmd"

func main() {
    cmd.Execute()
}
```

> Memory hook: **commands in `cmd/`, logic in `internal/`, the entry point is
> just a messenger.**

## 4. Step 4: your first command

`cmd/root.go` defines the root command and global flags (excerpted from spark):

```go
package cmd

import (
    "github.com/spf13/cobra"
    "github.com/spf13/viper"
)

var rootCmd = &cobra.Command{
    Use:   "mycli",
    Short: "A CLI tool that does useful things",
}

func Execute() {
    if err := rootCmd.Execute(); err != nil {
        return
    }
}

func init() {
    cobra.OnInitialize(initConfig)
    rootCmd.PersistentFlags().StringSliceP("path", "p", []string{"."}, "Directory to scan")
    viper.BindPFlag("repo-path", rootCmd.PersistentFlags().Lookup("path"))
}
```

One subcommand per file (modeled on `cmd/magic/flush_dns.go`):

```go
package magic

import (
    "github.com/spf13/cobra"
    "github.com/pterm/pterm"
)

var flushDNSCmd = &cobra.Command{
    Use:   "flush-dns",
    Short: "Flush DNS cache on the current system",
    RunE: func(cmd *cobra.Command, args []string) error {
        pterm.Success.Println("DNS cache flushed!")
        return nil
    },
}

func init() {
    MagicCmd.AddCommand(flushDNSCmd)
}
```

Three key points:

1. `Use` is the command name; `RunE` is the body (return an error instead of
   calling `os.Exit` yourself)
2. `func init()` calls `AddCommand` to attach the subcommand — every file
   self-registers, no central registry needed
3. Output through `pterm` gives users colored success/warning messages

Verify:

```bash
go run . flush-dns
go build -o bin/mycli . && ./bin/mycli --help
```

## 5. Step 5: writing a Taskfile build script

**Why a Taskfile**: real build commands get long (ldflags version stamping,
installing to `~/.local/bin`, sha256 verification…); retyping them is
impractical, and Windows often lacks `make`. [Task](https://taskfile.dev) is a
Go-written task runner — a single binary, YAML-declared, cross-platform —
that fills the gap.

First, the skeleton of spark's `Taskfile.yml`:

```yaml
version: '3'

vars:                    # Global variables
  BINARY_NAME: spark
  BIN_DIR: bin
  VERSION:               # Dynamic variable: sh: runs a shell command, uses its output
    sh: cat internal/witr/version/VERSION 2>/dev/null || echo dev

env:
  CGO_ENABLED: '0'       # Pure-Go build, produces a portable static binary

tasks:
  build:
    desc: Build for current OS into bin/, stamp version, install to ~/.local/bin
    cmds:
      - task: prepare-bin          # Reference another task (creates bin/ first)
      - cmd: '{{.GO}} build -ldflags="-s -w -X spark/internal/witr/version.Version=v{{.VERSION}}" -o {{.BIN_DIR}}/{{.BINARY_NAME}}{{exeExt}} main.go'
      - cmd: powershell -NoProfile -ExecutionPolicy Bypass -File scripts/install-binary.ps1 ...
        platforms: [windows]       # Platform dispatch: Windows/Linux each run their own
      - cmd: bash scripts/install-binary.sh ...
        platforms: [linux, darwin]

  cross-build:           # Internal task: hidden from task --list, reused by cross-compiles
    internal: true
    requires:
      vars: [GOOS, GOARCH, OUTPUT]   # Callers must provide these
    env:
      GOOS: '{{.GOOS}}'              # Cross-compiling only needs these env vars
      GOARCH: '{{.GOARCH}}'
    cmds:
      - '{{.GO}} build -o {{.OUTPUT}} main.go'

  build:linux:           # Public target: fill in vars, then call cross-build
    cmds:
      - task: cross-build
        vars: { GOOS: linux, GOARCH: amd64, OUTPUT: 'bin/spark_linux' }
```

The essentials, one by one:

- **`vars`**: literal values, or `sh:` to run a shell command and capture output
- **`cmds`**: executed in order; `task:` references another task (a function call)
- **`platforms`**: per-OS dispatch within one task — the core of cross-platform support
- **`internal: true`**: hidden helper task, not shown by `task --list`
- **`requires.vars`**: forces callers to pass arguments; missing ones fail fast
- **`{{exeExt}}`**: built-in Task variable — `.exe` on Windows, empty elsewhere
- **`ignore_error: true`**: tolerate a failure and keep going (e.g. run all tests,
  then render the report)

A minimal template for a new project:

```yaml
version: '3'

vars:
  BINARY_NAME: mycli
  BIN_DIR: bin

tasks:
  build:
    desc: Build for the current OS
    cmds:
      - go build -o {{.BIN_DIR}}/{{.BINARY_NAME}}{{exeExt}} .

  test:
    desc: Run all tests
    cmds:
      - go test ./...

  lint:
    desc: Run go vet
    cmds:
      - go vet ./...

  clean:
    desc: Remove build artifacts
    cmds:
      - cmd: powershell -NoProfile -Command "Remove-Item -Recurse -Force {{.BIN_DIR}}"
        platforms: [windows]
      - cmd: rm -rf {{.BIN_DIR}}
        platforms: [linux, darwin]
```

Install Task itself: `go install github.com/go-task/task/v3/cmd/task@latest`,
then run `task --list` to see all targets and `task build` to start using them.
The Makefile and Taskfile in this project expose identical targets, so
Linux/macOS users can equally use `make`.

## 6. Wrap-up: the pre-commit checklist

```text
✅ go.mod / go.sum committed (never gitignore them)
✅ bin/ added to .gitignore (build artifacts stay out of the repo)
✅ go mod tidy run, no stray dependencies
✅ go vet ./... passes
✅ go test ./... passes
```

When installing to `~/.local/bin` on Windows, keep both `mycli.exe` and the
extension-less `mycli` (bash prefers the latter) — that's what spark's
`install-binary.ps1` does.

---

## Appendix: SKILL — golang-project-from-scratch

Save as `SKILL.md` (e.g. `.claude/skills/golang-project-from-scratch/SKILL.md`)
and an AI assistant can scaffold a standard Go CLI project for you the spark way:

```markdown
---
name: golang-project-from-scratch
description: Create a Go CLI project from scratch following the standard flow
  (go mod init, the Cobra/Viper/PTerm trio, cmd+internal layering, Taskfile
  builds). Use when the user asks to "create a Go CLI project / scaffold a Go
  project / standardize a Go project layout".
---

# Build a Standard Go CLI Project from Scratch

Execute in this order, confirming with the user after each step:

1. **Module init** — `go mod init <module-path>` (use the repo URL); explain the
   module/go lines; state that go.mod and go.sum must be committed.
2. **Dependencies** — `go get` as needed: cobra (commands), viper (config),
   pterm (output), bubbletea (TUI), ginkgo+gomega (BDD tests); finish with
   `go mod tidy`.
3. **Layering** — main.go only calls cmd.Execute(); cmd/ defines commands (one
   file per subcommand, self-registered via AddCommand in init()); all business
   logic in internal/; only genuinely reusable code in pkg/; build helpers in
   scripts/.
4. **First command** — root command plus a demo subcommand (Use/Short/RunE
   trio, RunE returns an error); verify with `go run .`, then
   `go build -o bin/<name> .`.
5. **Taskfile** — write Taskfile.yml (vars/cmds/platforms essentials; cross
   compile via GOOS/GOARCH plus an internal cross-build task with
   requires.vars; {{exeExt}} for the suffix); provide build/test/lint/clean.
6. **Wrap-up** — gitignore bin/; run go vet ./... and go test ./....

Reference implementation: github.com/variableway/spark-cli (Cobra+Viper+PTerm,
Makefile and Taskfile as dual entry points). Build details in its
docs/en/usage/how-to-build.md.
```

---

## Further reading

- [Golang CLI Essentials · Lesson 1](golang-cli-101.md) — the concepts; do that first, then this
- [How to Build](../usage/how-to-build.md) — building an existing project, cross-compiling, pnpm setup
- [Docs Site from Scratch](docs-site-from-scratch.md) — the other half of this project: the Node world
