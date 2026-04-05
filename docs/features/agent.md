# AI Agent 配置管理

## 功能概述

`spark agent` 统一管理多种 AI Agent（Claude Code、Codex、Kimi、GLM）的配置文件。通过 Profile 模板机制，可以在不同项目间快速切换 Agent 配置。

## 支持的 Agent

| Agent | 配置文件 |
|-------|---------|
| Claude Code | `CLAUDE.md`、`.claude/settings.json` 等 |
| Codex | `AGENTS.md`、codex 配置 |
| Kimi | `.kimi/` 目录下的配置 |
| GLM | `.glm/` 目录下的配置 |

## 核心能力

### 配置查看与编辑

查看、编辑、重置各 Agent 的配置文件，无需记忆文件路径。

```bash
spark agent list                    # 列出所有 Agent
spark agent view claude-code        # 查看配置
spark agent edit kimi               # 编辑配置
spark agent reset glm               # 重置配置
```

### Profile 模板

Profile 是配置模板，保存了特定 Agent 的完整配置。可以为不同项目或工作模式创建不同 Profile。

```bash
# 创建 Profile
spark agent profile add my-claude -t claude-code
spark agent profile add my-glm -t glm

# 查看 Profile
spark agent profile show my-claude
spark agent profile edit my-claude
```

### 跨项目应用

将 Profile 应用到指定项目，自动创建或覆盖对应的配置文件。

```bash
spark agent use my-claude                    # 应用到当前目录
spark agent use my-claude -p /path/to/proj   # 应用到指定项目
spark agent current                          # 查看当前 Profile
```

## 使用参数

| 参数 | 说明 |
|------|------|
| `--tui` | 交互式选择模式 |
| `-t, --type` | Profile 的 Agent 类型 |
| `-p, --project` | 目标项目路径，默认 `.` |

## 相关文档

- [Agent 命令规格](../spec/agent.md)
- [Agent 使用指南](../usage/agent.md)
