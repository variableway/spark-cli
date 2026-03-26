# AI Agent Configuration Management

## Status: ✅ Implemented

## 功能描述

实现一个可以管理不同 AI Agent 配置管理的 CLI 工具。

## 支持的 AI Agent

| Agent | 配置文件位置 |
|-------|-------------|
| **Claude Code** | `~/.claude.json`, `~/.claude/settings.json`, `~/.claude/settings.local.json` |
| **OpenAI Codex** | `~/.codex/config.toml` |
| **Kimi CLI** | `~/.kimi/config.toml` |
| **GLM (Zhipu AI)** | `~/.claude.json`, `~/.claude/settings.json` |

## 使用方法

### 列出所有支持的 AI Agent

```bash
monolize agent list
```

### 查看配置

```bash
# 查看 Claude Code 配置
monolize agent view claude-code

# 查看 Kimi CLI 配置
monolize agent view kimi

# 查看 GLM 配置
monolize agent view glm

# 查看 Codex 配置
monolize agent view codex
```

### 修改配置

```bash
# 使用默认编辑器打开配置文件
monolize agent edit claude-code

# 指定配置文件索引
monolize agent edit claude-code 0  # 编辑第一个配置文件
monolize agent edit claude-code 1  # 编辑第二个配置文件

# TUI 交互模式选择配置文件
monolize agent edit claude-code --tui
```

### 重置配置

```bash
# 重置配置（会备份原文件为 .bak）
monolize agent reset claude-code

# TUI 交互模式确认
monolize agent reset claude-code --tui
```

## TUI 模式

所有命令都支持 `--tui` 标志启用交互式终端界面：

```bash
monolize agent edit claude-code --tui   # 交互式选择配置文件
monolize agent reset claude-code --tui  # 交互式确认重置
```

## 实现文件

| 文件 | 描述 |
|------|------|
| [internal/agent/agent.go](../../internal/agent/agent.go) | Agent 配置管理核心逻辑 |
| [cmd/agent.go](../../cmd/agent.go) | CLI 命令定义 |
