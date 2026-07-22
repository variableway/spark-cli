# Spark Hub Architecture Decision RFC

**Version**: v1.0
**Date**: 2026-04-02
**Status**: Draft
**Goal**: assess whether a dedicated Hub repository is necessary, deeply analyze the strengths and weaknesses of the OpenCLI Hub protocol, clarify the boundaries and collaboration between `spark-hub`, `opencli`, and `cli-anything`, and produce an actionable architecture decision.

---

## 1. Executive Summary

After an in-depth review of **OpenCLI** (`jackwener/opencli`), **public-clis** (`github.com/public-clis`), **CLI-Anything** (`HKUDS/CLI-Anything`), and the **OpenCLI External CLI Hub** protocol mechanism, this RFC draws the following conclusions:

1. **A dedicated `spark-hub` repository should be created**. Decoupling the Hub capability from `spark-cli` is the only path to long-term architectural health.
2. **`spark-cli` should be the first "native registered member" of `spark-hub`**, not the other way around.
3. **OpenCLI's Hub protocol is a "tightly bound, convenient, but opaque control plane" wrapper**. Reusing it directly saves 30–40% of the engineering work, but at the cost of full control over the registry format, install strategy, and error-handling chain.
4. **Recommended strategy**: `spark-hub` adopts a **"in-house registry protocol + OpenCLI bridge adapter"** hybrid architecture:
   - Core implemented in Go (registry format, installer, passthrough executor).
   - An `opencli-bridge` plugin plugs OpenCLI's 80+ adapters and the External CLI Hub into spark-hub without duplicating work.
5. **CLI-Anything and spark-hub are not competitors.** CLI-Anything is a **CLI generator** (Producer); spark-hub is a **CLI aggregator/router** (Consumer + Registry).

---

## 2. Background

### 2.1 User's underlying need

The user wants to bring the following CLI ecosystems under the Spark brand:

- **OpenCLI**: website/Electron automation (80+ built-in adapters).
- **public-clis**: social-platform CLIs (Twitter/X, Bilibili, Reddit, Telegram).
- **CLI-Anything**: desktop app automation (the `cli-anything-*` family generated for GIMP, Blender, LibreOffice, etc.).

### 2.2 Key architectural questions

| Question | Impact |
|----------|--------|
| Should the Hub live inside spark-cli or in a separate repo? | Determines maintenance boundaries, version coupling, and ecosystem openness. |
| OpenCLI already has an External CLI Hub — do we still need our own? | Determines who owns the control plane, how flexible the protocol is, and how independent the brand is. |
| Can CLI-Anything replace the Hub? | Determines whether the product positioning is being muddled. |

---

## 3. Deep Analysis of the OpenCLI External CLI Hub

### 3.1 How OpenCLI's Hub works

OpenCLI's External CLI Hub is not a publicly documented standalone protocol, but a **"command discovery + auto-install + passthrough exec"** mechanism embedded in the OpenCLI runtime. From the source and documentation, its core behavior is:

#### 3.1.1 Discovery

1. **Built-in whitelist**: OpenCLI maintains a hard-coded list of external CLIs (e.g. `gh`, `obsidian`, `docker`, `lark-cli`, `dingtalk`, `wecom`, `vercel`, etc.).
2. **User registration**: `opencli register mycli` registers any local CLI into OpenCLI's discovery table, so it appears in `opencli list`.
3. **Dynamic scan**: for built-in adapters (`.ts` / `.yaml` files in `src/clis/<site>/`), OpenCLI dynamically scans and loads them at startup.

#### 3.1.2 Execution

When the user types `opencli gh pr list`:

1. OpenCLI parses the command tree, finds that `gh` is not a built-in adapter but is in the External CLI Hub list.
2. It checks whether `gh` is on `PATH`.
3. If yes, it **passthrough-executes** `gh pr list`.
4. If no, it triggers **auto-install** (e.g. on macOS: `brew install gh`), and re-runs on success.

#### 3.1.3 Registration

```bash
opencli register mycli --path /usr/local/bin/mycli
```

- Registration info is stored in OpenCLI's internal data directory (likely `~/.opencli/` or a similar JSON/YAML file).
- Registered CLIs are visible via `opencli list --all`.

