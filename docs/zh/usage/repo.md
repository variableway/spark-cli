# spark repo — 仓库管理

通过 registry 文件管理一个目录下的多个 GitHub 仓库，替代 submodule 管理。

## 命令速查

```bash
spark repo scan [folder-name]                    # 扫描分类目录并写入分类 registry_<folder>.yaml
spark repo scan [folder-name] --json             # 同时写出格式化 registry_<folder>.json
spark repo scan [folder-name] --flatten          # （仅旧两层布局）拍平为 category/repo 再扫描
spark repo list -f registry_<folder>.yaml        # 列出 registry 中的仓库（分类格式按分组输出）
spark repo clone -f registry_<folder>.yaml       # 克隆 registry 中全部仓库（按记录的 path 还原）
spark repo clone -r <name> -f registry_<folder>.yaml  # 仅克隆指定仓库
```

---

## spark repo scan

递归扫描目录，发现带 `origin` 远程的 Git 仓库，写入当前目录下的 `registry_<folder>.yaml`（分类格式）。

```bash
spark repo scan                                # 扫描当前目录
spark repo scan ~/workspace/innate-references  # 扫描指定目录（三分层布局）
spark repo scan ~/workspace/innate-apps --json # 同时写出 registry_innate-apps.json
spark repo scan ~/workspace/legacy-refs --flatten  # 旧两层布局：先拍平再扫描
```

| 标志 | 默认值 | 说明 |
|------|--------|------|
| `--json` | `false` | 在 YAML 之外额外写出格式化（2 空格缩进）的 `registry_<folder>.json`，内容与 YAML 一致 |
| `--flatten` | `false` | 扫描前把超过两层（`category/repo`）的仓库上移到**旧两层布局**；三分层（`category/subcategory/project`）目录禁止使用 |

**流程**：（可选）`--flatten` 拍平深层目录 → 递归查找 `.git`（含 `.git` 文件）→ 解析 `origin` 远程 URL → 归一化 → 与已有 registry 合并 → 按分类目录归组（`Categorize`）→ 写入 `registry_<folder>.yaml`（及 `--json` 时的 `registry_<folder>.json`）

扫描时会跳过隐藏目录以及 `node_modules`/`venv`/`.venv`/`__pycache__`/`dist`/`build`。SSH URL 会归一化为 HTTPS 形式存储。重复扫描会保留已有的 `name`/`desc`，并清理目录已不存在的旧条目。

### 三层分类布局（registry v2）

目录约定为**三层**：`<分类>/<子分类>/<项目>`。

```
references/
├── skills/                 # 一级 = 分类（目录名即 registry 的 category）
│   ├── agent/              # 二级 = 子分类
│   │   └── taste-skill/    # 三级 = 开源项目（带 origin 的 git 仓）
│   └── others/             # 没有子分类的项目归入 others（每个分类恒有 others）
├── products/
│   └── others/
└── plugins/
    └── others/
```

- **分类**取自一级子目录（即使一个项目都没有也会出现在 registry 里）；**每个分类恒有 `others` 子分类**。
- 直接放在分类下的项目（`skills/some-project`）没有子分类，registry 中归入该分类的 `others`（磁盘上应移动到 `skills/others/some-project`）。
- 项目内部更深的嵌套仓（如 `fire-skills/downloads/*`）保全完整 path，仍归入其前两段的 `分类/子分类`。
- 直接放在扫描根目录的仓库没有分类，打印 `WARNING` 且不写入 registry（需先移入某个分类）。
- **没有一级分类目录**的普通目录自动回退为旧的扁平 `projects:` 格式，行为与旧版一致。

### `--flatten` 仅适用于旧两层布局

旧布局约定为两层：第一层 category，第二层仓库（`tooling/spark-cli`）。当存在三层或更深目录时，`--flatten` 会把深层仓库移动到 `<category>/<仓库名>`，例如：

```
apps/fe/innate/web/innate-fe-cli  →  apps/innate-fe-cli
tooling/spark/spark-cli           →  tooling/spark-cli
```

- **不要对三分层分类目录使用 `--flatten`**：它会把 `skills/agent/taste-skill` 上移到 `skills/taste-skill`，破坏子分类结构。分类布局靠 `Categorize` 归组，不需要移动任何文件。
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

克隆目标按 registry 记录的 `path` 还原（分类格式即 `<分类>/<子分类>/<项目>`），并按 path 深度**从浅到深**执行——先克隆父项目，再克隆记录在其内部的嵌套仓。

---

## spark repo list

列出 registry 文件中的仓库。

| 标志 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `-f, --file` | | | registry 文件（必填） |

```bash
spark repo list -f registry_innate-apps.yaml
```

每行输出 `name<TAB>repo<TAB>path`。分类格式（v2）会先打印一行分组头 `# <分类> / <子分类> (<数量>)`，行格式不变（机器解析时跳过 `#` 开头的行即可）。

---

## registry 文件

**分类格式（v2，三分层目录扫描的默认输出）**：

```yaml
# Project registry
# Synced by spark repo scan

version: 2
categories:
    - name: skills
      subcategories:
        - name: agent
          projects:
            - name: taste-skill
              repo: https://github.com/Leonxlnx/taste-skill.git
              path: skills/agent/taste-skill
              desc: 前端审美 skill
        - name: others
          projects: []
    - name: products
      subcategories:
        - name: others
          projects: []
    - name: plugins
      subcategories:
        - name: others
          projects: []
```

**旧扁平格式（无一级分类目录的目录仍保持不变，可继续读取）**：

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
