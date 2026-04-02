# Spark CLI 外部 CLI 集成调研报告

**版本**: v2.0  
**日期**: 2026-04-02  
**目标**: 评估将 OpenCLI、public-clis、CLI-Anything 集成到 Spark CLI 的可行性，并给出详细实施计划。

---

## 1. 执行摘要

本报告调研了 **OpenCLI**（`jackwener/opencli`）、**public-clis**（`github.com/public-clis` 组织下的 `twitter-cli`、`bilibili-cli`、`rdt-cli`、`tg-cli` 等）、**CLI-Anything**（`HKUDS/CLI-Anything`）三款工具/生态的技术特性、分发方式与调用接口。

基于 Spark CLI 当前 **Go + Cobra + Viper** 的单二进制架构，推荐采用 **"统一 Hub + 分层 Adapter" 模式** 进行集成：

- 新增 `spark hub` 作为所有外部 CLI 的统一管理入口（负责检测、安装提示、通用透传）。
- 将高频/稳定的命令提升为 Spark 的一级子命令：
  - `spark web`    → OpenCLI（网站 / Electron 自动化）
  - `spark social` → public-clis（Twitter/X、Bilibili、Reddit、Telegram 等社交平台 CLI）
  - `spark app`    → CLI-Anything（桌面软件自动化，如 Blender、GIMP、LibreOffice 等）
- 不引入外部运行时依赖，保持 Spark 核心二进制独立；集成部分为 **可选加载（opt-in）**。

该方案在技术、维护和扩展层面均为**高度可行**，预计完整实施周期 **5–6 周**。

---

## 2. 被集成 CLI 生态调研

### 2.1 OpenCLI

| 项目 | 详情 |
|------|------|
| **仓库** | `github.com/jackwener/opencli` |
| **技术栈** | TypeScript / Node.js 20+ |
| **安装方式** | `npm install -g @jackwener/opencli` |
| **典型调用** | `opencli <adapter> <command> [flags]` |
| **输出格式** | `table`(默认)、`json`、`yaml`、`md`、`csv`（`-f/--format`） |
| **核心特点** | 80+ 内置网站适配器；支持 Electron App CDP 控制；自带 **External CLI Hub** 可注册/透传其他 CLI；AI-Agent 友好（`AGENT.md` / skill 标准）；输出结构化、可管道化。 |
| **运行依赖** | Node.js 运行时 + Chrome 浏览器扩展（部分命令） |

**集成要点**：
- 调用方式简单，直接 `os/exec` 子进程执行即可。
- 由于其自身已是 CLI Hub，Spark 可选择 **直接透传** 或 **封装高频命令**。推荐后者，以减少用户记忆成本。
- 需检测 `node` / `npm` / `opencli` 是否存在于 PATH。

### 2.2 public-clis

| 项目 | 详情 |
|------|------|
| **组织** | `github.com/public-clis` |
| **代表项目** | `twitter-cli` (2.1k⭐)、`bilibili-cli` (601⭐)、`rdt-cli` (306⭐)、`tg-cli` (214⭐) |
| **技术栈** | Python |
| **安装方式** | 各项目通常通过 `pip` 或源码安装（如 `pip install twitter-cli` 等，具体以各仓库 README 为准） |
| **典型调用** | `twitter-cli feed`、`bilibili-cli search <keyword>`、`rdt-cli hot`、`tg-cli sync` |
| **输出格式** | 文本 / JSON（视具体 CLI 实现而定） |
| **核心特点** | 针对特定社交平台的高度定制化 CLI；专注终端浏览、搜索、导出；社区活跃，stars 较高。 |
| **运行依赖** | Python 3.x 运行时 |