#### 3.1.4 Plugin mechanism

- `opencli plugin install github:user/opencli-plugin-my-tool`
- A plugin is essentially an npm/TypeScript package that conforms to the OpenCLI host conventions, loaded via symlink or copy into OpenCLI's `node_modules/`.
- Plugins share the `@jackwener/opencli/registry` runtime with the host.

### 3.2 Strengths of OpenCLI's Hub

| Strength | Detail |
|----------|--------|
| **Zero-config passthrough** | Known CLIs (`gh`, `docker`, etc.) require no wrapper code; args are forwarded as-is. |
| **Auto-install** | If a CLI is missing, the package manager is invoked (`brew install`, `apt install`, etc.) — extremely user-friendly. |
| **80+ built-in adapters** | Huge coverage of website/Electron automation; active community (8k+ stars). |
| **Unified structured output** | Built-in adapters all support `--format json/yaml/md/csv`, easing downstream consumption. |
| **Self-diagnosis** | `opencli doctor` checks browser extensions, daemon state, external CLI availability. |

### 3.3 Weaknesses and risks

| Weakness | Detail | Impact on spark-hub |
|----------|--------|---------------------|
| **Opaque protocol** | The registry format, auto-install policy, and data-directory layout are undocumented. Deep integration requires reading the source or black-box inference. | Internal refactors of OpenCLI could break spark-hub's bridge code. |
| **Strong runtime coupling** | OpenCLI is a Node.js project, and the Hub is embedded in its process. The "Hub protocol" cannot be extracted as a lightweight service or library. | Users must install Node.js + OpenCLI; spark-hub (a Go single-binary) cannot offer a zero-dep path. |
| **Limited control plane** | The registry is OpenCLI's private implementation, and cannot be customized. You cannot change the `opencli list` output format, intercept or rewrite install logic (e.g. from a private mirror), or pin multiple versions of the same CLI. | Hard to extend in enterprise scenarios with private registries or mirror sources. |
| **Naming collisions** | OpenCLI's built-in adapters and External CLIs share the same namespace (`opencli <name>`). If OpenCLI ships a future built-in called `spark`, the meaning of `opencli spark` would shift. | Once registered, spark-cli is at risk of being shadowed by future OpenCLI versions. |
| **Uncontrollable error path** | On passthrough, external exit codes, stderr, and progress bars are returned verbatim. OpenCLI offers no unified timeout or no-input policy. | CI automation can hang waiting on external prompts. |
| **Inconsistent install across platforms** | Auto-install depends on a hard-coded mapping (macOS→brew, Linux→apt, etc.), and behavior on Windows or Chinese Linux distros can be unpredictable. | The default strategy is not always optimal for Chinese developers. |

### 3.4 Key conclusion: OpenCLI Hub is best treated as a "bridged ecosystem", not the Hub core

OpenCLI Hub's biggest value is that it **already connects a large CLI/website-adapter ecosystem**. spark-hub should not try to replace it; instead:

- Treat OpenCLI as a powerful **"sub-ecosystem"** to plug into.
- Own the routing layer, the registry format, and the install strategy.

---

## 4. CLI-Anything's Positioning

### 4.1 What CLI-Anything is

CLI-Anything (`HKUDS/CLI-Anything`) is a **CLI generator framework**:

1. Input: the source or binary of any desktop software (GIMP, Blender, LibreOffice, Zoom, etc.).
2. Process: a 7-stage pipeline (analyze → design → implement → test plan → test code → docs → release) that auto-generates a Python CLI.
3. Output: `cli-anything-<software>` (e.g. `cli-anything-gimp`), with built-in `SKILL.md`, JSON output, REPL mode.

### 4.2 Relationship between CLI-Anything and spark-hub

| Dimension | CLI-Anything | spark-hub |
|-----------|--------------|-----------|
| **Core action** | Produce CLIs | Discover, register, route, execute CLIs |
| **Output** | `cli-anything-*` Python package | Go single-binary executable |
| **Relationship with OpenCLI** | The generated CLIs can register with OpenCLI Hub | Can bridge OpenCLI; can also directly discover `cli-anything-*` |
| **Does it replace the Hub?** | **No**. It's just one important content source in the Hub ecosystem. | **Yes**. It's the consumer and scheduler. |

