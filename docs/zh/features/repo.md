# 仓库管理

## 功能概述

`spark repo` 通过 registry 文件管理一个目录下的多个 GitHub 仓库，替代 submodule 管理。目录中包含很多 GitHub 仓库、但又不希望作为 submodule 管理时，可用该命令扫描、登记、克隆这些仓库。

## 核心能力

### 目录扫描

递归扫描目录，发现带 `origin` 远程的 Git 仓库，写入 `registry_<folder>.yaml`。

```bash
spark repo scan ~/workspace/innate-apps
```

- 跳过隐藏目录与 `node_modules`/`venv`/`.venv`/`__pycache__`/`dist`/`build`
- SSH URL 归一化为 HTTPS 形式存储
- 重复扫描与已有 registry 合并，保留 `name`/`desc`，清理已消失的条目

### 批量克隆

从 registry 文件克隆仓库到 folder 目录，支持全量或按名称克隆。

```bash
# 克隆全部
spark repo clone -f registry_innate-apps.yaml

# 仅克隆指定仓库
spark repo clone -r spark-cli -f registry_innate-apps.yaml
```

已存在的仓库自动跳过。

### 列出仓库

列出 registry 中声明的仓库，便于查看登记状态。

```bash
spark repo list -f registry_innate-apps.yaml
```

## registry 文件

```yaml
# Project registry
# Synced by spark repo scan

projects:
    - name: spark-cli
      repo: https://github.com/variableway/spark-cli.git
      path: tooling/spark-cli
      desc: Spark CLI 工具
```

## 依赖

- `git` 命令行工具

## 相关文档

- [Repo 命令规格](../spec/repo.md)
- [Repo 使用指南](../usage/repo.md)
