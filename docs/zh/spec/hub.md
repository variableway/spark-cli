# spark hub — 命令规格

项目 Hub 命令组。扫描本地 Git 仓库并输出 innate-apps registry 格式的注册信息。

## 父命令

```
spark hub
```

无参数，无标志。

---

## spark hub scan

扫描目录中的 Git 仓库（**默认只扫顶层**），转换为 registry 条目。

```
spark hub scan [path] [-o <file>] [--merge <file>] [--skip-api] [--deep] [--category <name>]
```

| 标志 | 简写 | 类型 | 默认值 | 必填 | 说明 |
|------|------|------|--------|------|------|
| `--output` | `-o` | string | stdout | 否 | 输出文件路径 |
| `--merge` | | string | | 否 | 与已有注册文件合并，保留手工字段 |
| `--skip-api` | | bool | `false` | 否 | 跳过 GitHub API，只用本地 git 信息 |
| `--deep` | | bool | `false` | 否 | 包含嵌套仓库（默认只扫顶层） |
| `--category` | | string | | 否 | 为新发现条目设置分类 |

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `path` | string | 否 | 扫描根目录，默认 `.` |

### 扫描行为

- 查找带 `origin` 远程的 Git 仓库（含 `.git` 目录与 `.git` 文件两种形态）；默认只取顶层，`--deep` 改为不限深度
- 默认**只取顶层**的仓库；`--deep` 改为不限深度
- 跳过隐藏目录以及 `node_modules` / `venv` / `.venv` / `__pycache__` / `dist` / `build`
- 远程 URL 需为 GitHub 形式（`https://github.com/<owner>/<repo>.git` 或
  `git@github.com:<owner>/<repo>.git`）才会进入注册表
- `--skip-api` 为真时不调用 GitHub API，条目只含本地可推断的字段
- API 调用失败时**自动回退**到本地信息：该条目没有 `language` 与 `description`，
  `visibility` 仍为 `public`

设置 `GITHUB_TOKEN` 可提高 API 速率限制。

### 输出格式

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

| 字段 | 来源 |
|------|------|
| `$schema` | 固定 `./schema.json` |
| `version` | 固定 `1` |
| `updated_at` | 写入日期，格式 `2006-01-02` |
| `name` | GitHub 仓库名（远程 URL 里的 slug） |
| `title` | GitHub description；为空时由目录名人性化得到（`my-app` → `My App`） |
| `repo` | `origin` 解析出的 `owner/repo` |
| `url` | GitHub homepage；为空时用仓库 URL |
| `local_path` | 相对扫描根目录的路径（统一为 `/` 分隔） |
| `category` | 默认 `app`；`--category` 可覆盖 |
| `status` | 默认 `maintained` |
| `visibility` | GitHub API：`private` → `private`，否则 `public` |
| `language` | GitHub API 主语言 |
| `description` | GitHub API 描述 |

分类取值：`base` / `app` / `reference`。
状态取值：`maintained` / `archived` / `experimental`。

### 合并行为

`--merge <file>` 指定已有注册文件时：

- **保留手工字段**：`title`、`category`、`status`、`url`、`description`
- **刷新自动字段**：`repo`、`local_path`、`visibility`、`language`
- **保留未匹配条目**：扫描中没发现的已有条目原样保留（例如 `../base/` 下的基础框架）
- **追加新发现**：新扫到的仓库自动加入

匹配顺序：先按 `name`，再按 `repo`。

### 输出位置

- 同时给 `-o` 和 `--merge` 时，写入 `-o` 指定的文件
- 只给 `--merge` 时，写回该文件本身
- 都不给时输出到 stdout

写入文件时打印 `Wrote N collection(s) to <path>`。
