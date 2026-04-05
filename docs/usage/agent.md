# spark agent — AI Agent 配置管理 (已禁用)

> ⚠️ 此功能当前已禁用，命令入口已关闭。待后续重新设计后再启用。

管理多种 AI Agent 的配置文件（Claude Code、Codex、Kimi、GLM）。

## 命令速查

```bash
# 基本操作
spark agent list                              # 列出所有支持的 Agent
spark agent view <agent>                      # 查看配置
spark agent edit <agent> [index]              # 编辑配置
spark agent reset <agent>                     # 重置配置

# Profile 管理
spark agent profile list                      # 列出所有 profile
spark agent profile add <name> -t <type>      # 添加 profile
spark agent profile show <name>               # 查看 profile 配置
spark agent profile edit <name> [index]       # 编辑 profile

# 应用 Profile
spark agent use <profile> [-p <dir>]          # 应用 profile 到项目
spark agent current [-p <dir>]                # 查看当前 profile
```

支持的 Agent: `claude-code`, `codex`, `kimi`, `glm`

---

## 基本操作

### spark agent list

列出所有支持的 AI Agent 及其配置文件位置。

```bash
spark agent list                              # 列出所有 Agent
spark agent list --tui                        # 交互模式
```

### spark agent view

查看指定 Agent 的配置文件内容。

```bash
spark agent view claude-code                  # 查看 Claude Code 配置
spark agent view kimi                         # 查看 Kimi 配置
spark agent view glm                          # 查看 GLM 配置
spark agent view codex                        # 查看 Codex 配置
```

### spark agent edit

使用默认编辑器打开 Agent 配置文件。

```bash
spark agent edit claude-code                  # 编辑第一个配置文件
spark agent edit claude-code 0                # 编辑指定索引的配置文件
```

### spark agent reset

重置 Agent 的配置文件。

```bash
spark agent reset claude-code                 # 重置 Claude Code 配置
```

---

## Profile 管理

Profile 是配置模板，用于在不同项目间快速切换 Agent 配置。

### spark agent profile add

创建新的配置 Profile。

| 标志 | 简写 | 说明 |
|------|------|------|
| `--type` | `-t` | Agent 类型（必填） |

```bash
spark agent profile add my-claude -t claude-code   # 创建 Claude Code profile
spark agent profile add my-glm -t glm              # 创建 GLM profile
```

### spark agent profile show

查看 Profile 的配置内容。

```bash
spark agent profile show my-claude
```

### spark agent profile edit

编辑 Profile 的配置文件。

```bash
spark agent profile edit my-claude
spark agent profile edit my-claude 0               # 编辑指定索引
```

### spark agent use

将 Profile 应用到当前项目。

| 标志 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--project` | `-p` | `.` | 项目目录 |

```bash
spark agent use my-claude                     # 应用到当前目录
spark agent use my-claude -p /path/to/project # 应用到指定项目
```

### spark agent current

查看当前项目使用的 Profile。

```bash
spark agent current                           # 当前目录
spark agent current -p /path/to/project       # 指定项目
```

## 相关命令

- [Git 管理](./git.md)
- [任务管理](./task.md)
