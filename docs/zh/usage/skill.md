# spark skill — AI Skill 管理

查找、列出并同步 AI agent skills（`SKILL.md` 目录）。

## 命令速查

```bash
spark skill list                    # 列出所有发现的 skill
spark skill list --json             # JSON 输出
spark skill sync <target-dir>       # 复制所有 skill 到目标目录
spark skill sync <target-dir> --clear  # 清空目标目录后复制
```

---

## Skill 发现位置

`spark skill` 从以下已知位置扫描包含 `SKILL.md` 的目录：

| 位置 | 来源标签 |
|------|----------|
| `.mimocode/skills/`、`.mimocode/skill/`（当前项目） | `project` |
| `.agents/skills/`（当前项目） | `project` |
| `~/.claude/skills/` | `claude` |
| `~/.agents/skills/`、`~/.mimocode/skills/`、`~/.mimocode/skill/` | `global` |
| `~/.local/share/mimocode/builtin_skills/<version>/skills/` | `builtin:<version>` |

按 skill 名称去重：项目级优先于全局，全局优先于 builtin；builtin 多版本时最新版本优先。

---

## spark skill list

扫描所有位置并列出发现的 skill。

```bash
spark skill list
spark skill list --json
```

输出包含 skill 名称、来源与路径。`--json` 输出结构化 JSON，便于脚本处理。

SKILL.md 的 YAML frontmatter 中的 `name` 与 `description` 会被解析；缺少 frontmatter 时使用目录名。

---

## spark skill sync

把所有发现的 skill 复制到指定目录。

```bash
spark skill sync ./skills               # 复制到 ./skills
spark skill sync ./skills --clear       # 先清空 ./skills 再复制
spark skill sync ~/.claude/skills       # 同步到 Claude skills 目录
```

| 选项 | 说明 |
|------|------|
| `--clear` | 复制前清空目标目录 |

典型用法：汇总分散在各处的 skill 到一个目录（例如 `fire-skills` 仓库），或把 builtin skill 复制到项目本地以供自定义修改。

---

## 本仓库自带的 spark-cli Skill

`skills/spark-cli/SKILL.md` 是本仓库自带的一份 skill，内容就是**这份使用说明的
Agent 版**：命令地图、常用工作流、以及「如何获取 GitHub 仓库项目列表」的三条路径。
安装到你的 agent 技能目录即可让助手直接会用 spark：

```bash
# 从本仓库安装到 Claude 的 skills 目录
spark skill sync ~/.claude/skills --clear

# 或者只安装这一个
mkdir -p ~/.claude/skills/spark-cli
cp skills/spark-cli/SKILL.md ~/.claude/skills/spark-cli/
```

安装后 `spark skill list` 就能看到它：

```text
NAME                   SOURCE           PATH
spark-cli              claude           /Users/me/.claude/skills/spark-cli
```

> 技能目录约定：每个 skill 是一个**目录**，目录里放 `SKILL.md`；
> frontmatter 里的 `name` 与 `description` 决定它何时被助手触发。
