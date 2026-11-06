# Skill 管理

## 功能概述

`spark skill` 负责发现、列出并同步 AI agent 的 skill。一个 skill 就是**一个包含
`SKILL.md` 的目录**——`SKILL.md` 顶部用 YAML frontmatter 声明 `name` 与 `description`，
正文写使用说明。

## 核心能力

### 多位置发现

一次扫描覆盖项目级、全局与内置三档位置：

```bash
spark skill list
```

| 档位 | 位置 |
|------|------|
| 项目级 | `.mimocode/skills/`、`.mimocode/skill/`、`.agents/skills/` |
| 全局 | `~/.claude/skills/`、`~/.agents/skills/`、`~/.mimocode/skills/`、`~/.mimocode/skill/` |
| 内置 | `~/.local/share/mimocode/builtin_skills/<version>/skills/` |

同名 skill 只保留优先级最高的一个：**项目级 > 全局 > 内置**；内置多版本时取最新版本。
列表会标出每个 skill 的来源与完整路径。

### 结构化输出

```bash
spark skill list --json
```

输出 JSON 数组（`name` / `description` / `path` / `source`），可直接喂给脚本。

### 一键汇总同步

把散落在各处的 skill 汇总到一个目录，便于集中管理或二次加工：

```bash
spark skill sync ./skills            # 汇总复制
spark skill sync ./skills --clear    # 先清空目标目录再复制
```

复制后目录结构为 `<target-dir>/<skill-name>/SKILL.md`。
`--clear` 会**删除目标目录现有内容**，执行前请确认目标路径无误。

## 使用参数

| 命令 | 参数 | 说明 |
|------|------|------|
| `list` | `[--json]` | 列出发现的 skill |
| `sync` | `<target-dir> [--clear]` | 复制所有 skill 到目标目录 |

## 典型场景

| 场景 | 做法 |
|------|------|
| 看看本机装了哪些 skill | `spark skill list` |
| 把项目级 skill 导出成仓库 | `spark skill sync ./skills` |
| 把内置 skill 拷到项目里改 | `spark skill sync ./.agents/skills` |
| 校验某个 skill 是否被识别 | `spark skill list --json \| grep <name>` |

## 相关文档

- [Skill 命令规格](../spec/skill.md)
- [Skill 使用说明](../usage/skill.md)