**Analogy**:
- CLI-Anything = **the factory** (makes tools)
- OpenCLI = **a large chain store** (own brand + resells other brands)
- spark-hub = **an independent shopping platform / router** (can stock the chain store's goods, can also stock the factory's goods, and own the UI and logistics)

---

## 5. Comparison of Three Architectural Approaches

### Option A: Hub embedded in spark-cli (Monolith)

- `spark-cli` gains `spark hub`, `spark web`, `spark social`, `spark app` subcommands.
- **Pros**: users only download one binary.
- **Cons**:
  - spark-cli expands from a "Git tool" to a "universal toolbox".
  - Every Hub change triggers a spark-cli release; semver becomes muddled.
  - Non-Git users can't use the Hub standalone.
- **Verdict**: **not recommended**.

### Option B: Fully reuse OpenCLI Hub (Thin wrapper)

- Standalone `spark-hub` repo, but with little to no logic — a thin wrapper around `opencli`.
- **Pros**: minimum development effort; fastest go-live.
- **Cons**:
  - Fully tied to OpenCLI's protocol and release cadence.
  - No way to customize the registry format, install strategy, or enterprise mirror.
  - Weak brand presence — users may see it as "opencli in disguise".
- **Verdict**: **not recommended as a long-term solution**, but acceptable as an MVP for fast validation.

### Option C: Standalone spark-hub + in-house protocol + OpenCLI/CLI-Anything bridge (**strongly recommended**)

- Standalone `spark-hub` repo, Go (consistent with spark-cli).
- Define the **Spark Registry Protocol (SRP)**: a JSON/YAML CLI registry format.
- Core modules:
  - **Registry Manager**: read local and remote registries (configurable).
  - **Installer**: multi-backend (brew, apt, winget, npm, pip, curl, enterprise mirror).
  - **Executor**: safe subprocess exec (timeout, stdin isolation, exit-code passthrough).
  - **Bridge Adapters**:
    - `opencli-bridge`: map OpenCLI's built-in adapters + External CLI Hub into SRP.
    - `anything-bridge`: scan PATH for `cli-anything-*` and auto-register.
    - `social-bridge`: maintain the public-clis mapping manually.
- **Pros**:
  - Full control over the registry format and routing strategy.
  - Plug into multiple heterogeneous ecosystems (OpenCLI, CLI-Anything, public-clis, and more in the future).
  - spark-cli is just a normal registered member — clean relationship.
  - Supports enterprise private deployment (custom registry URL, mirror sources).
- **Cons**:
  - ~40% more initial development than Option B.
  - Have to maintain bridge adapters (usually stable passthrough).
- **Verdict**: **recommended**.

---

## 6. Recommended Architecture

### 6.1 Repository layout

```
github.com/yourname/spark-hub
├── cmd/
│   ├── root.go
│   ├── list.go          # hub list
│   ├── doctor.go        # hub doctor
│   ├── run.go           # hub run <cli> -- <args>
│   ├── install.go       # hub install <cli>
│   ├── register.go      # hub register <path>
│   └── registry.go      # hub registry manage
├── internal/
│   ├── registry/        # Spark Registry Protocol core
│   │   ├── model.go     # Registry data structures
│   │   ├── loader.go    # Local/remote registry loader
│   │   └── merger.go    # Multi-source registry merge
│   ├── installer/       # Installer abstraction & implementations
│   │   ├── manager.go
│   │   ├── brew.go
│   │   ├── apt.go
│   │   ├── winget.go
│   │   ├── npm.go
│   │   ├── pip.go
│   │   └── script.go    # Custom install script
│   ├── executor/        # Safe executor
│   │   ├── runner.go
│   │   └── sanitize.go
│   └── bridge/          # Heterogeneous ecosystem bridges
│       ├── opencli/     # OpenCLI bridge
│       ├── anything/    # CLI-Anything bridge
│       └── social/      # public-clis bridge
├── pkg/
│   └── srp/             # Public Spark Registry Protocol spec
│       └── v1/
│           ├── types.go
│           └── schema.json
├── registry/
│   └── default.yaml     # Default built-in registry (incl. spark-cli, opencli, etc.)
└── docs/
    ├── architecture.md
    └── srp-v1.md
```