**集成要点**：
- 每个 CLI 都是独立的二进制/入口点，需要分别检测是否存在。
- 由于它们数量不多且命令语义相对统一（`feed`、`search`、`hot`、`sync` 等），适合在 Spark 中用 **一个 `social` 子命令统一聚合**，再通过二级参数区分平台。
- 例如：`spark social twitter feed`、`spark social bilibili search golang`。
- 也可以考虑借助 **OpenCLI 的 External CLI Hub** 进行自动发现，但直接封装能提供更一致的 Spark UX。

### 2.3 CLI-Anything

| 项目 | 详情 |
|------|------|
| **仓库** | `github.com/HKUDS/CLI-Anything` |
| **技术栈** | Python 3.10+ |
| **安装方式** | `git clone` 后通过 Claude Code / OpenCode / Codex 等 Agent 插件调用；生成的 CLI 通过 `pip install -e .` 安装 |
| **典型调用** | `cli-anything-gimp --json project new`、`cli-anything-blender --help` |
| **输出格式** | 人类可读文本 + `--json` 结构化输出 |
| **核心特点** | **CLI 生成器**：通过 7 阶段流水线（分析→设计→实现→测试计划→测试编写→文档→发布）将任意桌面软件（GIMP、Blender、LibreOffice、Zoom、OBS 等）转化为 agent-native CLI；拥有 **CLI-Hub** 注册表，可自动发现社区 CLI；每个生成的 CLI 自带 `SKILL.md`。 |
| **运行依赖** | Python 3.10+；被控制的桌面软件本身需已安装 |

**集成要点**：
- CLI-Anything **本身不是直接使用的 CLI**，而是一个**生成器**；真正被集成的是它生成的 `cli-anything-*` 系列命令。
- 这些命令具有 **统一的命名模式**（`cli-anything-<software>`）和 **统一的参数风格**（`--json`、子命令组、REPL 模式）。
- Spark 有两种集成策略：
  1. **动态发现**：扫描 PATH 中所有 `cli-anything-*` 前缀的可执行文件，动态注册到 `spark app` 下。
  2. **静态配置**：在 `~/.spark.yaml` 中显式列出用户常用的 `cli-anything-*` 命令。
- 推荐 **策略 1（动态发现）+ 策略 2（白名单过滤）** 相结合，兼顾自动化和可控性。

---

## 3. Spark CLI 现状与集成约束

| 约束项 | 说明 |
|--------|------|
| **技术栈** | Go 1.24+，Cobra CLI 框架，Viper 配置管理 |
| **分发形态** | 单二进制可执行文件，跨平台（Windows/Linux/macOS） |
| **已有模块** | `git`、`agent`、`task` |
| **测试框架** | Ginkgo + Gomega（BDD 风格） |
| **配置体系** | `~/.spark.yaml`（Viper 自动读取） |
| **核心约束** | **不能**因为集成外部 CLI 而强制所有用户安装 Node.js 或 Python。集成必须是可选的（opt-in）。 |

---

## 4. 集成方案对比

| 评估维度 | 方案 A：直接透传 Proxy | 方案 B：Adapter 包装 | 方案 C：混合 Hub+Adapter（**推荐**） |
|----------|------------------------|----------------------|----------------------------------------|
| **代码量** | 最小 | 中等 | 中等 |
| **UX 一致性** | 低（用户仍需学习外部 CLI 语法） | 高 | 高（高频命令统一，复杂命令可透传） |
| **维护成本** | 低 | 高（参数变更需同步更新） | 中（核心命令稳定，透传兜底） |
| **扩展性** | 低（新增 CLI 需新增子命令） | 中 | 高（`hub` 体系可注册任意 Adapter） |
| **风险** | 外部 CLI 变更无影响 | 接口变更可能导致 break | 核心封装稳定，复杂场景走透传 |

### 为什么推荐方案 C

1. **统一入口**：`spark hub` 负责所有外部 CLI 的生命周期管理（检测、诊断、透传）。
2. **高频快捷**：将最常用的能力提升为 Spark 一级子命令，降低用户记忆负担。
3. **保持核心干净**：外部依赖隔离在 `internal/hub` 包中，不污染 `git`、`agent`、`task` 等核心模块。
4. **渐进增强**：用户即使不安装外部 CLI，也能正常使用 Spark 的核心功能。

