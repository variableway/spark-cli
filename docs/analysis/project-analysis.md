# Spark CLI 项目分析报告

## 项目概述

Spark CLI 是一个 Go 语言编写的命令行工具，定位为日常开发自动化和 AI Skill 集成的 CLI 后端。

**核心理念：** 确定性任务通过 CLI 自动化执行，节省 LLM token 成本；同时为 AI Agent 提供 CLI 调用接口。

## 技术栈

| 层面 | 技术选型 |
|------|---------|
| 语言 | Go 1.25 |
| CLI 框架 | Cobra |
| 配置管理 | Viper |
| 终端 UI | PTerm + Bubble Tea |
| 测试框架 | Ginkgo / Gomega |
| 文档生成 | docmd |

## 功能模块

| 模块 | 命令 | 功能 |
|------|------|------|
| Git 管理 | `spark git` | 多仓库更新、Mono-repo 创建、子模块同步、Gitcode 远程、组织克隆 |
| Agent 配置 | `spark agent` | 多种 AI Agent（Claude Code、Codex、Kimi、GLM）的配置管理和 Profile 切换 |
| 任务管理 | `spark task` | 任务创建、分发、同步、AI 实现 |
| 系统工具 | `spark magic` | DNS 刷新、pip/go/node 镜像源切换 |
| 脚本管理 | `spark script` | 自定义脚本发现与执行 |
| 文档管理 | `spark docs` | 文档结构初始化、docmd 站点配置 |

## 架构设计

```
main.go → cmd.Execute()
│
├── cmd/                    # Cobra 命令定义层
│   ├── git/                # Git 操作命令组
│   ├── magic/              # 系统工具命令组
│   ├── script/             # 脚本管理命令组
│   ├── docs/               # 文档管理命令组
│   ├── agent.go            # Agent 命令
│   ├── agent_profile.go    # Profile 子命令
│   └── task.go             # 任务命令
│
└── internal/               # 业务逻辑层
    ├── agent/              # Agent 配置管理
    ├── config/             # 配置加载与迁移
    ├── git/                # Git 核心操作
    ├── github/             # GitHub API 交互
    ├── mono/               # Mono-repo 管理
    ├── script/             # 脚本发现与执行
    ├── task/               # 任务工作流
    └── tui/                # 终端 UI 组件
```

**设计特点：**
- cmd/ 只负责参数解析和调用 internal/ 的逻辑
- internal/ 包之间低耦合，各司其职
- 支持 `--tui` 标志在 CLI 和交互模式间切换

## 优点

### 1. 清晰的架构分层
cmd/ 和 internal/ 的职责划分明确，命令层只做参数解析和 UI 呈现，业务逻辑完全在 internal/ 中。

### 2. 良好的外部库选型
Cobra + Viper + PTerm 是 Go CLI 开发的成熟组合，降低了开发和维护成本。

### 3. AI Agent 统一抽象
将多种 AI Agent（Claude Code、Codex、Kimi、GLM）的配置管理统一到一套接口下，通过 Profile 模板实现跨项目切换。

### 4. 实用导向
每个功能都源于真实的工作需求（多仓库管理、镜像切换、DNS 刷新），不是为了技术而技术。

### 5. 配置迁移支持
自动将旧配置 `.monolize.yaml` 迁移到 `.spark.yaml`，体现了对用户的尊重。

## 需要改进的方面

### 1. 测试覆盖不足
- `internal/agent/` 和 `internal/mono/` 完全没有测试
- cmd/ 层缺少集成测试
- 现有测试质量不错（使用 Ginkgo BDD 风格），但覆盖面需要扩展

### 2. 外部命令依赖过重
大量使用 `exec.Command` 调用 `git`、`gh`、`kimi`、`npm` 等外部命令，缺少抽象层。这导致：
- 难以在不安装这些工具的环境中运行
- 单元测试需要 mock 整个环境
- 错误信息不够精确

### 3. 错误处理不一致
- 部分函数返回错误链 (`fmt.Errorf("...: %w", err)`)，部分直接返回
- 缺少统一的错误类型和用户友好的错误提示
- 某些路径缺少上下文信息

### 4. 代码重复
- `cmd/magic/` 下 pip.go、go.go、node.go 的代码结构高度相似（list/use/current），可以提取为通用模板
- 多处文件拷贝逻辑重复出现
- `exec.Command` 的调用模式重复

### 5. 配置验证缺失
- 没有对配置值进行验证
- 缺少配置文件的 schema 定义
- 环境变量覆盖支持不足

## 改进建议

| 优先级 | 改进项 | 预期收益 |
|--------|--------|---------|
| 高 | 补充 internal/agent/ 和 internal/mono/ 的测试 | 提高代码可靠性 |
| 高 | 提取外部命令执行抽象层 | 可测试性 + 可维护性 |
| 中 | 统一 magic 命令的 mirror 切换模式 | 减少 60% 重复代码 |
| 中 | 添加配置验证 | 减少用户配置错误 |
| 低 | 添加集成测试 | 端到端验证 |
| 低 | 添加 contribution guide | 降低贡献门槛 |

## 总结

Spark CLI 是一个实用的开发工具，架构清晰、功能覆盖合理。核心优势在于将多种日常开发操作（Git 管理、镜像切换、AI Agent 配置）统一到一个 CLI 中，并通过 Profile 系统和 TUI 模式提供了良好的用户体验。主要改进方向是扩展测试覆盖、减少代码重复、统一外部命令调用模式。
