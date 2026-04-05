# Spark Hub 架构决策 RFC

**版本**: v1.0  
**日期**: 2026-04-02  
**状态**: 草案（Draft）  
**目标**: 评估独立 Hub 仓库的必要性，深度剖析 OpenCLI Hub 协议的优劣，明确 spark-hub、opencli、cli-anything 三者的边界与协作关系，并给出可执行的架构决策。

---

## 1. 执行摘要

经过对 **OpenCLI** (`jackwener/opencli`)、**public-clis** (`github.com/public-clis`)、**CLI-Anything** (`HKUDS/CLI-Anything`) 的深入调研，以及对 **OpenCLI External CLI Hub** 协议机制的分析，本 RFC 提出以下核心结论：

1. **应当创建独立的 `spark-hub` 仓库**。将 Hub 能力从 `spark-cli` 中解耦，是长期架构健康的唯一选择。
2. **`spark-cli` 应作为 `spark-hub` 的第一个"原生注册成员"**，而非反过来把 Hub 内嵌进 spark-cli。
3. **OpenCLI 的 Hub 协议是一个"强绑定、高便利、但控制面不透明"的封装层**。直接复用它可以节省 30–40% 的工程量，但会失去对注册表格式、安装策略和错误处理链路的完全掌控。
4. **推荐策略**：`spark-hub` 采用 **"自有注册表协议 + OpenCLI 桥接适配器"** 的混合架构。即：
   - 核心用 Go 自研（ registry 格式、安装器、透传执行器）。
   - 通过 `opencli-bridge` 插件，将 OpenCLI 已支持的 80+ adapter 和 External CLI Hub 无缝接入，避免重复造轮子。
5. **CLI-Anything 与 spark-hub 不是竞争关系**。CLI-Anything 是 "CLI 生成器"（Producer），spark-hub 是 "CLI 聚合器/路由器"（Consumer + Registry）。

---

## 2. 问题背景

### 2.1 用户原始需求

用户希望方便地将以下 CLI 生态集成到 Spark 品牌下：
- **OpenCLI**：网站/Electron 自动化（80+ 内置适配器）。
- **public-clis**：社交平台 CLI（Twitter/X、Bilibili、Reddit、Telegram）。
- **CLI-Anything**：桌面软件自动化（GIMP、Blender、LibreOffice 等生成的 `cli-anything-*` 命令）。

### 2.2 架构层面的关键疑问

| 疑问 | 影响 |
|------|------|
| Hub 应该放在 spark-cli 内部，还是独立仓库？ | 决定维护边界、版本耦合度和生态开放性。 |
| OpenCLI 已经有 External CLI Hub，是否还需要自研？ | 决定控制面归属、协议灵活性和品牌独立性。 |
| CLI-Anything 是否可以直接替代 Hub？ | 决定产品定位是否混淆。 |

---

## 3. OpenCLI External CLI Hub 深度分析

### 3.1 OpenCLI Hub 的工作机制

OpenCLI 的 External CLI Hub 并不是一个公开文档化的独立协议，而是内嵌在 OpenCLI 运行时中的一套 **"命令发现 + 自动安装 + 透传执行"** 机制。根据源码和文档分析，其核心行为如下：

#### 3.1.1 发现机制（Discovery）

1. **内置白名单**：OpenCLI 维护了一个硬编码的 External CLI 列表（如 `gh`、`obsidian`、`docker`、`lark-cli`、`dingtalk`、`wecom`、`vercel` 等）。
2. **用户注册**：通过 `opencli register mycli` 可以将本地任意 CLI 注册到 OpenCLI 的 discovery 表中，使其出现在 `opencli list` 的输出中。
3. **动态扫描**：对于内置的 adapters（`.ts` / `.yaml` 文件放入 `src/clis/<site>/` 即自动注册），OpenCLI 在启动时动态扫描并加载。

#### 3.1.2 执行机制（Execution）

- 当用户输入 `opencli gh pr list` 时：
  1. OpenCLI 解析命令树，发现 `gh` 不在内置 adapter 中，但在 External CLI Hub 列表中。
  2. 检查 `gh` 是否在 PATH 中。
  3. 如果存在，**纯透传**（passthrough）执行 `gh pr list`。
  4. 如果不存在，触发 **auto-install**（例如在 macOS 上运行 `brew install gh`），安装成功后重新执行。

#### 3.1.3 注册机制（Registration）