---

## 5. 推荐的架构设计

### 5.1 目录结构

```
spark/
├── cmd/
│   ├── hub.go              # spark hub 根命令
│   ├── web.go              # spark web (OpenCLI adapter)
│   ├── social.go           # spark social (public-clis adapter)
│   └── app.go              # spark app (CLI-Anything generated CLIs adapter)
├── internal/
│   └── hub/
│       ├── manager.go      # HubManager / Adapter 接口与注册表
│       ├── runner.go       # 子进程执行、安全转义、输出捕获
│       ├── config.go       # hub 配置读取 (~/.spark.yaml 中 hub.*)
│       ├── opencli.go      # OpenCLIAdapter
│       ├── social.go       # SocialCLIAdapter (聚合 twitter-cli/bilibili-cli 等)
│       ├── anything.go     # CLIAnythingAdapter (动态发现 cli-anything-*)
│       └── discover.go     # PATH 扫描、动态注册辅助函数
└── docs/
    └── usage/
        ├── hub.md
        ├── web.md
        ├── social.md
        └── app.md
```

### 5.2 Adapter 接口

```go
package hub

type Adapter interface {
    // 元信息
    Name() string
    DisplayName() string

    // 依赖检测
    Check(ctx context.Context) error

    // 安装指引
    InstallGuide() string

    // 列出该 Adapter 下可用的子命令/子工具（用于 hub list / TUI）
    ListTools() []ToolInfo

    // 将 Spark 参数映射为外部 CLI 参数
    BuildArgs(tool string, sparkArgs []string, flags map[string]string) ([]string, error)

    // 执行前环境准备
    Environ() []string
}

type ToolInfo struct {
    Name        string
    DisplayName string
    Installed   bool
}
```

### 5.3 配置节点设计

在 `~/.spark.yaml` 中新增 `hub` 节点：

```yaml
hub:
  opencli:
    path: "opencli"            # 可自定义二进制路径
    default_format: "json"

  social:
    # 可单独指定每个 CLI 的路径
    twitter:
      path: "twitter-cli"
    bilibili:
      path: "bilibili-cli"
    reddit:
      path: "rdt-cli"
    telegram:
      path: "tg-cli"

  anything:
    # 动态发现：扫描 PATH 中 cli-anything-* 前缀的命令
    auto_discover: true
    # 白名单：只注册以下软件（空列表表示不过滤）
    whitelist: []
    # 黑名单：忽略以下软件
    blacklist: []
```

---

## 6. 命令映射与 UX 设计

### 6.1 Hub 管理命令

```bash
# 列出所有已注册的外部 CLI 适配器及可用状态
spark hub list

# 诊断所有外部 CLI 依赖
spark hub doctor

# 通用透传：在 "--" 后原样传递给外部 CLI
spark hub run opencli -- bilibili hot -f json
spark hub run social.twitter -- feed --limit 20
spark hub run anything.gimp -- --json project new
```

### 6.2 快捷命令 - Web (spark web)

```bash
# 映射到 opencli list
spark web list

# 映射到 opencli <adapter> <command>
spark web bilibili hot -f json
spark web zhihu hot --limit 10
spark web hackernews top

# Electron App 控制
spark web cursor status
spark web cursor open ./my-project
```

### 6.3 快捷命令 - 社交 (spark social)

```bash
# 列出已安装的 social CLI
spark social list

# Twitter/X
spark social twitter feed
spark social twitter bookmarks

# Bilibili
spark social bilibili hot
spark social bilibili search "Golang 教程"

# Reddit
spark social reddit hot
spark social reddit search rust

# Telegram
spark social telegram sync
spark social telegram search "project name"
```

### 6.4 快捷命令 - 桌面应用 (spark app)

