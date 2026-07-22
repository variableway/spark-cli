# Spark CLI External CLI Integration Research Report

**Version**: v2.0
**Date**: 2026-04-02
**Goal**: assess the feasibility of integrating OpenCLI, public-clis, and CLI-Anything into Spark CLI and produce a detailed implementation plan.

---

## 1. Executive Summary

This report surveys three tools/ecosystems: **OpenCLI** (`jackwener/opencli`), **public-clis** (the `twitter-cli`, `bilibili-cli`, `rdt-cli`, `tg-cli` repos under the `github.com/public-clis` org), and **CLI-Anything** (`HKUDS/CLI-Anything`), looking at their technical characteristics, distribution model, and invocation interface.

Given Spark CLI's current **Go + Cobra + Viper** single-binary architecture, the recommended integration pattern is a **"unified Hub + layered Adapters"** model:

- Add `spark hub` as the single entry point for managing all external CLIs (detection, install hints, generic passthrough).
- Promote the highest-value, most stable commands to first-class Spark subcommands:
  - `spark web`    → OpenCLI (website / Electron automation)
  - `spark social` → public-clis (Twitter/X, Bilibili, Reddit, Telegram, etc.)
  - `spark app`    → CLI-Anything (desktop app automation: Blender, GIMP, LibreOffice, etc.)
- Do not pull external runtime dependencies into the core binary — integration is **opt-in**.

The approach is **highly feasible** on all three axes (technical, maintenance, extensibility). Estimated end-to-end delivery: **5–6 weeks**.

---

## 2. Survey of External CLI Ecosystems

### 2.1 OpenCLI

| Field | Detail |
|-------|--------|
| **Repository** | `github.com/jackwener/opencli` |
| **Tech** | TypeScript / Node.js 20+ |
| **Install** | `npm install -g @jackwener/opencli` |
| **Typical call** | `opencli <adapter> <command> [flags]` |
| **Output formats** | `table` (default), `json`, `yaml`, `md`, `csv` (`-f/--format`) |
| **Highlights** | 80+ built-in website adapters; Electron CDP control; ships with an **External CLI Hub** for registering/passing through other CLIs; structured, pipeable output |
| **Runtime deps** | Node.js + Chrome browser extension (for some commands) |

**Integration notes**:
- Trivial to call via `os/exec`.
- Since OpenCLI is itself a hub, Spark can either pass through or wrap the high-frequency commands — the latter is recommended to reduce user-facing cognitive load.
- Detect `node` / `npm` / `opencli` on `PATH`.

### 2.2 public-clis