```bash
opencli register mycli --path /usr/local/bin/mycli
```

- 注册信息保存在 OpenCLI 的内部数据目录中（推测为 `~/.opencli/` 或类似路径的 JSON/YAML 文件）。
- 注册后的 CLI 可被 `opencli list --all` 发现，也可被 AI Agent 通过 `AGENT.md` 协议调用。

#### 3.1.4 插件机制（Plugin）

- `opencli plugin install github:user/opencli-plugin-my-tool`
- 插件本质是符合 OpenCLI 宿主约定的 npm/TypeScript 包，通过 symlink 或复制到 OpenCLI 的 `node_modules/` 下实现加载。
- 插件与宿主共享 `@jackwener/opencli/registry` 运行时。

### 3.2 OpenCLI Hub 的优势（Strengths）

| 优势 | 说明 |
|------|------|
| **零配置透传** | 对已知 CLI（如 `gh`、`docker`）无需任何 wrapper 代码，直接转发参数。 |
| **自动安装** | 如果检测到 CLI 缺失，自动调用包管理器安装（`brew install`、`apt install` 等），对用户极度友好。 |
| **AI-Agent 原生集成** | 所有注册的 CLI 都会通过 `AGENT.md` / `SKILL.md` 协议暴露给 Claude Code、Cursor、Codex 等 Agent。 |
| **80+ 内置适配器** | 网站/Electron 自动化的覆盖度极高，社区活跃（8k+ stars）。 |
| **结构化输出统一** | 内置 adapter 全部支持 `--format json/yaml/md/csv`，降低了下游消费难度。 |
| **自诊断能力** | `opencli doctor` 可以检测浏览器扩展、daemon 状态、外部 CLI 可用性。 |

### 3.3 OpenCLI Hub 的劣势与风险（Weaknesses & Risks）

| 劣势 | 详细说明 | 对 spark-hub 的影响 |
|------|----------|----------------------|
| **协议不透明** | External CLI Hub 的注册表格式、auto-install 策略、数据目录结构没有公开文档。如果想深度集成，必须阅读源码或做黑盒推断。 | 若直接依赖，后续 OpenCLI 内部重构可能导致 spark-hub 的桥接代码失效。 |
| **强运行时绑定** | OpenCLI 是 Node.js 项目，Hub 能力内嵌在 OpenCLI 进程中。无法将 "Hub 协议" 单独拆出来作为一个轻量级服务或库使用。 | 用户必须安装 Node.js + OpenCLI 才能使用 Hub 功能，无法做到像 spark-hub（Go 单二进制）那样的零依赖分发。 |
| **控制面受限** | 注册表是 OpenCLI 的私有实现，无法自定义：
- 不能改变 `opencli list` 的输出格式（虽然有 `-f json`，但字段由 OpenCLI 定义）。
- 不能拦截或重写安装逻辑（例如从企业内部镜像安装）。
- 不能为同一个 CLI 设置多版本切换。 | 企业场景（私有 registry、镜像源）下扩展困难。 |
| **命令命名冲突** | OpenCLI 内置 adapter 和 External CLI 共享同一个命名空间（`opencli <name>`）。如果未来 OpenCLI 官方新增了一个也叫 `spark` 的内置 adapter，那么 `opencli spark` 的语义会发生冲突。 | spark-cli 注册进 OpenCLI Hub 后，存在被未来版本覆盖的风险。 |
| **错误处理链路不可控** | 透传执行时，外部 CLI 的 exit code、stderr、进度条输出会原样返回。如果外部 CLI 挂起或交互式提示，OpenCLI 没有提供统一的 timeout 或 no-input 策略。 | 在 CI/Agent 自动化场景中可能导致流程卡住。 |
| **跨平台安装策略不一致** | auto-install 依赖于对包管理器的硬编码映射（macOS→brew，Linux→apt 等），在 Windows 或国产 Linux 发行版上可能行为不可预期。 | 如果 spark-hub 面向中国开发者，brew/apt 的默认策略并不总是最优。 |

### 3.4 关键结论：OpenCLI Hub 适合作为 "被桥接的生态"，而非 "Hub 核心"

OpenCLI Hub 的最大价值在于它**已经连接了一个庞大的 CLI 和网站适配器生态**。spark-hub 不应该试图替代这个生态，而应该：
- **把 OpenCLI 当作一个强大的 "子生态" 来接入**。
- **自己掌握路由层、注册表格式和安装策略**。

