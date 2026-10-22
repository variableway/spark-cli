# spark repo — 仓库管理

通过 registry 文件管理一个目录下的多个 GitHub 仓库，替代 submodule 管理。

## 命令速查

```bash
spark repo scan [folder-name]                    # 扫描目录并写入 registry_<folder>.yaml
spark repo scan [folder-name] --json             # 同时写出格式化 registry_<folder>.json
spark repo scan [folder-name] --flatten          # 先把超过两层的目录拍平为 category/repo 再扫描
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
spark repo scan ~/workspace/innate-apps --json # 同时写出 registry_innate-apps.json
spark repo scan ~/workspace/innate-apps --flatten  # 先拍平深层目录再扫描
```

| 标志 | 默认值 | 说明 |
|------|--------|------|
| `--json` | `false` | 在 YAML 之外额外写出格式化（2 空格缩进）的 `registry_<folder>.json`，内容与 YAML 一致 |
| `--flatten` | `false` | 扫描前把超过两层（`category/repo`）的仓库上移到两层布局 |

**流程**：（可选）`--flatten` 拍平深层目录 → 递归查找 `.git`（含 `.git` 文件）→ 解析 `origin` 远程 URL → 归一化 → 与已有 registry 合并 → 写入 `registry_<folder>.yaml`（及 `--json` 时的 `registry_<folder>.json`）

扫描时会跳过隐藏目录以及 `node_modules`/`venv`/`.venv`/`__pycache__`/`dist`/`build`。SSH URL 会归一化为 HTTPS 形式存储。重复扫描会保留已有的 `name`/`desc`，并清理目录已不存在的旧条目。

### 两层目录布局与 --flatten

目录约定为两层：第一层是 category，第二层是正式仓库（`tooling/spark-cli`、`docs/quick-start`）。当存在三层或更深目录时，`--flatten` 会把深层仓库移动到 `<category>/<仓库名>`，例如：

```
apps/fe/innate/web/innate-fe-cli  →  apps/innate-fe-cli
tooling/spark/spark-cli           →  tooling/spark-cli
```

- 不覆盖任何文件：目标位置已存在（或本次运行中已被其他仓库占用）时，该仓库保持原位并在输出中打印 `Skipped ...` 告警。
- 移动后自动清理空的中间目录。
- `--flatten` 会直接修改磁盘上的目录结构，属于破坏性操作，请确认后再使用。

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
