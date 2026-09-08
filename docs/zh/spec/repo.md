# spark repo — 命令规格

通过 registry 文件管理目录下多个 GitHub 仓库（不使用 submodule）。

## 父命令

```
spark repo
```

无参数，无标志。

Registry 文件格式：

```yaml
# Project registry
# Synced by spark repo scan

projects:
    - name: spark-cli
      repo: https://github.com/variableway/spark-cli.git
      path: tooling/spark-cli
      desc: Spark CLI 工具
```

---

## spark repo scan

递归扫描目录下的 Git 仓库（仅保留带 `origin` 远程的仓库），将结果写入当前目录下的 `registry_<folder>.yaml`。

```
spark repo scan [folder-name]
```

| 参数 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `folder-name` | string | `.` | 否 | 要扫描的目录路径 |

无标志。

**行为**：
- 递归查找 `.git` 目录与 `.git` 文件（含 `gitdir:` 重定向），解析 `[remote "origin"]` 下的 `url`
- 跳过隐藏目录以及 `node_modules`/`venv`/`.venv`/`__pycache__`/`dist`/`build`
- SSH URL 归一化为 HTTPS 形式后存储
- registry 文件名取目录绝对路径的 basename：`registry_<folder>.yaml`
- 重复扫描会与已有 registry 合并：按 `path` 优先、其次按 `repo` URL 匹配，保留旧的 `name`/`desc`，删除目录已不存在的旧条目，追加新发现的仓库

---

## spark repo clone

从 registry 文件克隆仓库到对应的 folder 目录。目标目录名由 registry 文件名推导（`registry_<folder>.yaml` → `<folder>`）。

```
spark repo clone [-r <repo-name>] -f <registry-file>
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `-r, --repo` | string | | 否 | 仅克隆指定名称的仓库（省略则克隆全部） |
| `-f, --file` | string | | 是 | registry 文件（`registry_<folder>.yaml`） |

无参数。

**行为**：
- 已存在 `.git` 或目录已存在时跳过（输出 `SKIP ...`）
- 逐个执行 `git clone <repo> <target>`
- 结束打印 `cloned / skipped / failed` 统计；`failed > 0` 时返回错误

---

## spark repo list

列出 registry 文件中声明的仓库（名称、远程 URL、相对路径）。

```
spark repo list -f <registry-file>
```

| 标志 | 类型 | 默认值 | 必填 | 说明 |
|------|------|--------|------|------|
| `-f, --file` | string | | 是 | registry 文件（`registry_<folder>.yaml`） |

无参数。

**输出**：每行 `name<TAB>repo<TAB>path`；registry 为空时打印 `No repositories in registry.`