```bash
# 列出已安装的 cli-anything-* 命令
spark app list

# 调用具体的 cli-anything 命令
spark app gimp --json project new --width 1920 --height 1080
spark app blender render --file ./scene.blend -o ./output.png
spark app libreoffice convert --input ./doc.docx --output ./doc.pdf

# 进入 REPL（如果该 CLI 支持）
spark app gimp --repl
```

---

## 7. 可行性分析

### 7.1 技术可行性 ⭐⭐⭐⭐⭐ (高)

- **子进程调用**：Go 标准库 `os/exec` 完全满足需求。Spark 核心代码中已有 `internal/git` 等模块大量运用 `exec.Command` 的实践经验。
- **参数安全**：通过 `cmd.Args` 显式传递参数（而非拼接 shell 字符串），天然避免命令注入。
- **配置扩展**：Viper 支持嵌套 key（`hub.opencli.path`），无需改动现有配置加载逻辑。
- **动态发现**：扫描 PATH 中 `cli-anything-*` 前缀的命令仅需 `exec.LookPath` 或遍历 `PATH` 目录，技术门槛低。

### 7.2 维护成本 ⭐⭐⭐ (中)

- **外部 CLI 版本变更** 是最大维护风险。例如 opencli 新增/废弃 flag，或 public-clis 中某个 CLI 变更参数名。
- **缓解策略**：
  1. 快捷命令只封装 **稳定且高频** 的参数（如 `--format`、`--limit`、`--file`）。
  2. 复杂或前沿功能始终通过 `spark hub run <adapter> -- <raw args>` 透传，规避 break 风险。
  3. `spark social` 下各 CLI 的参数映射保持 **最小化封装**，尽量直接透传给原始 CLI。

### 7.3 跨平台兼容性 ⭐⭐⭐⭐⭐ (高)

- **OpenCLI**：Node.js 项目，本身跨平台。Spark 只需检测 `node` / `npm` / `opencli` 是否在 PATH。
- **public-clis**：Python 项目，本身跨平台。Spark 只需检测 `python` / `pip` 及各 CLI 是否在 PATH。
- **CLI-Anything**：生成器及产物均为 Python，本身跨平台。生成的 `cli-anything-*` 命令也是 Python entry points。
- 唯一需要注意的是 Windows 上 Python/Node 的可执行文件名可能是 `python.exe` / `node.exe`，Spark 的 `exec.LookPath` 会自动处理。

### 7.4 安全与隐私风险 ⭐⭐⭐⭐ (低)

- **敏感配置**：部分 social CLI 可能需要 API Token（如 Twitter API）。建议：
  - 默认从 `~/.spark.yaml` 或环境变量读取。
  - 提示用户 `chmod 600 ~/.spark.yaml`。
- **命令注入**：使用 `exec.Command(name, args...)` 而非 `bash -c` 即可消除风险。
- **PATH 扫描安全**：动态发现 `cli-anything-*` 时，只扫描 `PATH` 中的可执行文件，不执行未知脚本，风险可控。

---

## 8. 实施计划

### Phase 1：Hub 基础设施 (第 1–2 周)

- 创建 `internal/hub` 包，定义 `Adapter` 接口、`Runner`、`Config`。
- 实现 `spark hub list` 和 `spark hub doctor`。
- 实现依赖检测通用逻辑（PATH 查找、版本解析）。
- 配置体系接入：在 `~/.spark.yaml` 中支持 `hub.*` 节点。
- **验收标准**：`spark hub list` 能正确显示三个 Adapter 的可用/不可用状态；`spark hub doctor` 能给出清晰的安装指引。

### Phase 2：OpenCLI 集成 (第 2–3 周)