### 6.2 Spark Registry Protocol (SRP) v1 draft

```yaml
# registry.yaml
apiVersion: spark.io/srp/v1
kind: Registry
metadata:
  name: default
spec:
  sources:
    - name: opencli
      type: opencli-bridge
      enabled: true
    - name: anything
      type: anything-bridge
      enabled: true
      config:
        auto_discover: true
        prefix: "cli-anything-"
    - name: social
      type: static
      enabled: true

  clis:
    - name: spark
      displayName: "Spark CLI"
      category: git
      description: "Manage multiple git repositories"
      binary: spark
      homepage: https://github.com/yourname/spark-cli
      install:
        strategy: go-install
        command: "go install github.com/yourname/spark-cli@latest"

    - name: opencli
      displayName: "OpenCLI"
      category: web
      description: "Universal CLI Hub for websites and Electron apps"
      binary: opencli
      install:
        strategy: npm
        command: "npm install -g @jackwener/opencli"

    - name: twitter
      displayName: "Twitter CLI"
      category: social
      binary: twitter-cli
      install:
        strategy: pip
        command: "pip install twitter-cli"
      # This CLI should be handled by the social bridge
      bridge: social

    - name: gimp
      displayName: "CLI-Anything GIMP"
      category: app
      binary: cli-anything-gimp
      install:
        strategy: pip
        command: "pip install cli-anything-gimp"
      bridge: anything
```

### 6.3 Command design

```bash
# List all known CLIs (merged from local registry + bridge discovery)
spark-hub list

# Diagnose dependencies
spark-hub doctor

# Install a CLI (via the strategy declared in the registry)
spark-hub install opencli
spark-hub install twitter
spark-hub install gimp

# Generic passthrough
spark-hub run opencli -- bilibili hot -f json
spark-hub run twitter -- feed --limit 20
spark-hub run gimp -- --json project new

# Register a local custom CLI
spark-hub register ./my-custom-cli --name mycli

# Manage registry sources
spark-hub registry add https://mycompany.com/spark-registry.yaml
spark-hub registry list
```

### 6.4 Changes to spark-cli

spark-cli only needs an extremely thin forwarding command:

```go
// spark-cli/cmd/hub.go
var hubCmd = &cobra.Command{
    Use:   "hub",
    Short: "Delegate to spark-hub for CLI management",
    RunE: func(cmd *cobra.Command, args []string) error {
        c := exec.Command("spark-hub", args...)
        c.Stdin = os.Stdin
        c.Stdout = os.Stdout
        c.Stderr = os.Stderr
        return c.Run()
    },
}
```

So `spark hub` becomes equivalent to `spark-hub` — the user experience is seamless, but the architecture boundary is clean.

---

## 7. OpenCLI Bridge Adapter — Design Notes

### 7.1 Responsibilities of `bridge/opencli`

The bridge does **not** try to understand OpenCLI's internal data formats. It treats OpenCLI as a black-box but powerful CLI pool, and integrates via:

1. **Discovery**
   - Call `opencli list -f json` to get every available command (built-in adapters and external CLIs).
   - Convert the result to a list of SRP `CLIEntry`, marked `source: opencli`.

