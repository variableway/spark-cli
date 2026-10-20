# Golang CLI Essentials · Lesson 1

For absolute beginners: use the spark project as the textbook and learn how a
Go command-line tool is actually made. After this lesson you should be able to
answer four questions:

1. What are the **basic techniques** for writing a CLI in Go?
2. How do you **use third-party packages**?
3. How do you **manage dependencies**?
4. What are **Makefile / Taskfile** for?

---

## 1. Basics: a CLI is just a Go program

Go compiles to a **single executable** — users don't need a runtime. A typical
CLI layout:

```
main.go            entry point: calls cmd.Execute()
cmd/               one file per command / subcommand
internal/          business logic (invisible outside the module)
go.mod             dependency manifest (like a shopping list)
go.sum             dependency checksums (tamper-proofing)
```

In spark, `main.go` is just a few lines:

```go
package main

import "spark/cmd"

func main() {
    cmd.Execute()
}
```

How are commands defined? With the third-party library **Cobra** — the
"command + subcommand + flag" trio:

```go
var flushDNSCmd = &cobra.Command{
    Use:   "flush-dns",
    Short: "Flush DNS cache",
    RunE: func(cmd *cobra.Command, args []string) error {
        return magic.FlushDNS()   // real work lives in internal/
    },
}
```

Config? **Viper** reads `~/.spark.yaml`, environment variables and flags with a
clear precedence (flags > config file > env).

Pretty terminal output? **PTerm**. Interactive TUI? **Bubble Tea**.

> Memory hook: **Cobra = commands, Viper = config, PTerm = output,
> internal/ = logic.**

## 2. Using third-party packages

A Go package *is* a Git repository; the import path is the repo URL:

```go
import (
    "github.com/spf13/cobra"   // CLI framework
    "github.com/spf13/viper"   // config loading
    "github.com/pterm/pterm"   // terminal styling
)
```

Install (download and record in go.mod):

```bash
go get github.com/spf13/cobra@latest
```

`go build` then compiles those sources into your binary — **no node_modules,
still one file**.

## 3. Managing dependencies

| File | Purpose | Node analogue |
|------|---------|---------------|
| `go.mod` | module name, Go version, dependency list | `package.json` |
| `go.sum` | checksum of each dependency | `pnpm-lock.yaml` |

Common commands:

```bash
go get  <pkg>@latest   # add / upgrade a dependency
go mod tidy            # add missing ones, drop unused ones (most used)
go mod download        # download deps into the local cache
go list -m all         # list all dependencies and versions
```

Three good habits:

1. **Commit `go.mod` and `go.sum`** — otherwise others can't reproduce the build
2. Upgrade with `go get pkg@latest` instead of hand-editing versions
3. Run `go mod tidy` when the dependency list feels stale

Caches live in `GOCACHE` / `GOMODCACHE` (on C: by default).

## 4. What Makefile / Taskfile are for

They turn long commands into short ones — **a task list, not a programming
language**.

| Goal | Without | With Makefile / Taskfile |
|------|---------|--------------------------|
| Build | `go build -ldflags='...' -o spark.exe main.go` | `make build` / `task build` |
| Test | `go test ./... -v` | `make test` / `task test` |
| Cross-compile | `GOOS=windows GOARCH=amd64 go build ...` | `task build:windows` |
| Clean | delete files by hand | `make clean` / `task clean` |

- **Makefile** — the Unix standard (`make`), preinstalled on Linux/macOS;
  on Windows it needs extra setup, so this project also ships —
- **Taskfile.yml** — the `task` runner (written in Go), cross-platform and
  friendlier on Windows.

The two mirror each other target-for-target (`build` / `test` / `lint` /
`clean` …); pick either. Open `Taskfile.yml`: under each `tasks:` entry, `cmds:`
is simply "which commands run when you press this button".

---

## 5. What about the docs site? (Node ecosystem)

The `docs/` site is a different world: **Node + pnpm + docmd** — same build
idea: `pnpm install` (≈ go mod tidy) → `pnpm build` (≈ go build) → output in
`site/`. See [How to Build](../usage/how-to-build.md) for the full comparison.

---

## Appendix A: course prompt (copy into your AI assistant)

```text
You are my Go CLI mentor. I am a complete beginner. Use the spark-cli project
as the textbook and teach me in four lessons; each lesson = one-sentence
concept + one runnable mini-example + one exercise.
1) Basics: main.go / cmd/ / internal/ layering, Cobra commands and flags,
   Viper config
2) Third-party packages: import path = repo URL, go get
3) Dependency management: go.mod / go.sum, go mod tidy, upgrading versions
4) Makefile and Taskfile: why task lists exist, how to read a target
Rules: one lesson at a time; prefer real files from the project; exercises
must be doable in 5 minutes on Windows; wait for my answer before the next
lesson.
```

## Appendix B: Skill (SKILL.md)

Save as `SKILL.md` (e.g. `~/.codex/skills/golang-cli-101/SKILL.md` or
`.claude/skills/golang-cli-101/SKILL.md`) to install it as "CLI Lesson 1":

```markdown
---
name: golang-cli-101
description: Lesson 1 of Go CLI for beginners. Use when the user wants to
  learn writing CLIs in Go, understand go.mod/Cobra/Makefile, or asks for a
  "CLI intro / first lesson".
---

# Go CLI essentials — Lesson 1

Teach four lessons from real project files, one 5-minute exercise each:

1. **Basics** — read `main.go`, `cmd/` (Cobra commands), `internal/`
   (business logic); explain the command -> flag -> function call chain.
2. **Third-party packages** — with `github.com/spf13/cobra`, `spf13/viper`,
   `pterm/pterm`: import path is the repo URL; `go get` installs and compiles
   everything into a single binary.
3. **Dependency management** — `go.mod` (manifest) + `go.sum` (checksums);
   demo `go mod tidy` and `go get pkg@latest`; stress both files must be
   committed.
4. **Makefile / Taskfile** — open `Makefile` and `Taskfile.yml` side by side
   for the `build/test/lint/clean` targets; they are just command shortcuts.

Teaching rules: one lesson at a time; Chinese explanations with code kept in
English; one exercise per lesson and wait for the answer; after the final
lesson suggest three next steps (flag binding, table-driven tests,
cross-compiling).
```

---

Next step: run `task build` (Windows) or `make build`, then `spark version`
to verify — you just passed the graduation build of Lesson 1.
