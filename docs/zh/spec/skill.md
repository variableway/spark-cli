# spark skill — 命令规格

AI Skill 管理命令组。用于发现、列出并同步 `SKILL.md` 目录。

## 父命令

```
spark skill
```

无参数，无标志。

---

## spark skill list

扫描所有已知位置，列出发现的 skill。

```
spark skill list [--json]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--json` | bool | `false` | 否 | 以 JSON 输出，便于脚本处理 |

无参数。

### 发现位置与来源标签

按下列顺序扫描，来源标签即列表中的 `source` 列：

| 顺序 | 位置 | `source` |
|------|------|----------|
| 1 | `<cwd>/.mimocode/skills/` | `project` |
| 2 | `<cwd>/.mimocode/skill/` | `project` |
| 3 | `<cwd>/.agents/skills/` | `project` |
| 4 | `~/.claude/skills/` | `claude` |
| 5 | `~/.agents/skills/` | `global` |
| 6 | `~/.mimocode/skills/` | `global` |
| 7 | `~/.mimocode/skill/` | `global` |
| 8 | `~/.local/share/mimocode/builtin_skills/<version>/skills/` | `builtin:<version>` |

- 每个目录下的一级子目录即一个 skill，需包含 `SKILL.md`
- builtin 目录按版本号倒序扫描，多个版本时**最新版本优先**
- **同名去重**：先到先得，因此扫描顺序即优先级（项目级 > 全局 > builtin）
- 目录不存在时跳过，不报错

### 名称与描述解析

读取 `SKILL.md` 的 YAML frontmatter：

- `name`：缺省时使用目录名
- `description`：可缺省

### 输出

文本输出为三列表格（`NAME` / `SOURCE` / `PATH`），描述过长时截断到 60 字符。
一个 skill 都没找到时打印 `No skills found.` 并列出搜索位置。

`--json` 输出为 JSON 数组：

```json
[
  {
    "name": "spark-cli",
    "description": "spark 命令行工具的使用说明",
    "path": "/Users/me/.claude/skills/spark-cli",
    "source": "claude"
  }
]
```

---

## spark skill sync

把发现的 skill 复制到目标目录。

```
spark skill sync <target-dir> [--clear]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--clear` | bool | `false` | 否 | 复制前清空目标目录 |

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `target-dir` | string | 是 | 目标目录 |

行为：

1. 扫描并去重（同 `list`）
2. 一个 skill 都没有时打印 `No skills found to sync.` 并直接返回，不创建目录
3. `--clear` 时先清空目标目录
4. 每个 skill 复制为 `<target-dir>/<skill-name>/`
5. 结束后打印复制数量与每个目标路径

无 skill 被复制时目标目录可能尚未创建。
