# spark agent

管理多种 AI Agent 的配置文件。

## 概述

`agent` 命令用于查看、编辑和管理多种 AI Agent（如 Claude Code、OpenAI Codex、Kimi CLI、GLM）的配置文件。这简化了在不同 AI 工具之间切换和配置的过程。

## 支持的 Agent

| Agent | 名称 | 配置文件 |
|-------|------|----------|
| `claude-code` | Claude Code | `~/.claude.json`, `~/.claude/settings.json`, `~/.claude/settings.local.json` |
| `codex` | OpenAI Codex | `~/.codex/config.toml` |
| `kimi` | Kimi CLI | `~/.kimi/config.toml` |
| `glm` | GLM (智谱 AI) | `~/.claude.json`, `~/.claude/settings.json` |

## 使用方法

```bash
spark agent [command]
```

## 子命令

### `agent list`

列出所有支持的 AI Agent 及其配置状态。

```bash
spark agent list
```

**输出示例**:

```
╔══════════════════════════════════════════════════════════════════╗
║                    Supported AI Agents                           ║
╚══════════════════════════════════════════════════════════════════╝

Agent         Display Name     Config Files                    Status
claude-code   Claude Code      .claude.json                    ✅ Configured
                               .claude/settings.json
                               .claude/settings.local.json
codex         OpenAI Codex     .codex/config.toml              ❌ Not configured
kimi          Kimi CLI         .kimi/config.toml               ✅ Configured
glm           GLM (Zhipu AI)   .claude.json                    ❌ Not configured
                               .claude/settings.json
```

### `agent view`

查看指定 Agent 的配置文件内容。

```bash
spark agent view <agent>
```

**示例**:

```bash
spark agent view claude-code
spark agent view kimi
```

**输出示例**:

```
╔══════════════════════════════════════════════════════════════════╗
║                  Claude Code Configuration                       ║
╚══════════════════════════════════════════════════════════════════╝

File: /Users/you/.claude.json
────────────────────────────────────────────────────────────────────
{
  "api_key": "your-api-key",
  "model": "claude-3-opus-20240229"
}
```

### `agent edit`

编辑指定 Agent 的配置文件。

```bash
spark agent edit <agent> [config-index] [flags]
```

**参数**:

| 参数 | 说明 |
|------|------|
| `agent` | Agent 名称 |
| `config-index` | 配置文件索引（可选，从 0 开始） |

**标志**:

| 标志 | 说明 |
|------|------|
| `--tui` | 使用交互式终端 UI 选择配置文件 |

**示例**:

```bash
# 编辑第一个配置文件
spark agent edit claude-code

# 编辑指定索引的配置文件
spark agent edit claude-code 1

# 使用 TUI 选择要编辑的配置文件
spark agent edit claude-code --tui
```

**编辑器选择**:

编辑器由 `$EDITOR` 环境变量决定：
- 如果设置了 `$EDITOR`，使用该编辑器
- macOS/Linux 默认使用 `vim`
- Windows 默认使用 `notepad`

## 标志

| 标志 | 适用命令 | 说明 |
|------|----------|------|
| `--tui` | `edit` | 启用交互式终端 UI |

## Profile 配置模板管理

除了全局配置，`agent` 命令还支持 **Profile (配置模板)** 管理。这允许你在不同的项目中使用不同的 Agent 配置（例如在项目 A 中使用 Claude Opus，在项目 B 中使用 GLM-4）。

### `agent profile list`

列出所有已创建的配置模板。

```bash
spark agent profile list
```

### `agent profile add`

创建一个新的配置模板。

```bash
spark agent profile add <name> --type <agent-type>
```

**示例**:

```bash
# 创建一个名为 my-glm 的模板，类型为 glm
spark agent profile add my-glm --type glm

# 创建一个名为 claude-opus 的模板，类型为 claude-code
spark agent profile add claude-opus --type claude-code
```

### `agent profile edit`

编辑配置模板的内容。

```bash
spark agent profile edit <name> [config-index]
```

### `agent use`

将指定的配置模板应用到当前项目。这会将模板中的配置文件复制到当前项目目录下。

```bash
spark agent use <profile-name> [--project <path>]
```

**示例**:

```bash
cd my-project
spark agent use my-glm
```

### `agent current`

查看当前项目正在使用的配置模板。

```bash
spark agent current [--project <path>]
```

## 完整示例

### 查看所有 Agent 状态

```bash
spark agent list
```

### 查看并编辑 Claude Code 配置

```bash
# 查看当前配置
spark agent view claude-code

# 编辑配置
spark agent edit claude-code --tui
```

### 在不同项目中使用不同模型

```bash
# 1. 创建两个配置模板
spark agent profile add my-claude --type claude-code
spark agent profile add my-glm --type glm

# 2. 分别编辑它们的配置
spark agent profile edit my-claude
spark agent profile edit my-glm

# 3. 在项目 A 中使用 Claude
cd ~/workspace/project-a
spark agent use my-claude

# 4. 在项目 B 中使用 GLM
cd ~/workspace/project-b
spark agent use my-glm
```

### 配置新的 AI Agent

```bash
# 查看需要配置的文件
spark agent view kimi

# 创建/编辑配置文件
spark agent edit kimi
```

## 配置文件格式

### Claude Code (`~/.claude.json`)

```json
{
  "api_key": "your-api-key",
  "model": "claude-3-opus-20240229"
}
```

### Codex / Kimi (TOML 格式)

```toml
api_key = "your-api-key"
model = "gpt-4"
```

## 故障排除

### 配置文件不存在

如果配置文件不存在，`view` 命令会报错。使用 `edit` 命令会自动创建目录和文件。

### 权限问题

确保有权限访问 `~` 目录下的配置文件。

### 编辑器问题

如果编辑器无法启动，检查 `$EDITOR` 环境变量：

```bash
echo $EDITOR
export EDITOR=nano  # 或其他编辑器
```
