# Golang CLI Application

Build a production-grade Go CLI application using Cobra + Viper + Bubble Tea/PTerm, tested with Ginkgo/Gomega.

## Project Structure

```
project/
├── main.go                  # Entry point, calls cmd.Execute()
├── go.mod
├── Makefile
├── cmd/                     # CLI command definitions (Cobra)
│   ├── root.go              # Root command, config init, persistent flags
│   ├── git/                 # Command group: git-related
│   │   ├── update.go
│   │   └── clone.go
│   └── magic/               # Command group: system utilities
│       └── flush_dns.go
├── internal/                # Business logic (not importable externally)
│   ├── config/              # Config loading and management
│   ├── git/                 # Domain: git operations
│   ├── github/              # Domain: GitHub API
│   └── tui/                 # Shared TUI components (spinner, dialogs, selector)
└── docs/usage/              # Usage docs per command
```

**Key rule**: `cmd/` only defines CLI interface (flags, help text, RunE). All business logic lives in `internal/`.

## Core Dependencies

```
github.com/spf13/cobra          # CLI framework
github.com/spf13/viper          # Configuration management
github.com/pterm/pterm          # Rich terminal output
github.com/charmbracelet/bubbletea  # Interactive TUI
github.com/onsi/ginkgo/v2       # BDD test framework
github.com/onsi/gomega           # Test matchers
```

## Entry Point

`main.go` should be minimal:

```go
package main

import "spark/cmd"

func main() {
    cmd.Execute()
}
```

## Root Command Pattern

`cmd/root.go`:

```go
package cmd

import (
    "os"
    "github.com/spf13/cobra"
    "github.com/spf13/viper"
)

var cfgFile string

var rootCmd = &cobra.Command{
    Use:   "spark",
    Short: "A CLI tool for managing repos, agents, scripts, and tasks",
}

func Execute() {
    if err := rootCmd.Execute(); err != nil {
        os.Exit(1)
    }
}

func init() {
    cobra.OnInitialize(initConfig)
    rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "", "config file (default is $HOME/.spark.yaml)")
}

func initConfig() {
    if cfgFile != "" {
        viper.SetConfigFile(cfgFile)
    } else {
        home, _ := os.UserHomeDir()
        viper.AddConfigPath(home)
        viper.SetConfigName(".spark")
        viper.SetConfigType("yaml")
    }
    viper.AutomaticEnv()
    viper.ReadInConfig()
}
```

## Command Definition Pattern

Each command is a `cobra.Command` variable with `init()` registering it to its parent:

```go
package git

import (
    "github.com/spf13/cobra"
    "github.com/spf13/viper"
)

var updateCmd = &cobra.Command{
    Use:   "update",
    Short: "Update all git repositories",
    RunE: func(cmd *cobra.Command, args []string) error {
        paths := viper.GetStringSlice("repo_path")
        return internalgit.UpdateRepos(paths)
    },
}

func init() {
    updateCmd.Flags().BoolP("force", "f", false, "Force update even if dirty")
    viper.BindPFlag("force", updateCmd.Flags().Lookup("force"))
    GitCmd.AddCommand(updateCmd)
}
```

**Conventions**:
- Use `RunE` (not `Run`) to return errors
- Bind flags to Viper in `init()` with `viper.BindPFlag()`
- Config keys use `snake_case` in YAML, `mapstructure` tags on structs
- Parent commands are defined in the same package, subcommands register via `init()`

## Command Group Pattern

Group related commands under a parent command in a subdirectory:

```go
// cmd/git/git.go
package git

import "github.com/spf13/cobra"

var GitCmd = &cobra.Command{
    Use:   "git",
    Short: "Git repository management",
}

// cmd/git/update.go registers updateCmd via init()
// cmd/git/clone.go registers cloneCmd via init()
```

Then in `cmd/root.go`:

```go
func init() {
    rootCmd.AddCommand(git.GitCmd)
}
```

## Config Management

### Config File (~/.spark.yaml)

```yaml
repo_path:
  - ~/workspace
git:
  user_name: "user"
  user_email: "user@example.com"
github_owner: "myorg"
work_dir: "~/workspace"
```

### Config Struct Pattern

```go
type Config struct {
    RepoPath     []string `mapstructure:"repo_path"`
    GitUserName  string   `mapstructure:"git.user_name"`
    GitUserEmail string   `mapstructure:"git.user_email"`
}
```

Load config:

```go
var cfg Config
viper.Unmarshal(&cfg)
```

### Priority Order

Command-line flags > Environment variables > Config file > Defaults

## TUI Pattern

### Dual Mode (CLI vs TUI)

Commands accept `--tui` flag for interactive mode:

```go
var useTUI bool

func init() {
    myCmd.Flags().BoolVar(&useTUI, "tui", false, "Use interactive TUI mode")
}

// In RunE:
ui := tui.New(useTUI)
ui.Info("Processing...")
```

### TUI Abstraction Layer

`internal/tui/` provides a unified interface:

