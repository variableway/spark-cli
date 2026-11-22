# spark hub — 项目 Hub

`spark hub` 有两条互不替代的路径：

| 路径 | 管什么 | 产物 |
|------|--------|------|
| `registry` | references 目录里的仓库，按清单克隆回来 | `registry_<folder>.yaml` |
| `collections` | 自己开发的 app 的注册信息 | `registry/apps.json` |

多仓库目录用 registry，不用 git submodule。

## 命令速查

```bash
# references
spark hub registry scan [folder-name]
spark hub registry scan [folder-name] --json
spark hub registry list -f registry_<folder>.yaml
spark hub registry clone -f registry_<folder>.yaml
spark hub registry clone -r <name> -f registry_<folder>.yaml
spark hub registry clone-registry <registry-file>

# 自己开发的 app
spark hub collections scan [path]
spark hub collections scan . -o registry/apps.json --merge registry/apps.json
```

---

## spark hub registry

管理一个 references 目录。扫描把带 `origin` 的 Git 仓库写入当前目录的 `registry_<folder>.yaml`；`list` 查看；`clone` / `clone-registry` 按记录的 `path` 克隆。

目录约定为三层：`<分类>/<子分类>/<项目>`。分类取自一级子目录（空目录也会入册），每个分类恒有 `others` 子分类。直接放在分类下的项目归入 `others`。没有任何一级分类目录时回退旧的扁平 `projects:` 格式。直接放在扫描根目录的仓库会打印 `WARNING`，不写入 registry。

```bash
spark hub registry scan ~/workspace/innate-references
spark hub registry scan ~/workspace/innate-references --json
spark hub registry list -f registry_innate-references.yaml
spark hub registry clone -f registry_innate-references.yaml
spark hub registry clone-registry ~/innate/base/innate-skills/registry_references.yaml --dry-run
```

| 命令 | 标志 | 说明 |
|------|------|------|
| `scan` | `--json` | 额外写出格式化的 `registry_<folder>.json` |
| `scan` | `--flatten` | 仅旧两层布局：扫描前把超过两层的仓库上移。三分层目录不要用 |
| `list` | `-f, --file` | registry 文件（必填） |
| `clone` | `-f, --file` | registry 文件（必填） |
| `clone` | `-r, --repo` | 只克隆指定名称 |
| `clone` | `--depth` | 浅克隆深度，`0` 为完整历史 |
| `clone-registry` | `--out` | 目标目录，默认由 registry 文件位置和名称推导 |
| `clone-registry` | `--dry-run` | 只打印计划 |
| `clone-registry` | `--depth` | 浅克隆深度，`0` 为完整历史 |

重复扫描会合并已有 registry：按 `path`、其次按仓库 URL 匹配，保留 `name` / `desc`。本地没有检出的旧条目原样保留，registry 同时是恢复记录。删除条目要手工改文件。

`clone` 的目标目录名由文件名推导（`registry_<folder>.yaml` → `<folder>`），已存在的目录跳过。`clone-registry` 只克隆磁盘上还没有的条目，目标默认在 registry 文件旁边。

扫描跳过隐藏目录以及 `node_modules` / `venv` / `.venv` / `__pycache__` / `dist` / `build`。SSH URL 存成 HTTPS。

### registry 文件

```yaml
# Project registry
# Synced by spark hub registry scan

version: 2
categories:
  - name: skills
    subcategories:
      - name: agent
        projects:
          - name: taste-skill
            repo: https://github.com/Leonxlnx/taste-skill.git
            path: skills/agent/taste-skill
      - name: others
        projects: []
```

---

## spark hub collections scan

登记自己开发的 app。扫描本地 Git 仓库，用 GitHub API 补上 description、language、visibility，写成 innate-apps collections 目录。

默认只扫顶层。`--deep` 包含嵌套仓库。

```bash
spark hub collections scan /path/to/innate-apps
spark hub collections scan . -o registry/apps.json --merge registry/apps.json
spark hub collections scan . --skip-api --category app
```

| 标志 | 说明 |
|------|------|
| `-o, --output` | 输出文件。默认 stdout；只给 `--merge` 时写回该文件 |
| `--merge` | 与已有目录合并，保留手工字段 |
| `--skip-api` | 不调用 GitHub API |
| `--deep` | 包含嵌套仓库 |
| `--category` | 新条目的分类：`base` / `app` / `reference` |

`--merge` 保留 `title`、`category`、`status`、`url`、`description`，刷新 `repo`、`local_path`、`visibility`、`language`。这次扫描没看到的旧条目原样保留。设置 `GITHUB_TOKEN` 可提高 API 速率限制。

```json
{
  "$schema": "./schema.json",
  "version": 1,
  "updated_at": "2026-11-01",
  "collections": [
    {
      "name": "spark-cli",
      "title": "Spark CLI",
      "repo": "variableway/spark-cli",
      "url": "https://github.com/variableway/spark-cli",
      "local_path": "spark-cli",
      "category": "app",
      "status": "maintained",
      "visibility": "public",
      "language": "Go",
      "description": "Daily Cli command ideas fired by spark"
    }
  ]
}
```

改完 `registry/apps.json` 后，README 和 profile 里的项目清单要用 `spark git update-org-status` 另行刷新。字段定义见 `registry/schema.json`。