---

## 4. CLI-Anything 的定位分析

### 4.1 CLI-Anything 是什么

CLI-Anything (`HKUDS/CLI-Anything`) 是一个 **CLI 生成器框架**。它的核心能力：

1. 输入：任意桌面软件的源码或二进制（GIMP、Blender、LibreOffice、Zoom 等）。
2. 处理：通过 7 阶段流水线（分析→设计→实现→测试计划→测试编写→文档→发布），由 AI Agent 自动生成一个 Python CLI。
3. 输出：`cli-anything-<software>`（如 `cli-anything-gimp`），自带 `SKILL.md`、JSON 输出、REPL 模式。

### 4.2 CLI-Anything 与 spark-hub 的关系

| 维度 | CLI-Anything | spark-hub |
|------|--------------|-----------|
| **核心动作** | 生产 CLI | 发现、注册、路由、执行 CLI |
| **产出物** | `cli-anything-*` Python 包 | Go 单二进制可执行文件 |
| **与 OpenCLI 的关系** | 生成的 CLI 可以被 OpenCLI Hub 注册 | 可以桥接 OpenCLI，也可以直接发现 `cli-anything-*` |
| **是否替代 Hub？** | **否**。它只是 Hub 生态中的一个重要内容来源。 | **是**。它是消费端和调度端。 |

**比喻**：
- CLI-Anything = **工厂**（造工具的）
- OpenCLI = **大型连锁超市**（自有品牌 + 代销其他品牌）
- spark-hub = **独立的购物平台/路由器**（可以接入连锁超市的货，也可以直接接入工厂的货，自己掌握用户界面和物流）

---

## 5. 三种架构方案对比

### 方案 A：Hub 内嵌在 spark-cli（Monolith）

- `spark-cli` 新增 `spark hub`、`spark web`、`spark social`、`spark app` 子命令。
- **优点**：用户只下载一个二进制即可。
- **缺点**：
  - spark-cli 的职责从 "Git 工具" 膨胀为 "万能工具箱"。
  - 每次 Hub 层改动都要发 spark-cli 版本，版本号语义混乱。
  - 非 Git 用户无法单独使用 Hub 能力。
- **结论**：**不推荐**。

### 方案 B：完全复用 OpenCLI Hub（Thin Wrapper）

- 独立仓库 `spark-hub`，但内部几乎不实现逻辑，只是 `opencli` 的一个薄包装。
- **优点**：开发量最小，快速上线。
- **缺点**：
  - 完全受限于 OpenCLI 的协议和版本节奏。
  - 无法自定义 registry 格式、安装策略、企业镜像。
  - 品牌存在感弱（用户会觉得 "这不就是 opencli 换了个皮？"）。
- **结论**：**不推荐作为长期方案**，但可作为 MVP 快速验证。

### 方案 C：独立 spark-hub + 自有协议 + OpenCLI/CLI-Anything 桥接（**强烈推荐**）

- 独立仓库 `spark-hub`，技术栈 Go（与 spark-cli 一致）。
- 定义自己的 **Spark Registry Protocol (SRP)**：JSON/YAML 格式的 CLI 注册表。
- 核心模块：
  - **Registry Manager**：读取本地 registry、远程 registry（可配置）。
  - **Installer**：支持多后端（brew、apt、winget、npm、pip、curl、企业内部镜像）。
  - **Executor**：安全子进程执行（timeout、stdin 隔离、exit code 透传）。
  - **Bridge Adapters**：
    - `opencli-bridge`：将 OpenCLI 的内置 adapter + External CLI Hub 映射到 SRP。
    - `anything-bridge`：扫描 PATH 中的 `cli-anything-*` 并自动注册到 SRP。
    - `social-bridge`：手动维护 public-clis 的映射。
- **优点**：
  - 完全掌控 registry 格式和路由策略。
  - 可以接入多个异构生态（OpenCLI、CLI-Anything、public-clis、未来更多）。
  - spark-cli 作为普通成员注册，关系清晰。
  - 支持企业私有化部署（自定义 registry URL、镜像源）。
- **缺点**：
  - 初始开发量比方案 B 大（约多 40%）。
  - 需要维护桥接适配器（但适配器逻辑通常是稳定的透传）。
- **结论**：**推荐**。

---

## 6. 推荐的架构设计

