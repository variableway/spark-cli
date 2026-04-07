# CI/CD Config

## Support Windows ,Linux,Mac Build 

1. current build/make script doesn't support windows build.
2. fix it to support build in windows
3. Use [task](https://taskfile.dev/docs) to support build in windows,and other platforms include Mac,Linux

## Status: Done

### Changes

- Created `Taskfile.yml` using [Taskfile](https://taskfile.dev) (v3) as the cross-platform build system
- Supports Windows, Linux, and macOS builds with platform-specific commands
- Uses `platforms` key to conditionally run commands per OS
- Uses `env` key for cross-compilation (avoids `VAR=val command` which doesn't work on Windows)
- Added `.task/` and `spark_*` to `.gitignore`
- Installed `task` v3.49.1 via `go install`

### Available Tasks

```
task build           # Build for current OS and install
task build:all       # Cross-compile all platforms
task build:linux     # Cross-compile Linux amd64
task build:linux:arm64
task build:darwin    # Cross-compile macOS amd64
task build:darwin:arm64
task build:windows   # Cross-compile Windows amd64
task build:windows:arm64
task test            # Run all tests
task test-bdd        # Run BDD tests
task lint            # Run go vet
task clean           # Remove build artifacts
task install         # Build and install
task run             # Build and run
```