# Learn Points of Git-Monolize

This document summarizes the key technical aspects and usage of the Git-Monolize project.

---

## 1. Project Tech Stack Summary
- **Programming Language**: Go 1.24.2
- **CLI Framework**: [Cobra](https://github.com/spf13/cobra) - Powerful framework for building CLI applications.
- **Configuration**: [Viper](https://github.com/spf13/viper) - Versatile Go configuration solution.
- **Testing Framework**: [Ginkgo](https://onsi.github.io/ginkgo/) & [Gomega](https://onsi.github.io/gomega/) - BDD-style testing framework and matcher library.
- **Build System**: Makefile - Support for multi-platform (Windows, Linux, macOS).
- **Environment Management**: VS Code integration via `.vscode` configuration.

---

## 2. CLI Usage Notes (Non-Technical)
This tool is designed to manage multiple Git repositories.

### 1. How to get help?
If you're unsure about any command, use the `-h` or `--help` flag:
```bash
monolize --help
monolize update --help
```

### 2. Passing Parameters
Parameters allow you to specify how the command should run. Most use the format `--key value` or `-k value`:
- **Path**: Use `--path` or `-p` to tell the tool where your repositories are.
- **Name**: Use `--name` or `-n` to specify a name for a new mono-repo.
- **Output**: Use `--output` to specify where to save the result.

### 3. Setting Up Environment Variables (Path)
To use `monolize` from anywhere, add it to your system's PATH.
- **Windows**:
    1. Open "Environment Variables" in System Properties.
    2. Edit "Path" under "User variables".
    3. Add the folder path where `monolize.exe` is located.
- **Linux / macOS**:
    1. Open your shell config (e.g., `~/.bashrc` or `~/.zshrc`).
    2. Add: `export PATH=$PATH:/path/to/your/monolize_folder`
    3. Run `source ~/.bashrc` or `source ~/.zshrc`.

### 4. Subcommands
`monolize` uses subcommands for different tasks:
- `monolize update`: Updates repositories in a given path.
- `monolize create`: Creates a new mono-repo from multiple sub-repos.
- `monolize sync`: Synchronizes submodules within a mono-repo.

---

## 3. Key Implementation Points (with Code Examples)

### 1. Cobra for CLI Command Application
Cobra defines the structure of our commands.
- **File**: [root.go](file:///d:/workspace/innate/use-cases/daily-use/git-monolize/cmd/root.go)
```go
var rootCmd = &cobra.Command{
    Use:   "monolize",
    Short: "A CLI tool to manage multiple git repositories",
    // ... logic ...
}
```

### 2. Viper for Configuration File
Viper handles loading settings from files or environment variables.
- **File**: [config.go](file:///d:/workspace/innate/use-cases/daily-use/git-monolize/internal/config/config.go)
```go
func Load() (*Config, error) {
    var cfg Config
    // ... set defaults ...
    viper.SetDefault("path", ".")
    // ... unmarshal config ...
    if err := viper.Unmarshal(&cfg); err != nil {
        return nil, err
    }
    return &cfg, nil
}
```

### 3. Dependency Management
Go uses `go.mod` to track dependencies.
- **File**: [go.mod](file:///d:/workspace/innate/use-cases/daily-use/git-monolize/go.mod)
```go
module monolize

go 1.24.2

require (
    github.com/spf13/cobra v1.10.2
    github.com/spf13/viper v1.21.0
    // ... other packages ...
)
```

### 4. Key Golang Features Used

- **Basic Language (Types/Variables)**:
  - Example in [root.go](file:///d:/workspace/innate/use-cases/daily-use/git-monolize/cmd/root.go#L11): `var cfgFile string`
- **Functions**:
  - Example in [finder.go](file:///d:/workspace/innate/use-cases/daily-use/git-monolize/internal/git/finder.go#L11): `func FindRepositories(rootPath string) ([]string, error)`
- **Structures**:
  - Example in [config.go](file:///d:/workspace/innate/use-cases/daily-use/git-monolize/internal/config/config.go#L8-L12):
    ```go
    type Config struct {
        Path          string `mapstructure:"path"`
        DefaultBranch string `mapstructure:"default_branch"`
        AutoCommit    bool   `mapstructure:"auto_commit"`
    }
    ```
- **Error Handling**:
  - Example in [finder.go](file:///d:/workspace/innate/use-cases/daily-use/git-monolize/internal/git/finder.go#L23-L25):
    ```go
    entries, err := os.ReadDir(rootPath)
    if err != nil {
        return nil, err
    }
    ```
- **For-loops**:
  - Example in [finder.go](file:///d:/workspace/innate/use-cases/daily-use/git-monolize/internal/git/finder.go#L27):
    ```go
    for _, entry := range entries {
        // ... loop body ...
    }
    ```
- **Package Invocation**:
  - `main.go` calls `cmd.Execute()` from the `cmd` package.
  - [main.go](file:///d:/workspace/innate/use-cases/daily-use/git-monolize/main.go#L11): `cmd.Execute()`
- **init() Function**:
  - Used for initialization before `main()` or other functions run.
  - Example in [root.go](file:///d:/workspace/innate/use-cases/daily-use/git-monolize/cmd/root.go#L29-L34):
    ```go
    func init() {
        cobra.OnInitialize(initConfig)
        // ... setup flags ...
    }
    ```