- 实现 `OpenCLIAdapter`。
- 实现 `spark web list`。
- 实现 `spark web <adapter> <command>` 的动态参数透传（利用 Cobra 的 `Args` 机制）。
- 自动追加 `--format json` 以便 Spark 做二次处理（当用户未显式指定格式时）。
- **验收标准**：`spark web bilibili hot -f json` 与 `opencli bilibili hot -f json` 输出一致；未安装 opencli 时给出友好提示。

### Phase 3：public-clis 集成 (第 3–4 周)

- 实现 `SocialCLIAdapter`，支持 `twitter-cli`、`bilibili-cli`、`rdt-cli`、`tg-cli` 的检测与映射。
- 实现 `spark social list`。
- 实现 `spark social <platform> <command>` 动态子命令。
- **验收标准**：`spark social twitter feed` 能正确调用 `twitter-cli feed`；`spark social bilibili search golang` 工作正常。

### Phase 4：CLI-Anything 集成 (第 4–5 周)

- 实现 `CLIAnythingAdapter`。
- 实现 PATH 动态发现逻辑：扫描 `cli-anything-*` 可执行文件。
- 实现 `spark app list`。
- 实现 `spark app <software> [args...]` 动态子命令。
- **验收标准**：安装 `cli-anything-gimp` 后，`spark app list` 能显示 `gimp`；`spark app gimp --json project new` 调用成功。

### Phase 5：文档、测试、发布 (第 5–6 周)

- 为 `internal/hub` 编写 BDD 测试（使用 mock runner 或测试子进程）。
- 更新 `docs/usage/hub.md`、`docs/usage/web.md`、`docs/usage/social.md`、`docs/usage/app.md`。
- 更新 `README.md` 和 `AGENTS.md`。
- 运行 `make lint` 和 `make test`，确保全部通过。
- **验收标准**：所有新功能均有文档覆盖；CI 通过；发布新版本 tag。

---

## 9. 详细任务分解

### Task 1：Hub 包基础设施搭建
- **目标**：建立 `internal/hub` 目录结构和核心接口。
- **输入**：当前 Spark 的 `internal/` 目录规范。
- **输出**：
  - `internal/hub/adapter.go`（接口定义）
  - `internal/hub/manager.go`（注册表）
  - `internal/hub/runner.go`（安全子进程执行）
- **验收标准**：接口编译通过；`Runner` 能正确执行命令并捕获 stdout/stderr/exit code。
- **优先级**：P0
- **工时**：2 天

### Task 2：Hub 配置读取与 Viper 绑定
- **目标**：让 `~/.spark.yaml` 支持 `hub.*` 配置。
- **输入**：`internal/config` 现有逻辑。
- **输出**：`internal/hub/config.go` 及相关结构体。
- **验收标准**：Viper 能正确读取 `hub.opencli.path`、`hub.social.twitter.path`、`hub.anything.auto_discover` 等嵌套 key。
- **优先级**：P0
- **工时**：1 天

### Task 3：`spark hub list` 命令实现
- **目标**：列出所有 Adapter 名称、显示名称、可用状态及子工具列表。
- **输入**：Hub Manager、三个 Adapter 的 `Check()` / `ListTools()` 实现。
- **输出**：`cmd/hub.go` 中的 `hub list` 子命令。
- **验收标准**：终端表格输出正确；未安装时状态显示为 `not installed`。
- **优先级**：P0
- **工时**：1 天

### Task 4：`spark hub doctor` 命令实现
- **目标**：诊断所有外部 CLI 的依赖完整性。
- **输入**：各 Adapter 的 `Check()` 和 `InstallGuide()`。
- **输出**：`cmd/hub.go` 中的 `hub doctor` 子命令。
- **验收标准**：能分别提示 "缺少 Node.js"、"缺少 opencli"、"缺少 twitter-cli" 等并给出安装命令。
- **优先级**：P0
- **工时**：1 天

