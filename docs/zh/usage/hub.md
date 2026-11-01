# spark hub — 项目 Hub（Collections 注册）

扫描本地 Git 仓库并生成 innate-apps registry 格式（`registry/apps.json`）的项目注册信息。

## 命令速查

```bash
spark hub scan <path>                              # 扫描目录，输出 JSON 到 stdout
spark hub scan <path> -o registry/apps.json        # 输出到文件
spark hub scan <path> --merge registry/apps.json   # 合并已有注册文件
spark hub scan <path> --skip-api                   # 跳过 GitHub API，仅用本地信息
spark hub scan <path> --deep                       # 包含嵌套仓库
spark hub scan <path> --category reference          # 指定分类
```

---

## 输出格式

输出为 innate-apps registry 格式，字段定义见 `registry/schema.json`：

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
| `name` | 目录名 |
| `title` | GitHub description（或人名化目录名） |
| `repo` | git origin 解析出的 `owner/repo` |
| `url` | GitHub homepage（或仓库 URL） |
| `local_path` | 相对扫描根的路径 |
| `category` | 默认 `app`（可用 `--category` 覆盖） |
| `status` | 默认 `maintained` |
| `visibility` | GitHub API（`private` → `private`） |
| `language` | GitHub API 主语言 |
| `description` | GitHub API 描述 |

---

## spark hub scan

递归扫描目录中的 Git 仓库（带 `origin` 远程），调用 GitHub API 获取元数据，转化为注册信息。

```bash
spark hub scan /path/to/innate-apps
spark hub scan . -o registry/apps.json --merge registry/apps.json
```

| 选项 | 说明 |
|------|------|
| `-o, --output` | 输出文件路径（默认 stdout） |
| `--merge` | 与已有注册文件合并，保留手工字段 |
| `--skip-api` | 跳过 GitHub API，仅用本地 git 信息 |
| `--deep` | 包含嵌套仓库（默认仅扫描顶层目录） |
| `--category` | 为新发现条目设置分类（`base`/`app`/`reference`） |

### 合并行为

使用 `--merge` 时：

- **保留手工字段**：`title`、`category`、`status`、`url`、`description`
- **刷新自动字段**：`repo`、`local_path`、`visibility`、`language`
- **保留未匹配条目**：扫描中未发现的已有条目（如 `../base/` 下的基础框架）原样保留
- **追加新发现**：扫描到的新仓库自动加入

### GitHub API

设置 `GITHUB_TOKEN` 环境变量可提升 API 速率限制。API 调用失败时自动回退到本地 git 信息（不带 `language`/`description`/`visibility`）。
