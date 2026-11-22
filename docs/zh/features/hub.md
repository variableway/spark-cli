# 项目 Hub

## 功能概述

`spark hub` 是扫描、登记、按清单克隆的入口，里面有两份清单，用途不同：

- **registry** 管理 references 目录。扫描写入 `registry_<folder>.yaml`，再按这份文件把仓库克隆回来。
- **collections** 登记自己开发的 app。扫描写入 `registry/apps.json`，给文档站和 profile 用。

多仓库目录走 registry，不用 git submodule。

## 核心能力

### references：扫描并克隆

```bash
spark hub registry scan ~/workspace/innate-references
spark hub registry clone -f registry_innate-references.yaml
spark hub registry clone-registry registry_references.yaml --dry-run
```

重扫是合并。本地没检出的条目留在文件里，以后用 `clone` 或 `clone-registry` 补齐。

### 自研 app：写入 collections

```bash
spark hub collections scan . -o registry/apps.json --merge registry/apps.json
```

合并时保留手工维护的 `title` / `category` / `status` / `url` / `description`。

## 相关文档

- [Hub 命令规格](../spec/hub.md)
- [Hub 使用说明](../usage/hub.md)