```go
type UI struct {
    useTUI bool
}

func New(useTUI bool) *UI { return &UI{useTUI: useTUI} }

func (u *UI) Info(msg string) {
    if u.useTUI {
        // Bubble Tea styled output
    } else {
        pterm.Info.Printfln(msg)
    }
}

func (u *UI) Success(msg string) { /* ... */ }
func (u *UI) Error(msg string)   { /* ... */ }
func (u *UI) Spinner(msg string, action func() error) error { /* ... */ }
func (u *UI) Table(headers []string, rows [][]string) { /* ... */ }
func (u *UI) Confirm(msg string) bool { /* ... */ }
```

### PTerm for Rich Output

```go
pterm.Info.Printfln("Found %d repos", count)
pterm.Success.Printfln("Done!")
pterm.Error.Printfln("Failed: %v", err)
pterm.DefaultTable.WithHasHeader().WithData(tableData).Render()
```

### Bubble Tea for Interactive Selection

Use Bubble Tea for complex interactive flows: multi-select lists, form inputs, real-time updates.

## Business Logic Pattern

Keep `internal/` packages focused and composable:

```go
// internal/git/update.go
package git

func UpdateRepos(paths []string) error {
    for _, path := range paths {
        repos, err := FindRepos(path)
        if err != nil {
            return err
        }
        for _, repo := range repos {
            if err := pullRepo(repo); err != nil {
                log.Printf("warning: %s: %v", repo, err)
            }
        }
    }
    return nil
}
```

**Rules**:
- Functions accept and return plain Go types
- No direct Cobra/Viper dependency in `internal/`
- Errors are returned, not printed (let `cmd/` layer handle display)
- Use `log.Printf` for warnings, return errors for failures

## BDD Testing with Ginkgo/Gomega

### Suite File (`internal/git/git_suite_test.go`)

```go
package git_test

import (
    "testing"
    . "github.com/onsi/ginkgo/v2"
    . "github.com/onsi/gomega"
)

func TestGit(t *testing.T) {
    RegisterFailHandler(Fail)
    RunSpecs(t, "Git Suite")
}
```

### Test File (`internal/git/update_test.go`)

```go
package git_test

import (
    . "github.com/onsi/ginkgo/v2"
    . "github.com/onsi/gomega"
    "spark/internal/git"
)

var _ = Describe("UpdateRepos", func() {
    Context("when path is valid", func() {
        It("should find and update repositories", func() {
            err := git.UpdateRepos([]string{"testdata/repos"})
            Expect(err).NotTo(HaveOccurred())
        })
    })

    Context("when path does not exist", func() {
        It("should return an error", func() {
            err := git.UpdateRepos([]string{"/nonexistent"})
            Expect(err).To(HaveOccurred())
        })
    })
})
```

**Conventions**:
- Test files live alongside source in `internal/`
- Use `_suite_test.go` for Ginkgo runner registration
- Use `Describe/Context/It` structure for clarity
- Package uses `_test` suffix (e.g., `package git_test`) for black-box testing

## Makefile

```makefile
BINARY_NAME=spark
GO=go

.PHONY: build build-linux build-darwin test test-bdd lint clean

build:
	$(GO) build -ldflags="-s -w" -o $(BINARY_NAME) main.go
	install -d ~/.local/bin
	install $(BINARY_NAME) ~/.local/bin/

build-linux:
	GOOS=linux GOARCH=amd64 $(GO) build -ldflags="-s -w" -o $(BINARY_NAME)_linux main.go

build-darwin:
	GOOS=darwin GOARCH=amd64 $(GO) build -ldflags="-s -w" -o $(BINARY_NAME)_darwin main.go

test:
	$(GO) test ./... -v

test-bdd:
	$(GO) test ./internal/... -v

lint:
	$(GO) vet ./...

clean:
	rm -f $(BINARY_NAME) $(BINARY_NAME)_linux $(BINARY_NAME)_darwin
```

## Adding a New Command

1. Create command file: `cmd/<group>/<command>.go`
2. Define `cobra.Command` with `Use`, `Short`, `RunE`
3. Add flags in `init()`, bind with Viper
4. Register to parent command: `ParentCmd.AddCommand(myCmd)`
5. Implement logic in `internal/<domain>/<feature>.go`
6. Write BDD tests: `internal/<domain>/<feature>_test.go`
7. Add suite file if package is new: `internal/<domain>/<domain>_suite_test.go`
8. Add usage doc: `docs/usage/<command>.md`
9. Run `make test` to verify

## Checklist

- [ ] `main.go` is minimal (just `cmd.Execute()`)
- [ ] Command definitions in `cmd/`, logic in `internal/`
- [ ] Flags bound to Viper via `viper.BindPFlag()`
- [ ] `RunE` used instead of `Run` for error propagation
- [ ] BDD tests with Ginkgo/Gomega alongside source files
- [ ] `Makefile` targets: build, test, lint, clean
- [ ] Cross-compilation targets for target platforms
- [ ] Usage documentation in `docs/usage/`
- [ ] TUI abstraction for dual-mode (CLI + interactive)
