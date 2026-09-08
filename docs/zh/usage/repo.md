# spark repo — 仓库管理

通过 registry 文件管理一个目录下的多个 GitHub 仓库，替代 submodule 管理。

## 命令速查

```bash
spark repo scan [folder-name]                    # 扫描目录并写入 registry_<folder>.yaml
spark repo list -f registry_<folder>.yaml        # 列出 registry 中的仓库
spark repo clone -f registry_<folder>.yaml       # 克隆 registry 中全部仓库
spark repo clone -r <name> -f registry_<folder>.yaml  # 仅克隆指定仓库
```

---

## spark repo scan

递归扫描目录，发现带 `origin` 远程的 Git 仓库，写入当前目录下的 `registry_<folder>.yaml`。

```bash
spark repo scan                                # 扫描当前目录
spark repo scan ~/workspace/innate-apps        # 扫描指定目录
```

**流程**：递归查找 `.git`（含 `.git` 文件）→ 解析 `origin` 远程 URL → 归一化 → 与已有 registry 合并 → 写入 `registry_<folder>.yaml`

扫描时会跳过隐藏目录以及 `node_modules`/`venv`/`.venv`/`__pycache__`/`dist`/`build`。SSH URL 会归一化为 HTTPS 形式存储。重复扫描会保留已有的 `name`/`desc`，并清理目录已不存在的旧条目。

---

## spark repo clone

从 registry 文件克隆仓库到 folder 目录。目标目录名由 registry 文件名推导（`registry_<folder>.yaml` → `<folder>`）。

| 标志 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `-r, --repo` | | | 仅克隆指定名称的仓库 |
| `-f, --file` | | | registry 文件（必填） |

```bash
# 克隆 registry 中全部仓库到 innate-apps 目录
spark repo clone -f registry_innate-apps.yaml

# 仅克隆指定仓库
spark repo clone -r spark-cli -f registry_innate-apps.yaml
```

已存在的仓库（`.git` 或目录已存在）会被跳过，结束时打印 `cloned / skipped / failed` 统计。

---

## spark repo list

列出 registry 文件中的仓库。

| 标志 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `-f, --file` | | | registry 文件（必填） |

```bash
spark repo list -f registry_innate-apps.yaml
```

每行输出 `name<TAB>repo<TAB>path`。

---

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

## 相关命令

- [Git 管理](./git.md)
