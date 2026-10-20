# How to Build

This project produces **two artifacts with two toolchains**. The idea is the
same for both — install toolchain → fetch dependencies → build → place the
output:

| Artifact | Ecosystem | Dependency mgmt | Task entry | Output |
|----------|-----------|-----------------|------------|--------|
| `spark` CLI | **Go** | `go.mod` / `go.sum` | `Makefile` / `Taskfile.yml` | single binary `spark(.exe)` |
| Docs site | **Node** | `package.json` / `pnpm-lock.yaml` | `package.json` scripts | static site `site/` |

> Put simply: Go builds *one executable*, Node (the docs site) builds *a bunch
> of HTML pages*. Go uses `go build`, Node uses `docmd build` — same flow,
> different tools.

---

## 1. Go binary (golang ecosystem)

### Build & install

```bash
# Linux / macOS
make build

# Windows (use task when make is unavailable; they are equivalent)
task build
```

What it does:

1. `go build -ldflags='...version stamp...' -o bin/spark.exe main.go`
   — output always lands in the project's `bin/` directory; version / commit /
   build date are stamped into the binary
2. `scripts/install-binary.ps1` (or `.sh`) installs to `~/.local/bin/`
   On Windows both `spark.exe` and the extension-less `spark` are written
   (bash matches the latter first, so they must stay in sync)
3. `scripts/verify-install.ps1` compares sha256 of source and installed copies

Self-check:

```bash
spark version    # -> spark v0.3.2 / commit xxx / build date ...
spark --version  # -> spark version v0.3.2
```

### Cross-compile

Go cross-compilation only needs different environment variables:

```bash
task build:windows        # bin/spark_windows.exe       (amd64)
task build:windows:arm64  # bin/spark_windows_arm64.exe (arm64)
task build:linux          # bin/spark_linux
task build:darwin         # bin/spark_darwin
task build:all            # all platforms; everything lands in bin/ (gitignored)
```

### Test & lint

```bash
task test           # go test ./...
task test-bdd       # ginkgo BDD tests
task lint           # go vet ./...
```

---

## 2. Docs site (Node ecosystem)

The docs site is a standard Node project — exactly parallel to "Go manages
deps with go.mod":

| Go | Node (this project) | Purpose |
|----|---------------------|---------|
| `go.mod` | `package.json` | declare project + dependencies |
| `go.sum` | `pnpm-lock.yaml` | lock dependency versions |
| `go get <pkg>` | `pnpm add <pkg>` | add a dependency |
| `go mod tidy` | `pnpm install` | install per the manifest |
| `go build` | `pnpm build` (`docmd build`) | build the output |
| `go run` | `pnpm dev` | run locally |
| `~/.cache/go-build` | `D:\.pnpm-store` | dependency cache (can move to D: to save disk) |

### Commands

```bash
pnpm install    # install deps (hard-linked from the pnpm store)
pnpm build      # docmd build -> site/ (zh at root, en at /en/)
pnpm dev        # local dev server
pnpm preview    # static preview of site/
```

Output: 50+ static pages under `site/`, including search index, sitemap and
llms.txt. Configuration lives in `docmd.config.js` (`i18n.default: 'zh'`:
Chinese renders at the root URL, English at `/en/`).

---

## 3. Bun: the Node ecosystem can also build binaries

"Go makes binaries, Node makes HTML" is **not quite true**. With
[Bun](https://bun.sh)'s `bun build --compile`, TypeScript/JavaScript compiles
into a **single self-contained binary** that runs anywhere, just like a Go
binary:

```bash
bun build src/index.ts --compile --outfile mycli        # current platform
bun build src/index.ts --compile --target bun-windows-x64 --outfile mycli.exe
bun build src/index.ts --compile --target bun-darwin-arm64 --outfile mycli-mac
bun build src/index.ts --compile --target bun-linux-x64 --outfile mycli-linux
```

Real example: `innate-fe-cli` (25 modules, zero npm runtime deps) builds a
~96MB `innate-fe-cli.exe` in one command; install it into `~/.local/bin` and
it is available globally:

```bash
cd innate-fe-cli && bun install && bun run build:exe:win
cp ../../bin/innate-fe-cli.exe ~/.local/bin/

# Windows: let several command names share one copy of the data (NTFS hardlinks)
cd ~/.local/bin
fsutil hardlink create innate-fe innate-fe-cli.exe
fsutil hardlink create innate-fe.exe innate-fe-cli.exe
```

| | Go | Bun (`--compile`) | Node (docmd-style) |
|--|----|-------------------|--------------------|
| Output | single binary | single binary | needs `node`/`pnpm` to run |
| Cross-compile | `GOOS/GOARCH` | `--target bun-<os>-<arch>` | none (plain JS) |
| Size | ~17MB | ~96MB (Bun runtime included) | KB + node_modules |
| Fit for | system CLIs | frontend-engineering CLIs | docs sites / build scripts |

> Memory hook: **Go and Bun can both "ship one file"; plain Node projects can
> only "ship source + node_modules"**. Choose by distribution model.

---

## 4. pnpm on Windows (save C: drive space)

Goal: pnpm available system-wide, with **store / global packages / global bin
on D:**.

```bash
npm i -g pnpm@latest     # the CLI itself is tiny; keep it under the Node prefix

pnpm config set store-dir      "D:\.pnpm-store"  --global
pnpm config set global-dir     "D:\pnpm\global"  --global
pnpm config set global-bin-dir "D:\pnpm\bin"     --global
```

Verify:

```bash
pnpm store path   # -> D:\.pnpm-store\v11
pnpm root -g      # -> D:\pnpm\global\v11
pnpm bin -g       # -> D:\pnpm\bin
```

Windows environment variables:

| Variable | Value |
|----------|-------|
| `PNPM_HOME` (User) | `D:\pnpm` |
| `Path` (User) | starts with `D:\pnpm\bin` (replacing the old `%LOCALAPPDATA%\pnpm*` entries) |

```powershell
[Environment]::SetEnvironmentVariable('PNPM_HOME', 'D:\pnpm', 'User')
$p = [Environment]::GetEnvironmentVariable('Path', 'User')
$parts = $p -split ';' | Where-Object { $_.Trim() -ne '' -and $_ -notlike '*\AppData\Local\pnpm*' }
$parts = @('D:\pnpm\bin') + $parts
[Environment]::SetEnvironmentVariable('Path', ($parts -join ';'), 'User')
```

> **Warning**: do not edit PATH with `setx` — it truncates at 1024 chars and
> can destroy a long PATH. Use `[Environment]::SetEnvironmentVariable(...)`;
> filter paths with `-notlike` rather than `-notmatch` (`\L` is an invalid
> regex escape and drops every entry). Open a **new terminal** afterwards.

---

## 5. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `pnpm bin -g` → `ERR_PNPM_GLOBAL_BIN_DIR_NOT_IN_PATH` | Add `D:\pnpm\bin` to PATH and reopen the terminal |
| Tools disappear after `setx PATH` | PATH was truncated; rebuild it with `[Environment]::SetEnvironmentVariable` as shown above |
| PowerShell PATH filter: "unrecognized escape sequence" | Use `-notlike '*\AppData\Local\pnpm*'` |
| docmd says Rust engine not supported | Falls back to the JS engine and builds fine; for the native engine re-enable `@docmd/engine-rust` under `allowBuilds` in `pnpm-workspace.yaml` |
| `make` not found (Windows) | Use `task` (`Taskfile.yml` provides equivalent targets) |