### 6.1 仓库结构

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
│   ├── registry/        # Spark Registry Protocol 核心
│   │   ├── model.go     # Registry 数据结构
│   │   ├── loader.go    # 本地/远程 registry 加载
│   │   └── merger.go    # 多源 registry 合并
│   ├── installer/       # 安装器抽象与实现
│   │   ├── manager.go
│   │   ├── brew.go
│   │   ├── apt.go
│   │   ├── winget.go
│   │   ├── npm.go
│   │   ├── pip.go
│   │   └── script.go    # 自定义安装脚本
│   ├── executor/        # 安全执行器
│   │   ├── runner.go
│   │   └── sanitize.go
│   └── bridge/          # 异构生态桥接
│       ├── opencli/     # OpenCLI bridge
│       ├── anything/    # CLI-Anything bridge
│       └── social/      # public-clis bridge
├── pkg/
│   └── srp/             # Spark Registry Protocol 公开规范
│       └── v1/
│           ├── types.go
│           └── schema.json
├── registry/
│   └── default.yaml     # 默认内置 registry（含 spark-cli、opencli 等元信息）
└── docs/
    ├── architecture.md
    └── srp-v1.md
```

### 6.2 Spark Registry Protocol (SRP) v1 草案

```yaml
# registry.yaml 示例
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
      # 指定该 CLI 应由 social-bridge 处理参数映射
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

### 6.3 命令设计

```bash
# 列出所有已知 CLI（合并本地 registry + 桥接发现）
spark-hub list

# 诊断依赖
spark-hub doctor

# 安装某个 CLI（调用 registry 中声明的 install strategy）
spark-hub install opencli
spark-hub install twitter
spark-hub install gimp

# 通用透传
spark-hub run opencli -- bilibili hot -f json
spark-hub run twitter -- feed --limit 20
spark-hub run gimp -- --json project new

# 注册本地自定义 CLI
spark-hub register ./my-custom-cli --name mycli

# 管理 registry 源
spark-hub registry add https://mycompany.com/spark-registry.yaml
spark-hub registry list
```

### 6.4 spark-cli 的改动

spark-cli 只需要**极薄的桥接命令**：

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

这样 `spark hub` 等价于 `spark-hub`，用户体验无缝，但架构边界清晰。

---

## 7. OpenCLI 桥接适配器设计要点

### 7.1 bridge/opencli 的职责边界

该桥接器**不**试图理解 OpenCLI 的内部数据格式，而是将其视为一个黑盒的、功能强大的 CLI 池，通过以下方式集成：

1. **发现（Discovery）**
   - 调用 `opencli list -f json` 获取所有可用命令（包括内置 adapter 和 External CLI）。
   - 将结果转换为 SRP 的 `CLIEntry` 列表，标记 `source: opencli`。

2. **执行（Execution）**
   - 当用户执行 `spark-hub run opencli -- bilibili hot -f json` 时，Executor 直接转发为 `opencli bilibili hot -f json`。
   - 当用户执行 `spark-hub run gh -- pr list`（且 `gh` 在 OpenCLI 的 External CLI Hub 中）时，Executor 转发为 `opencli gh pr list`。

3. **安装（Installation）**
   - 对于 OpenCLI 自身：SRP registry 中声明 `npm install -g @jackwener/opencli`。
   - 对于 OpenCLI 内置的 External CLI（如 `gh`、`docker`）：**委托给 OpenCLI 的 auto-install**。即 spark-hub 检测到 `gh` 未安装时，可以直接执行 `opencli gh --version`，让 OpenCLI 自己触发 `brew install gh`。
   - 也可以选择在 spark-hub 层自己处理安装，绕过 OpenCLI 的 auto-install（更可控）。

### 7.2 关键边界约定

| 场景 | 处理方式 |
|------|----------|
| `opencli` 未安装 | `spark-hub doctor` 提示安装 Node.js + OpenCLI；`spark-hub install opencli` 执行 npm 安装。 |
| OpenCLI 命令与 SRP 命令重名 | 以 SRP 显式声明的 `clis` 为准（显式 > 桥接发现）。例如如果 SRP 中也有一个 `twitter` 条目，优先执行 SRP 定义的安装器/执行器，而非 OpenCLI 桥接。 |
| OpenCLI 返回非 0 exit code | 原样透传给 `spark-hub` 用户。 |
| OpenCLI 输出格式 | 保持透传。如果下游 Agent 需要 JSON，由用户显式在 `spark-hub run` 时传入 `-f json`。 |

