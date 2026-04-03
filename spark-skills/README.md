# Spark Skills

个人习惯的 AI Agent Skill 仓库，统一收集、管理和分发适配多种 AI 编程助手的 Skills。

## 支持的 AI Agent

本仓库中的 Skill 力求兼容以下 Agent 工具：

| Agent | 配置文件位置 | 说明 |
|-------|-------------|------|
| **Claude Code** | `~/.claude/skills/` | 通过 `SKILL.md` 自动识别 |
| **Kimi CLI** | `~/.kimi/skills/` 或 Kimi 内置 skills | 通过 `SKILL.md` 自动识别 |
| **Codex** | `~/.codex/skills/` (或项目目录) | 通过 `SKILL.md` 自动识别 |
| **OpenCode** | `~/.opencode/skills/` (或项目目录) | 通过 `SKILL.md` 自动识别 |

> 所有 Skill 均以标准 `SKILL.md` 作为入口，并辅以 Python 脚本和参考文档。

## 快速安装

### 方式一：使用安装脚本（推荐）

```bash
# 安装所有 skills 到 Claude Code
./install.sh claude-code

# 安装所有 skills 到 Kimi
./install.sh kimi

# 安装所有 skills 到 Codex
./install.sh codex

# 安装所有 skills 到 OpenCode
./install.sh opencode
```

### 方式二：项目级一键配置

```bash
# 在当前 git 仓库中自动安装 hooks、配置、GitHub Actions 和示例任务
bash /path/to/spark-skills/setup-project.sh
```

这会帮你完成：
1. 安装 `post-commit` 和 `prepare-commit-msg` Git hooks
2. 创建 `.github-task-workflow.yaml` 项目配置
3. 创建 `tasks/` 目录和示例 task 文件
4. 创建 `.github/workflows/close-issue-on-merge.yml`
5. 将 skill 安装到 `~/.claude/skills/`、`~/.kimi/skills/` 和 `~/.config/agents/skills/`

### 方式三：手动链接

```bash
# 以 Claude Code 为例
ln -s $(pwd)/github-task-workflow ~/.claude/skills/github-task-workflow
```

## 已包含 Skills

### `github-task-workflow`

通过 GitHub Issues 管理任务全生命周期：从任务创建、实现跟踪到提交完成总结。

> **注意**：这是一个 AI Agent Skill，支持三种使用方式：
> 1. **普通对话模式（推荐）**：直接说"请执行 tasks/xxx.md"
> 2. **普通对话模式**：直接说"执行 `tasks/xxx.md`"
> 3. **编排器模式（跨 Agent）**：`python scripts/orchestrate.py init tasks/xxx.md`，然后 AI 实现，再 `python scripts/orchestrate.py finish`

**核心能力**：
- **创建 Issue**：`python scripts/create_issue.py --title "..." --body "..."`
- **更新 Issue**：`python scripts/update_issue.py --issue 123 --comment "..."`
- **跨 Agent 编排器**：`python scripts/orchestrate.py init/finish/status/abort`
- **自动仓库检测**：支持从 git remote 自动推断 `owner/repo`
- **多级配置**：支持命令行参数、环境变量、项目级配置、全局配置

**自定义 Agent（强制工作流）**：
```bash
kimi --agent-file github-task-workflow/agent/kimi-agent.yaml
```

详见：[github-task-workflow/SKILL.md](github-task-workflow/SKILL.md)

### `spark-task-init`

为 spark-cli 初始化任务目录结构的 Skill。

**功能**：
- 创建任务目录结构（tasks/features/, tasks/config/ 等）
- 创建示例特性模板文件
- 可在任意目录执行

**使用方式**：
```bash
# 方式一：使用 spark 命令
spark task init

# 方式二：使用 skill 直接执行
kimi --agent-file spark-task-init-skill/SKILL.md
```

详见：[spark-task-init-skill/SKILL.md](spark-task-init-skill/SKILL.md)

## 仓库结构

```
spark-skills/
├── README.md                          # 本文件
├── SETUP.md                           # 仓库构建过程文档
├── install.sh                         # 多 Agent 安装脚本
├── github-task-workflow/              # Skill: GitHub 任务工作流
│   ├── SKILL.md                       # Skill 入口（标准格式）
│   ├── scripts/                       # 可执行脚本
│   │   ├── config_loader.py
│   │   ├── create_issue.py
│   │   └── update_issue.py
│   └── references/                    # 详细参考文档
│       └── workflow.md
├── spark-task-init-skill/             # Skill: spark task 初始化
│   └── SKILL.md                       # Skill 入口
└── ...                                # 未来添加更多 skills
```

## 添加新 Skill

1. 在仓库根目录创建新文件夹，命名即为 skill 名称
2. 编写 `SKILL.md`，包含标准的 YAML frontmatter：

```yaml
---
name: your-skill-name
description: 一句话描述该 skill 的用途和触发场景
supported_agents:
  - claude-code
  - kimi
  - codex
  - opencode
---
```

3. 在 `SKILL.md` 同级目录下按需创建 `scripts/`、`references/` 等子目录
4. 更新本 README 的 Skill 列表
5. 运行 `./install.sh <agent>` 将新 skill 同步到对应 Agent

## 设计原则

- **单一入口**：每个 skill 只有一个 `SKILL.md`，降低维护成本
- **无外部强依赖**：优先使用标准库或系统自带工具
- **脚本自解释**：所有 Python 脚本均内置 `--help`
- **配置分层**：支持 CLI > 环境变量 > 项目配置 > 全局配置的优先级链