| Field | Detail |
|-------|--------|
| **Org** | `github.com/public-clis` |
| **Flagship repos** | `twitter-cli` (2.1k⭐), `bilibili-cli` (601⭐), `rdt-cli` (306⭐), `tg-cli` (214⭐) |
| **Tech** | Python |
| **Install** | Per project — usually `pip` or source build (see each repo's README) |
| **Typical call** | `twitter-cli feed`, `bilibili-cli search <keyword>`, `rdt-cli hot`, `tg-cli sync` |
| **Output formats** | Text / JSON (varies by CLI) |
| **Highlights** | Highly customized per-platform CLIs; built for terminal browsing, search, export; active community |
| **Runtime deps** | Python 3.x |

**Integration notes**:
- Each CLI is its own binary/entry point — needs separate detection.
- They are few in number and share common verbs (`feed`, `search`, `hot`, `sync`), so a single `social` subcommand with second-level platform args is a good fit — e.g. `spark social twitter feed`, `spark social bilibili search golang`.
- OpenCLI's External CLI Hub can be used for auto-discovery, but wrapping directly provides a more consistent Spark UX.

### 2.3 CLI-Anything

| Field | Detail |
|-------|--------|
| **Repository** | `github.com/HKUDS/CLI-Anything` |
| **Tech** | Python 3.10+ |
| **Install** | `git clone`, then drive via Claude Code / OpenCode / Codex plugin; the generated CLIs are installed with `pip install -e .` |
| **Typical call** | `cli-anything-gimp --json project new`, `cli-anything-blender --help` |
| **Output formats** | Human-readable text + `--json` structured output |
| **Highlights** | A **CLI generator**: a 7-stage pipeline (analyze → design → implement → test plan → test code → docs → release) that turns desktop software (GIMP, Blender, LibreOffice, Zoom, OBS, etc.) into a CLI; ships with a **CLI-Hub** registry for auto-discovery; every generated CLI ships with a `SKILL.md` |
| **Runtime deps** | Python 3.10+; the controlled desktop software itself must be installed |

**Integration notes**:
- CLI-Anything is **not a directly used CLI**, but a **generator**; what actually gets integrated is the `cli-anything-*` family it produces.
- These commands share a consistent naming pattern (`cli-anything-<software>`) and argument style (`--json`, subcommand groups, REPL mode).
- Two integration strategies are possible:
  1. **Dynamic discovery** — scan `PATH` for `cli-anything-*` executables and register them under `spark app`.
  2. **Static configuration** — explicitly list commonly used `cli-anything-*` commands in `~/.spark.yaml`.
- Recommendation: combine (1) dynamic discovery with (2) whitelist filtering for control.

---

## 3. Spark CLI Status and Integration Constraints

| Constraint | Detail |
|------------|--------|
| **Tech stack** | Go 1.24+, Cobra, Viper |
| **Distribution** | Single-binary executable, cross-platform (Windows/Linux/macOS) |
| **Existing modules** | `git`, `task` |
| **Testing** | Ginkgo + Gomega (BDD style) |
| **Config** | `~/.spark.yaml` (Viper auto-read) |
| **Core constraint** | Integration must remain **opt-in** — never require Node.js or Python for users who only use the core features. |

---

## 4. Integration Approach Comparison

| Axis | A: Direct passthrough proxy | B: Adapter wrapper | C: Hybrid Hub + Adapter (**recommended**) |
|------|------------------------------|---------------------|-------------------------------------------|
| **Code volume** | Smallest | Medium | Medium |
| **UX consistency** | Low (users still learn external syntax) | High | High (common commands unified; complex commands fall through) |
| **Maintenance** | Low | High (args must be kept in sync) | Medium (core commands stable, passthrough as fallback) |
| **Extensibility** | Low (every new CLI needs a new subcommand) | Medium | High (the hub can register any adapter) |
| **Risk** | External changes don't propagate | Interface changes can break things | Core wrappers stable; complex paths fall through |

### Why C is recommended

1. **Unified entry**: `spark hub` owns the lifecycle (detection, diagnostics, passthrough) for every external CLI.
2. **Common shortcuts**: the most-used capabilities become first-class subcommands, lowering the cognitive load.
3. **Core stays clean**: external deps live in `internal/hub` and never bleed into `git`, `task`, etc.
4. **Progressive enhancement**: users who don't install external CLIs still get a fully functional Spark core.

---

## 5. Recommended Architecture

### 5.1 Directory Layout

```
spark/
├── cmd/
│   ├── hub.go              # spark hub root
│   ├── web.go              # spark web (OpenCLI adapter)
│   ├── social.go           # spark social (public-clis adapter)
│   └── app.go              # spark app (CLI-Anything adapter)
├── internal/
│   └── hub/
│       ├── manager.go      # HubManager / Adapter interface & registry
│       ├── runner.go       # Subprocess exec, safe escaping, output capture
│       ├── config.go       # hub.* config reader (~/.spark.yaml)
│       ├── opencli.go      # OpenCLIAdapter
│       ├── social.go       # SocialCLIAdapter (twitter-cli, bilibili-cli, …)
│       ├── anything.go     # CLIAnythingAdapter (dynamic discovery of cli-anything-*)
│       └── discover.go     # PATH scan & dynamic registration helpers
└── docs/
    └── usage/
        ├── hub.md
        ├── web.md
        ├── social.md
        └── app.md
```

### 5.2 Adapter Interface

```go
package hub

type Adapter interface {
    // Metadata
    Name() string
    DisplayName() string

    // Dependency check
    Check(ctx context.Context) error

    // Install hint
    InstallGuide() string

    // List subcommands/subtools available under this adapter
    ListTools() []ToolInfo

    // Map Spark args to external CLI args
    BuildArgs(tool string, sparkArgs []string, flags map[string]string) ([]string, error)

    // Pre-exec environment prep
    Environ() []string
}

type ToolInfo struct {
    Name        string
    DisplayName string
    Installed   bool
}
```

### 5.3 Config Schema

Add a `hub` node to `~/.spark.yaml`:

```yaml
hub:
  opencli:
    path: "opencli"            # Custom binary path
    default_format: "json"

  social:
    # Override path per platform
    twitter:
      path: "twitter-cli"
    bilibili:
      path: "bilibili-cli"
    reddit:
      path: "rdt-cli"
    telegram:
      path: "tg-cli"

  anything:
    # Dynamic discovery: scan PATH for cli-anything-* executables
    auto_discover: true
    # Whitelist: only register these (empty = no filter)
    whitelist: []
    # Blacklist: ignore these
    blacklist: []
```

---

## 6. Command Mapping & UX

### 6.1 Hub management commands

```bash
# List all registered external CLI adapters and their availability
spark hub list

# Diagnose all external CLI dependencies
spark hub doctor

# Generic passthrough: after "--" args go to the external CLI verbatim
spark hub run opencli -- bilibili hot -f json
spark hub run social.twitter -- feed --limit 20
spark hub run anything.gimp -- --json project new
```

### 6.2 Web shortcut (spark web)

```bash
# Maps to opencli list
spark web list

# Maps to opencli <adapter> <command>
spark web bilibili hot -f json
spark web zhihu hot --limit 10
spark web hackernews top

# Electron app control
spark web cursor status
spark web cursor open ./my-project
```

### 6.3 Social shortcut (spark social)

```bash
# List installed social CLIs
spark social list

# Twitter/X
spark social twitter feed
spark social twitter bookmarks

# Bilibili
spark social bilibili hot
spark social bilibili search "Golang tutorial"

# Reddit
spark social reddit hot
spark social reddit search rust

# Telegram
spark social telegram sync
spark social telegram search "project name"
```

### 6.4 Desktop app shortcut (spark app)

```bash
# List installed cli-anything-* commands
spark app list

# Call a specific cli-anything command
spark app gimp --json project new --width 1920 --height 1080
spark app blender render --file ./scene.blend -o ./output.png
spark app libreoffice convert --input ./doc.docx --output ./doc.pdf

# Enter REPL (if supported)
spark app gimp --repl
```

---

## 7. Feasibility Analysis

### 7.1 Technical feasibility ⭐⭐⭐⭐⭐ (high)

- **Subprocess invocation**: Go's standard `os/exec` is enough. `internal/git` already uses `exec.Command` heavily, so there is prior art.
- **Argument safety**: pass via `cmd.Args` (no shell string concatenation) — command injection is impossible by construction.
- **Config extension**: Viper supports nested keys (`hub.opencli.path`) with no changes to the existing config loader.
- **Dynamic discovery**: scanning `PATH` for `cli-anything-*` is just `exec.LookPath` and directory traversal.

### 7.2 Maintenance cost ⭐⭐⭐ (medium)

- The biggest risk is **external CLI version drift** — OpenCLI adding/deprecating flags, or any public-clis changing flag names.
- **Mitigation**:
  1. Only wrap the stable, high-frequency flags (`--format`, `--limit`, `--file`).
  2. Always provide a passthrough: `spark hub run <adapter> -- <raw args>`.
  3. Keep the per-CLI arg mapping under `spark social` minimal.

### 7.3 Cross-platform compatibility ⭐⭐⭐⭐⭐ (high)

- **OpenCLI**: cross-platform Node.js; Spark only needs to detect `node` / `npm` / `opencli`.
- **public-clis**: cross-platform Python; Spark only needs to detect `python` / `pip` and each CLI.
- **CLI-Anything**: both generator and outputs are Python — cross-platform by default.
- The only Windows note is the executable name (`python.exe` / `node.exe`); `exec.LookPath` handles it.

### 7.4 Security & privacy ⭐⭐⭐⭐ (low)

- **Sensitive config**: some social CLIs need API tokens (e.g. Twitter). Default to `~/.spark.yaml` or env vars; suggest `chmod 600 ~/.spark.yaml`.
- **Command injection**: `exec.Command(name, args...)` removes the risk entirely.
- **`PATH` scan safety**: dynamic discovery only matches file names — no unknown scripts are executed.

---

## 8. Implementation Plan

### Phase 1: Hub infrastructure (week 1–2)

- Create the `internal/hub` package, defining the `Adapter` interface, `Runner`, and `Config`.
- Implement `spark hub list` and `spark hub doctor`.
- Build common dependency detection (PATH lookup, version parsing).
- Wire the config schema (`hub.*` in `~/.spark.yaml`).
- **Acceptance**: `spark hub list` correctly shows three Adapters with available/missing state; `spark hub doctor` provides clear install hints.

### Phase 2: OpenCLI integration (week 2–3)

- Implement `OpenCLIAdapter`.
- Implement `spark web list`.
- Implement dynamic passthrough for `spark web <adapter> <command>` via Cobra's `Args` mechanism.
- Auto-append `--format json` for downstream processing when the user didn't pick one.
- **Acceptance**: `spark web bilibili hot -f json` matches `opencli bilibili hot -f json`; a friendly hint appears when opencli is missing.

### Phase 3: public-clis integration (week 3–4)

- Implement `SocialCLIAdapter` covering `twitter-cli`, `bilibili-cli`, `rdt-cli`, `tg-cli`.
- Implement `spark social list`.
- Implement dynamic subcommands `spark social <platform> <command>`.
- **Acceptance**: `spark social twitter feed` correctly calls `twitter-cli feed`; `spark social bilibili search golang` works.

### Phase 4: CLI-Anything integration (week 4–5)

- Implement `CLIAnythingAdapter`.
- Implement `PATH` dynamic discovery for `cli-anything-*` executables.
- Implement `spark app list`.
- Implement `spark app <software> [args...]` dynamic subcommand.
- **Acceptance**: after installing `cli-anything-gimp`, `spark app list` shows `gimp`; `spark app gimp --json project new` succeeds.

### Phase 5: Docs, tests, release (week 5–6)

- Write BDD tests for `internal/hub` (using a mock runner or test subprocesses).
- Update `docs/usage/hub.md`, `docs/usage/web.md`, `docs/usage/social.md`, `docs/usage/app.md`.
- Update `README.md`.
- Run `make lint` and `make test`.
- **Acceptance**: every new feature is documented; CI is green; release tag published.

---

## 9. Detailed Task Breakdown

### Task 1: scaffold the `internal/hub` package
- **Goal**: establish the directory layout and core interfaces.
- **Input**: existing `internal/` conventions.
- **Output**:
  - `internal/hub/adapter.go` (interface)
  - `internal/hub/manager.go` (registry)
  - `internal/hub/runner.go` (safe subprocess exec)
- **Acceptance**: the package compiles; `Runner` correctly captures stdout/stderr/exit code.
- **Priority**: P0
- **Effort**: 2 days

### Task 2: Hub config and Viper binding
- **Goal**: support `hub.*` in `~/.spark.yaml`.
- **Input**: `internal/config` existing logic.
- **Output**: `internal/hub/config.go` and supporting structs.
- **Acceptance**: Viper reads `hub.opencli.path`, `hub.social.twitter.path`, `hub.anything.auto_discover`.
- **Priority**: P0
- **Effort**: 1 day

### Task 3: `spark hub list` command
- **Goal**: list every adapter (name, display name, availability, subtools).
- **Input**: Hub Manager + per-adapter `Check()` / `ListTools()`.
- **Output**: `cmd/hub.go` `hub list` subcommand.
- **Acceptance**: terminal table output is correct; missing deps show `not installed`.
- **Priority**: P0
- **Effort**: 1 day

### Task 4: `spark hub doctor` command
- **Goal**: diagnose external CLI dependencies.
- **Input**: per-adapter `Check()` and `InstallGuide()`.
- **Output**: `cmd/hub.go` `hub doctor` subcommand.
- **Acceptance**: distinguishes "Node.js missing" / "opencli missing" / "twitter-cli missing" and provides install commands.
- **Priority**: P0
- **Effort**: 1 day

### Task 5: `spark hub run <adapter> -- <args>` generic passthrough
- **Goal**: raw command passthrough for every adapter.
- **Input**: Hub Runner.
- **Output**: `cmd/hub.go` `hub run` subcommand.
- **Acceptance**:
  - `spark hub run opencli -- bilibili hot -f json` matches `opencli bilibili hot -f json`.
  - `spark hub run social.twitter -- feed` matches `twitter-cli feed`.
  - `spark hub run anything.gimp -- --json project new` matches `cli-anything-gimp --json project new`.
- **Priority**: P0
- **Effort**: 1 day

### Task 6: OpenCLI Adapter
- **Goal**: wrap `opencli` invocations.
- **Input**: OpenCLI documentation and argument conventions.
- **Output**: `internal/hub/opencli.go`.
- **Acceptance**: `BuildArgs` translates `spark web` args to `opencli` args; auto-append `--format json` when needed.
- **Priority**: P1
- **Effort**: 2 days

### Task 7: `spark web list`
- **Goal**: list all OpenCLI-supported adapters.
- **Input**: `OpenCLIAdapter`.
- **Output**: `cmd/web.go` `web list` subcommand.
- **Acceptance**: output matches `opencli list`.
- **Priority**: P1
- **Effort**: 1 day

### Task 8: `spark web <adapter> <command>` dynamic subcommand
- **Goal**: call any OpenCLI adapter via `spark web`.
- **Input**: Cobra `Args` handling.
- **Output**: `cmd/web.go` main `RunE` logic.
- **Acceptance**: `spark web bilibili hot -f json` works; unknown args pass through.
- **Priority**: P1
- **Effort**: 1.5 days

### Task 9: SocialCLI Adapter
- **Goal**: wrap the four public-clis Python tools.
- **Input**: `twitter-cli`, `bilibili-cli`, `rdt-cli`, `tg-cli` docs.
- **Output**: `internal/hub/social.go`.
- **Acceptance**: detects each CLI independently; `BuildArgs` correctly maps `spark social <platform> <cmd>`.
- **Priority**: P1
- **Effort**: 2 days

### Task 10: `spark social list`
- **Goal**: list installed social CLIs.
- **Input**: `SocialCLIAdapter`.
- **Output**: `cmd/social.go` `social list` subcommand.
- **Acceptance**: tabular output with platform, CLI name, install state.
- **Priority**: P1
- **Effort**: 1 day

### Task 11: `spark social <platform> <command>` dynamic subcommand
- **Goal**: support calls like `spark social twitter feed` and `spark social bilibili search golang`.
- **Input**: `SocialCLIAdapter`, Cobra `Args`.
- **Output**: `cmd/social.go` main `RunE` logic.
- **Acceptance**: all four platforms support passthrough; missing deps get a clear hint.
- **Priority**: P1
- **Effort**: 1.5 days

### Task 12: CLI-Anything Adapter
- **Goal**: wrap the generated `cli-anything-*` family.
- **Input**: CLI-Anything docs, CLI-Hub registry format.
- **Output**: `internal/hub/anything.go`.
- **Acceptance**:
  - `auto_discover: true` scans PATH and lists every `cli-anything-*`.
  - `whitelist` / `blacklist` filtering works.
- **Priority**: P1
- **Effort**: 2 days

### Task 13: `PATH` dynamic discovery
- **Goal**: safely scan PATH and find `cli-anything-*` executables.
- **Input**: `os.Getenv("PATH")` + platform path-separator rules.
- **Output**: `internal/hub/discover.go`.
- **Acceptance**: works on Windows / Linux / macOS; skips non-executables; never executes unknown scripts.
- **Priority**: P1
- **Effort**: 1 day

### Task 14: `spark app list`
- **Goal**: list installed `cli-anything-*` software.
- **Input**: `CLIAnythingAdapter`, Discover logic.
- **Output**: `cmd/app.go` `app list` subcommand.
- **Acceptance**: with `cli-anything-gimp` and `cli-anything-blender` installed, `spark app list` lists both.
- **Priority**: P1
- **Effort**: 1 day

### Task 15: `spark app <software> [args...]` dynamic subcommand
- **Goal**: invoke any generated CLI.
- **Input**: `CLIAnythingAdapter`, Cobra `Args`.
- **Output**: `cmd/app.go` main `RunE` logic.
- **Acceptance**: `spark app gimp --json project new` matches `cli-anything-gimp --json project new`; native flags like `--repl` pass through.
- **Priority**: P1
- **Effort**: 1.5 days

### Task 16: BDD tests for the Hub module
- **Goal**: Ginkgo/Gomega tests for `internal/hub`.
- **Input**: existing test style in `internal/config/config_test.go`, `internal/git/finder_test.go`.
- **Output**: `internal/hub/hub_test.go` plus per-adapter unit tests.
- **Acceptance**: > 60% coverage; mock runner avoids hard deps on external binaries.
- **Priority**: P1
- **Effort**: 2 days

### Task 17: integration & end-to-end verification
- **Goal**: validate the three Adapters in a real environment.
- **Input**: a test box with opencli, twitter-cli, cli-anything-gimp (optional).
- **Output**: a test report and follow-up fix PRs.
- **Acceptance**:
  - `spark web list` succeeds on a box with opencli.
  - `spark social twitter --help` passes through.
  - `spark app list` discovers installed `cli-anything-*` commands.
- **Priority**: P1
- **Effort**: 2 days

### Task 18: usage docs
- **Goal**: usage docs for `hub`, `web`, `social`, `app`.
- **Input**: existing `docs/usage/*.md` template.
- **Output**:
  - `docs/usage/hub.md`
  - `docs/usage/web.md`
  - `docs/usage/social.md`
  - `docs/usage/app.md`
- **Acceptance**: docs include prerequisites, config example, common commands, troubleshooting.
- **Priority**: P2
- **Effort**: 2 days

### Task 19: update README
- **Goal**: keep the root README in sync.
- **Input**: the new feature list.
- **Output**: an updated `README.md`.
- **Acceptance**: the README has an "External CLI Hub" section.
- **Priority**: P2
- **Effort**: 0.5 days

### Task 20: lint, build, and CI
- **Goal**: ensure the project follows conventions; CI green.
- **Input**: Makefile, GitHub Actions (if any).
- **Output**: clean build artifacts.
- **Acceptance**: `make lint` and `make test` pass.
- **Priority**: P0
- **Effort**: 0.5 days

---

## 10. Appendix

### 10.1 Example `~/.spark.yaml`

```yaml
# Core Spark config
repo-path:
  - ~/workspace

git:
  username: your-name
  email: your@email.com

# External CLI Hub config
hub:
  opencli:
    path: "opencli"
    default_format: "json"

  social:
    twitter:
      path: "twitter-cli"
    bilibili:
      path: "bilibili-cli"
    reddit:
      path: "rdt-cli"
    telegram:
      path: "tg-cli"

  anything:
    auto_discover: true
    whitelist: []
    blacklist: []
```

### 10.2 Install-check pseudocode

```go
func (a *OpenCLIAdapter) Check(ctx context.Context) error {
    if _, err := exec.LookPath("node"); err != nil {
        return fmt.Errorf("Node.js is not installed")
    }
    if _, err := exec.LookPath(a.Path()); err != nil {
        return fmt.Errorf("opencli is not installed. Run: npm install -g @jackwener/opencli")
    }
    return nil
}

func (a *SocialCLIAdapter) Check(ctx context.Context) error {
    for _, tool := range a.Tools {
        exec.LookPath(tool.Path)
    }
    return nil
}

func (a *CLIAnythingAdapter) Check(ctx context.Context) error {
    if _, err := exec.LookPath("python"); err != nil {
        return fmt.Errorf("Python is not installed")
    }
    return nil
}
```

### 10.3 Security note on CLI-Anything dynamic discovery

`spark app list` discovers tools by scanning `PATH` for executables whose names start with `cli-anything-`. **No discovered file is executed**; the match is purely by file name. Real invocations always use `exec.Command(name, args...)` to avoid command injection.

---

*End of report*