---

## 8. 风险评估与缓解策略

| 风险 | 概率 | 影响 | 缓解策略 |
|------|------|------|----------|
| OpenCLI 内部协议变更导致桥接失效 | 中 | 中 | 桥接器只依赖 `opencli list -f json` 和命令透传两个稳定接口，不深入解析内部配置文件。 |
| `spark-hub` 初始开发周期长，延迟上线 | 中 | 高 | Phase 1 先做最小可用版本（list + run + opencli bridge），其余桥接器和安装器逐步迭代。 |
| 用户混淆 `spark-cli` 和 `spark-hub` 的关系 | 高 | 低 | 文档中明确区分：spark-cli 做 Git，spark-hub 做 CLI 管理；`spark hub` 只是快捷入口。 |
| public-clis 各项目接口不统一，映射成本高 | 中 | 中 | `social-bridge` 只做最薄封装：将 `spark-hub run twitter -- feed` 映射为 `twitter-cli feed`，不强行统一 flag 命名。 |
| CLI-Anything 生成的命令命名冲突 | 低 | 中 | `anything-bridge` 扫描到的命令会带上 `anything-` 前缀注册到 SRP（如 `anything-gimp`），用户通过 `spark-hub run anything-gimp` 调用。 |

---

## 9. 实施路线图

### Phase 1：spark-hub 骨架 + OpenCLI 桥接（MVP，2–3 周）

- 创建 `spark-hub` 仓库，Go + Cobra 脚手架。
- 定义 SRP v1 基础数据结构（YAML 解析）。
- 实现 `spark-hub list`、`spark-hub run`、`spark-hub doctor`。
- 实现 `bridge/opencli`：调用 `opencli list -f json` 并映射为 SRP 条目。
- 默认 registry 中注册 `spark-cli` 和 `opencli`。
- **验收标准**：安装 OpenCLI 后，`spark-hub list` 能看到 OpenCLI 的命令；`spark-hub run opencli -- hackernews top` 能正常输出。

### Phase 2：安装器 + CLI-Anything 桥接（2 周）

- 实现 Installer Manager，支持 npm/pip 策略。
- 实现 `spark-hub install <cli>`。
- 实现 `bridge/anything`：扫描 `cli-anything-*` 前缀命令。
- **验收标准**：`spark-hub install opencli` 能自动执行 npm 安装；安装 `cli-anything-gimp` 后 `spark-hub list` 能发现它。

### Phase 3：public-clis 桥接 + spark-cli 薄包装（1–2 周）

- 实现 `bridge/social`：静态注册 `twitter-cli`、`bilibili-cli`、`rdt-cli`、`tg-cli`。
- 在 `spark-cli` 中添加 `spark hub` 转发命令。
- 编写 BDD 测试和文档。
- **验收标准**：`spark social twitter feed`（通过 `spark hub run social.twitter -- feed`）能正确调用 `twitter-cli feed`。

### Phase 4：企业特性与生态扩展（持续）

- 支持远程 registry URL（`spark-hub registry add`）。
- 支持自定义安装镜像源。
- 支持 Agent 协议的 `SKILL.md` 自动生成。

---

## 10. 决策总结

| 问题 | 决策 |
|------|------|
| 是否创建独立 `spark-hub` 仓库？ | **是**。架构更清晰，生态更开放。 |
| `spark-cli` 放在哪里？ | 作为 `spark-hub` registry 中的普通一员，`spark-cli` 自身只保留一个 `spark hub` 转发命令。 |
| 是否完全复用 OpenCLI Hub？ | **否**。OpenCLI Hub 是黑盒协议，控制力不足。应选择 "自研 Hub + OpenCLI 桥接" 的混合模式。 |
| CLI-Anything 与 Hub 的关系？ | CLI-Anything 是 **内容生产者**（生成 CLI），spark-hub 是 **内容聚合者**（发现、安装、执行 CLI）。两者互补。 |
| 第一个 MVP 应该做多大？ | 只做 `list` + `run` + `doctor` + `opencli-bridge`，2–3 周内完成并发布 v0.1.0。 |

---

## 11. 附录：相关资源

- OpenCLI: https://github.com/jackwener/opencli
- public-clis: https://github.com/public-clis
- CLI-Anything: https://github.com/HKUDS/CLI-Anything
- spark-cli (当前项目): `/Users/patrick/innate/spark-cli`

---

*文档结束*
