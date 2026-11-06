# 项目 Hub

## 功能概述

`spark hub` 把本地的一堆 Git 仓库转成**项目注册表**（registry），也就是一份
JSON 格式的项目清单：每个项目是谁、在 GitHub 上的地址、分类、状态、可见性、
主语言。它替代了用 git submodule 管理多个项目的做法——注册表是**数据文件**，
可版本化、可评审、可被文档站消费。

## 核心能力

### 扫描本地仓库生成注册表

```bash
spark hub scan .
spark hub scan . -o registry/apps.json
```

扫描会找出带 `origin` 远程的 Git 仓库，调用 GitHub API 补齐 description /
language / visibility，再输出 innate-apps registry 格式（字段定义见
`registry/schema.json`）。

默认只扫顶层目录，`--deep` 可包含嵌套仓库。

### 合并时保留人工维护的字段

```bash
spark hub scan . -o registry/apps.json --merge registry/apps.json
```

| 字段 | 合并策略 |
|------|----------|
| `title` / `category` / `status` / `url` / `description` | **保留**已有注册文件里的手工值 |
| `repo` / `local_path` / `visibility` / `language` | **刷新**为本次扫描结果 |
| 未被扫到的条目 | 原样保留（如 `../base/` 下的基础框架） |
| 新扫到的仓库 | 追加进列表 |

### 离线模式

```bash
spark hub scan . --skip-api
```

不调用 GitHub API，只用本地 git 信息推导条目；API 调用失败时也会自动回退到
本地信息（该条目不带 `language` / `description`）。

## 使用参数

| 命令 | 参数 | 说明 |
|------|------|------|
| `scan` | `[path]` | 扫描根目录，默认 `.` |
| `scan` | `-o, --output <file>` | 输出文件，默认 stdout |
| `scan` | `--merge <file>` | 与已有注册文件合并 |
| `scan` | `--skip-api` | 跳过 GitHub API |
| `scan` | `--deep` | 包含嵌套仓库 |
| `scan` | `--category <name>` | 设置分类：`base` / `app` / `reference` |

## 输出结构

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

分类：`base`（基础框架）/ `app`（应用）/ `reference`（参考项目）。
状态：`maintained` / `archived` / `experimental`。

## 下游：注册表 → 文档与 profile

注册表是**数据源**，README 与 profile 仓库里的项目清单是它的**渲染产物**。
改完 `apps.json` 后要同步刷新：

1. 聚合仓库自身的 README 项目清单
2. 用户 profile 仓库（如 `qdriven/qdriven`）里的项目段落
3. 组织 profile 仓库（如 `<org>/.github`）里的项目段落

`spark git update-org-status <org>` 负责第 3 类（把 GitHub 上的仓库列表按 star
排序写进 README 段落）；第 1、2 类通常按注册表内容手工渲染。

## 相关文档

- [Hub 命令规格](../spec/hub.md)
- [Hub 使用说明](../usage/hub.md)
- [Git 管理](../features/git.md)
