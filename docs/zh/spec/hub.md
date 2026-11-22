# spark hub — 命令规格

项目 Hub。`registry` 管理 references 目录，`collections` 登记自己开发的 app。两者产物不同，不能互相替代。

## 父命令

```
spark hub
```

```
spark hub registry
spark hub collections
```

无参数，无标志。

---

## spark hub registry scan

递归扫描目录中带 `origin` 的 Git 仓库，写入当前目录的 `registry_<folder>.yaml`。

```
spark hub registry scan [folder-name] [--json] [--flatten]
```

| 参数 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `folder-name` | string | `.` | 否 | 要扫描的目录 |

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--json` | bool | `false` | 否 | 额外写出 `registry_<folder>.json` |
| `--flatten` | bool | `false` | 否 | 仅旧两层布局：扫描前上移超过两层的仓库。三分层目录禁用 |

**行为**：跳过隐藏目录和 `node_modules` / `venv` / `.venv` / `__pycache__` / `dist` / `build`。SSH URL 存成 HTTPS。与已有 registry 按 `path`、其次按 URL 合并，保留 `name` / `desc`，本地缺失的旧条目原样保留。有一级分类目录时写成 version 2（`<分类>/<子分类>/others`）；没有则写成扁平 `projects:`。根目录上的仓库打印 WARNING 且不入册。

---

## spark hub registry list

```
spark hub registry list -f <registry-file>
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `-f, --file` | string | | 是 | registry 文件 |

分类格式先打印 `# <分类> / <子分类> (n)`，然后每行 `name<TAB>repo<TAB>path`。空 registry 打印 `No repositories in registry.`

---

## spark hub registry clone

```
spark hub registry clone [-r <name>] -f <registry-file> [--depth <n>]
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `-f, --file` | string | | 是 | registry 文件 |
| `-r, --repo` | string | | 否 | 只克隆该名称 |
| `--depth` | int | `0` | 否 | `git clone --depth=N`；0 为完整历史 |

目标目录名由 `registry_<folder>.yaml` 推导为 `<folder>`。已有 `.git` 或目录已存在则 SKIP。按 path 从浅到深克隆。`failed > 0` 时返回错误。

---

## spark hub registry clone-registry

```
spark hub registry clone-registry <registry-file> [--out <folder>] [--dry-run] [--depth <n>]
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `registry-file` | string | 是 | registry 文件 |

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `--out` | string | 由文件位置与名称推导 | 否 | 目标目录 |
| `--dry-run` | bool | `false` | 否 | 只打印 `WOULD CLONE` |
| `--depth` | int | `0` | 否 | 浅克隆深度 |

先打印总数 / 在盘 / 缺失。已在盘的条目 SKIP，不重新克隆。

---

## spark hub collections scan

扫描自己开发的 app，写出 innate-apps collections 目录。默认只扫顶层。

```
spark hub collections scan [path] [-o <file>] [--merge <file>] [--skip-api] [--deep] [--category <name>]
```

| 参数 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `path` | string | `.` | 否 | 扫描根目录 |

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `-o, --output` | string | stdout | 否 | 输出文件。只给 `--merge` 时写回该文件 |
| `--merge` | string | | 否 | 合并已有目录，保留手工字段 |
| `--skip-api` | bool | `false` | 否 | 不调用 GitHub API |
| `--deep` | bool | `false` | 否 | 包含嵌套仓库 |
| `--category` | string | | 否 | 新条目分类：`base` / `app` / `reference` |

远程 URL 需为 GitHub 形式才会进入目录。API 失败时回退到本地信息。`--merge` 按 `name`、其次 `repo` 匹配；保留 `title` / `category` / `status` / `url` / `description`，刷新 `repo` / `local_path` / `visibility` / `language`，未扫到的旧条目原样保留。
