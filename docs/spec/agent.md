# spark agent — 命令规格

AI Agent 配置管理命令组。

支持的 Agent 类型：`claude-code`、`codex`、`kimi`、`glm`

## 父命令

```
spark agent [--tui]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--tui` | bool | `false` | 否 | 启用交互式 TUI 模式 |

---

## spark agent list

列出所有支持的 AI Agent 及其配置文件位置。

```
spark agent list [--tui]
```

无标志（除父命令 `--tui`）。无参数。

---

## spark agent view

查看指定 Agent 的配置文件内容。

```
spark agent view <agent>
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `agent` | string | 是 | Agent 类型：`claude-code`、`codex`、`kimi`、`glm` |

无标志。

---

## spark agent edit

使用默认编辑器打开 Agent 配置文件。

```
spark agent edit <agent> [config-index]
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `agent` | string | 是 | Agent 类型 |
| `config-index` | int | 否 | 配置文件索引，默认编辑第一个 |

无标志。

---

## spark agent reset

重置 Agent 的配置文件。

```
spark agent reset <agent>
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `agent` | string | 是 | Agent 类型 |

无标志。

---

## spark agent profile list

列出所有配置 Profile。

```
spark agent profile list
```

无标志，无参数。

---

## spark agent profile add

创建新的配置 Profile。

```
spark agent profile add <name> -t <type>
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `-t, --type` | string | | 否 | Agent 类型（`claude-code`、`codex`、`kimi`、`glm`） |

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | Profile 名称 |

---

## spark agent profile show

查看 Profile 的配置内容。

```
spark agent profile show <name>
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | Profile 名称 |

无标志。

---

## spark agent profile edit

编辑 Profile 的配置文件。

```
spark agent profile edit <name> [config-index]
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | Profile 名称 |
| `config-index` | int | 否 | 配置文件索引 |

无标志。

---

## spark agent use

将 Profile 应用到指定项目。

```
spark agent use <profile-name> [-p <dir>]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `-p, --project` | string | `.` | 否 | 项目目录 |

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `profile-name` | string | 是 | Profile 名称 |

---

## spark agent current

查看当前项目使用的 Profile。

```
spark agent current [-p <dir>]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `-p, --project` | string | `.` | 否 | 项目目录 |

无参数。