### Task 5：`spark hub run <adapter> -- <args>` 通用透传实现
- **目标**：为所有 Adapter 提供原生命令透传能力。
- **输入**：Hub Runner。
- **输出**：`cmd/hub.go` 中的 `hub run` 子命令。
- **验收标准**：
  - `spark hub run opencli -- bilibili hot -f json` 输出一致。
  - `spark hub run social.twitter -- feed` 输出一致。
  - `spark hub run anything.gimp -- --json project new` 输出一致。
- **优先级**：P0
- **工时**：1 天

### Task 6：OpenCLI Adapter 实现
- **目标**：封装 `opencli` 的调用逻辑。
- **输入**：OpenCLI 官方文档、参数规范。
- **输出**：`internal/hub/opencli.go`。
- **验收标准**：支持 `BuildArgs` 将 `spark web` 参数映射为 `opencli` 参数；自动追加 `--format json`（当需要时）。
- **优先级**：P1
- **工时**：2 天

### Task 7：`spark web list` 实现
- **目标**：列出 OpenCLI 支持的所有适配器。
- **输入**：OpenCLIAdapter。
- **输出**：`cmd/web.go` 中的 `web list` 子命令。
- **验收标准**：执行 `spark web list` 与 `opencli list` 输出一致。
- **优先级**：P1
- **工时**：1 天

### Task 8：`spark web <adapter> <command>` 动态子命令实现
- **目标**：允许用户像使用 `opencli` 一样通过 `spark web` 调用任意适配器。
- **输入**：Cobra 的 `Args` 处理机制。
- **输出**：`cmd/web.go` 的主 RunE 逻辑。
- **验收标准**：`spark web bilibili hot -f json` 工作正常；未知参数正确透传。
- **优先级**：P1
- **工时**：1.5 天

### Task 9：SocialCLI Adapter 实现
- **目标**：封装 public-clis 下的多个 Python CLI。
- **输入**：`twitter-cli`、`bilibili-cli`、`rdt-cli`、`tg-cli` 文档。
- **输出**：`internal/hub/social.go`。
- **验收标准**：能分别检测四个 CLI 的安装状态；`BuildArgs` 能正确将 `spark social <platform> <cmd>` 映射为对应 CLI 的参数。
- **优先级**：P1
- **工时**：2 天

### Task 10：`spark social list` 实现
- **目标**：列出已安装的 social CLI。
- **输入**：SocialCLIAdapter。
- **输出**：`cmd/social.go` 中的 `social list` 子命令。
- **验收标准**：表格展示 platform、CLI 名称、安装状态。
- **优先级**：P1
- **工时**：1 天

### Task 11：`spark social <platform> <command>` 动态子命令实现
- **目标**：支持 `spark social twitter feed`、`spark social bilibili search golang` 等调用。
- **输入**：SocialCLIAdapter、Cobra Args 机制。
- **输出**：`cmd/social.go` 主 RunE 逻辑。
- **验收标准**：四个平台均支持命令透传；未安装时给出明确提示。
- **优先级**：P1
- **工时**：1.5 天

### Task 12：CLI-Anything Adapter 实现
- **目标**：封装 CLI-Anything 生成的 `cli-anything-*` 命令。
- **输入**：CLI-Anything 文档、CLI-Hub 注册表格式。
- **输出**：`internal/hub/anything.go`。
- **验收标准**：
  - `auto_discover: true` 时，能扫描 PATH 并列出所有 `cli-anything-*`。
  - 支持 `whitelist` / `blacklist` 过滤。
- **优先级**：P1
- **工时**：2 天

### Task 13：PATH 动态发现逻辑实现
- **目标**：安全地扫描 PATH 目录，发现 `cli-anything-*` 可执行文件。
- **输入**：`os.Getenv("PATH")`、平台路径分隔符规则。
- **输出**：`internal/hub/discover.go`。
- **验收标准**：Windows / Linux / macOS 均能正确发现；忽略非可执行文件；不执行任何外部程序（仅扫描文件名）。
- **优先级**：P1
- **工时**：1 天