2. **Execution**
   - When the user runs `spark-hub run opencli -- bilibili hot -f json`, the Executor forwards as `opencli bilibili hot -f json`.
   - When the user runs `spark-hub run gh -- pr list` (and `gh` is in OpenCLI's External CLI Hub), the Executor forwards as `opencli gh pr list`.

3. **Installation**
   - For OpenCLI itself: declared in the SRP registry as `npm install -g @jackwener/opencli`.
   - For OpenCLI's built-in externals (e.g. `gh`, `docker`): **delegate to OpenCLI's auto-install** — spark-hub can run `opencli gh --version` to let OpenCLI trigger `brew install gh` itself.
   - Optionally handle installs at the spark-hub layer to bypass OpenCLI's auto-install.

### 7.2 Boundary conventions

| Scenario | Handling |
|----------|----------|
| `opencli` not installed | `spark-hub doctor` prompts to install Node.js + OpenCLI; `spark-hub install opencli` runs the npm install |
| OpenCLI command collides with an SRP command | SRP's explicit `clis` entries win (explicit > bridge). For example, if SRP also defines a `twitter` entry, it is preferred over the OpenCLI bridge's discovery. |
| OpenCLI returns a non-zero exit code | Passed through to the spark-hub user verbatim. |
| OpenCLI output format | Passthrough; if downstream tooling needs JSON, the user explicitly passes `-f json`. |

---

## 8. Risk Assessment and Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| OpenCLI internal protocol changes break the bridge | Medium | Medium | The bridge only depends on `opencli list -f json` and command passthrough — two stable interfaces. |
| `spark-hub` initial dev cycle is long, delaying release | Medium | High | Phase 1 delivers the minimum viable version (list + run + opencli bridge); other bridges and installers iterate later. |
| Users confuse the relationship between `spark-cli` and `spark-hub` | High | Low | Docs clearly separate concerns: spark-cli does Git, spark-hub does CLI management; `spark hub` is just a shortcut. |
| public-clis has inconsistent interfaces, increasing mapping cost | Medium | Medium | `social-bridge` stays minimal: `spark-hub run twitter -- feed` becomes `twitter-cli feed`, no flag renaming. |
| CLI-Anything generated command name collisions | Low | Medium | Commands discovered by the `anything-bridge` are registered with an `anything-` prefix (e.g. `anything-gimp`) and invoked via `spark-hub run anything-gimp`. |

---

## 9. Implementation Roadmap

### Phase 1: spark-hub skeleton + OpenCLI bridge (MVP, 2–3 weeks)

- Create the `spark-hub` repo with the Go + Cobra scaffold.
- Define the SRP v1 base data structures (YAML parsing).
- Implement `spark-hub list`, `spark-hub run`, `spark-hub doctor`.
- Implement `bridge/opencli`: call `opencli list -f json` and map to SRP entries.
- Register `spark-cli` and `opencli` in the default registry.
- **Acceptance**: after installing OpenCLI, `spark-hub list` shows OpenCLI's commands; `spark-hub run opencli -- hackernews top` produces the expected output.

### Phase 2: Installer + CLI-Anything bridge (2 weeks)

- Implement the Installer Manager with npm/pip strategies.
- Implement `spark-hub install <cli>`.
- Implement `bridge/anything`: scan for `cli-anything-*` prefixes.
- **Acceptance**: `spark-hub install opencli` automatically runs npm install; after installing `cli-anything-gimp`, `spark-hub list` discovers it.

### Phase 3: public-clis bridge + spark-cli thin wrapper (1–2 weeks)

- Implement `bridge/social`: statically register `twitter-cli`, `bilibili-cli`, `rdt-cli`, `tg-cli`.
- Add a `spark hub` forwarding command in `spark-cli`.
- Write BDD tests and docs.
- **Acceptance**: `spark social twitter feed` (via `spark hub run social.twitter -- feed`) correctly calls `twitter-cli feed`.

### Phase 4: enterprise features & ecosystem expansion (ongoing)

- Support remote registry URLs (`spark-hub registry add`).
- Support custom install mirror sources.

---

## 10. Decision Summary

| Question | Decision |
|----------|----------|
| Should we create a standalone `spark-hub` repository? | **Yes**. Cleaner architecture, more open ecosystem. |
| Where does `spark-cli` live? | As a normal member in the `spark-hub` registry; `spark-cli` only keeps a `spark hub` forwarding command. |
| Should we fully reuse OpenCLI Hub? | **No**. OpenCLI Hub is an opaque protocol with insufficient control. Use "in-house Hub + OpenCLI bridge" hybrid. |
| Relationship between CLI-Anything and Hub? | CLI-Anything is the **content producer** (generates CLIs); spark-hub is the **content aggregator** (discovers, installs, runs). They complement each other. |
| How big should the first MVP be? | Only `list` + `run` + `doctor` + `opencli-bridge`; ship v0.1.0 within 2–3 weeks. |

---

## 11. Appendix: References

- OpenCLI: https://github.com/jackwener/opencli
- public-clis: https://github.com/public-clis
- CLI-Anything: https://github.com/HKUDS/CLI-Anything
- spark-cli (this project): `/Users/patrick/innate/spark-cli`

---

*End of document*
