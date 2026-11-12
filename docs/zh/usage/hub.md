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

输出为 innate-apps registry 格式，字段定义见 innate-apps 仓库里的 `registry/schema.json`：

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
| `name` | GitHub 仓库名（远程 URL 里的 slug） |
| `title` | GitHub description（为空时用仓库名人名化，如 `my-app` → `My App`） |
| `repo` | git origin 解析出的 `owner/repo` |
| `url` | GitHub homepage（或仓库 URL） |
| `local_path` | 相对扫描根的路径 |
| `category` | 默认 `app`（可用 `--category` 覆盖） |
| `status` | 默认 `maintained` |
| `visibility` | GitHub API（`private` → `private`，否则 `public`） |
| `language` | GitHub API 主语言 |
| `description` | GitHub API 描述 |

---

## spark hub scan

扫描目录中的 Git 仓库（带 `origin` 远程），调用 GitHub API 获取元数据，转化为注册信息。

**默认只扫描顶层目录**；要包含嵌套仓库请加 `--deep`。

```bash
spark hub scan /path/to/innate-apps
spark hub scan . -o registry/apps.json --merge registry/apps.json
```

| 选项 | 说明 |
|------|------|
| `-o, --output` | 输出文件路径（默认 stdout；配合 `--merge` 且不给 `-o` 时，写回合并的那个文件） |
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

设置 `GITHUB_TOKEN` 环境变量可提升 API 速率限制。API 调用失败时自动回退到本地 git 信息：此时 `language` 与 `description` 为空，`visibility` 仍为 `public`。

---

## 与「获取 GitHub 仓库项目」的关系

同样是「拿到 GitHub 上的项目列表」，有三条路径，产物不同：

| 路径 | 产物 | 适用 |
|------|------|------|
| `spark git update-org-status <account>` | README 里的项目清单段落 | 直接贴到 README / profile 仓库 |
| `gh repo list` / `gh api` | 原始仓库列表 | 自己渲染成任意格式 |
| `spark hub scan` | 带分类与状态的注册表 JSON | 维护项目聚合站 |

详见 [Git 管理 · 如何获取 GitHub 仓库项目列表](./git.md)。

---

## 典型用法：维护 innate-apps 注册表

`registry/apps.json` 是 innate-apps 项目的**数据源**，README 与 profile 仓库里的
项目段落是它的**渲染产物**。改完数据源要同步刷新渲染产物：

```bash
# 1. 在 innate-apps 目录里扫描，合并回注册表（保留手工维护的 title/category/status）
spark hub scan . -o registry/apps.json --merge registry/apps.json

# 2. 提交后刷新下游渲染产物
#    - innate-apps 自身的 README 项目清单
#    - 用户 profile 仓库 qdriven/qdriven 里的项目段落
#    - 组织 profile 仓库 variableway/.github 里的项目清单
spark git update-org-status variableway --update-dot-github
```

字段定义见 `registry/schema.json`，约定见 `registry/README.md`。