### Task 14：`spark app list` 实现
- **目标**：列出已安装的 cli-anything 软件。
- **输入**：CLIAnythingAdapter、Discover 逻辑。
- **输出**：`cmd/app.go` 中的 `app list` 子命令。
- **验收标准**：安装 `cli-anything-gimp` 和 `cli-anything-blender` 后，`spark app list` 正确显示。
- **优先级**：P1
- **工时**：1 天

### Task 15：`spark app <software> [args...]` 动态子命令实现
- **目标**：支持调用任意 cli-anything 生成的 CLI。
- **输入**：CLIAnythingAdapter、Cobra Args 机制。
- **输出**：`cmd/app.go` 主 RunE 逻辑。
- **验收标准**：`spark app gimp --json project new` 与 `cli-anything-gimp --json project new` 输出一致；支持 `--repl` 等原生参数透传。
- **优先级**：P1
- **工时**：1.5 天

### Task 16：Hub 模块 BDD 测试编写
- **目标**：为 `internal/hub` 编写 Ginkgo/Gomega 测试。
- **输入**：现有 `internal/config/config_test.go`、`internal/git/finder_test.go` 风格。
- **输出**：`internal/hub/hub_test.go` 及各 Adapter 的单元测试。
- **验收标准**：覆盖率 > 60%；使用 mock runner 避免强依赖外部二进制。
- **优先级**：P1
- **工时**：2 天

### Task 17：集成测试与端到端验证
- **目标**：在真实环境中验证三个 Adapter 的可用性。
- **输入**：已安装 opencli、twitter-cli、cli-anything-gimp（可选）的测试环境。
- **输出**：测试报告、问题修复 PR。
- **验收标准**：
  - `spark web list` 在已安装 opencli 的机器上成功。
  - `spark social twitter --help` 透传成功。
  - `spark app list` 能动态发现已安装的 cli-anything 命令。
- **优先级**：P1
- **工时**：2 天

### Task 18：使用文档编写
- **目标**：为 `hub`、`web`、`social`、`app` 编写使用说明。
- **输入**：现有 `docs/usage/*.md` 模板。
- **输出**：
  - `docs/usage/hub.md`
  - `docs/usage/web.md`
  - `docs/usage/social.md`
  - `docs/usage/app.md`
- **验收标准**：文档包含安装前置条件、配置示例、常用命令、故障排查。
- **优先级**：P2
- **工时**：2 天

### Task 19：README & AGENTS.md 更新
- **目标**：同步更新项目根目录文档，保持信息一致。
- **输入**：新增的功能列表。
- **输出**：更新后的 `README.md`、`AGENTS.md`。
- **验收标准**：README 中出现 "External CLI Hub" 章节；AGENTS.md 中记录本次集成任务。
- **优先级**：P2
- **工时**：0.5 天

### Task 20：Lint、构建与 CI 检查
- **目标**：确保代码符合项目规范，CI 通过。
- **输入**：Makefile、GitHub Actions（如有）。
- **输出**：无报错构建产物。
- **验收标准**：`make lint` 和 `make test` 全部通过。
- **优先级**：P0
- **工时**：0.5 天

---

## 10. 附录

### 10.1 `~/.spark.yaml` 配置示例

```yaml
# Spark 核心配置
repo-path:
  - ~/workspace

git:
  username: your-name
  email: your@email.com

# 外部 CLI Hub 配置
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

### 10.2 安装检测逻辑伪代码

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
    // 分别检测 twitter-cli, bilibili-cli 等
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

### 10.3 关于 CLI-Anything 动态发现的安全说明

`spark app list` 通过扫描 `PATH` 环境变量中所有以 `cli-anything-` 为前缀的可执行文件来动态发现工具。**不会执行这些文件**，仅通过文件名匹配进行识别。实际调用时仍通过 `exec.Command(name, args...)` 安全传参，避免命令注入风险。

---

*报告结束*
