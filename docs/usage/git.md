# spark git — Git 仓库管理

管理多个 Git 仓库、创建 Mono-repo、同步子模块。

## 命令速查

```bash
spark git update                              # 更新所有仓库
spark git create -n <name> -o <path>          # 创建 Mono-repo
spark git sync <mono-path>                    # 同步子模块
spark git gitcode                             # 添加 Gitcode 远程
spark git config [--username --email]         # 配置 Git 用户
spark git url [repo-path]                     # 查看远程 URL
spark git clone-org <org> [-o <dir>]          # 克隆组织所有仓库
spark git update-org-status <org> [--dry-run] # 更新组织 README
```

---

## spark git update

批量更新指定目录下的所有 Git 仓库到最新版本。

```bash
spark git update                              # 更新当前目录下所有仓库
spark git update -p ~/workspace               # 更新指定目录
spark git update -p ~/ws -p ~/projects        # 多个目录
```

**流程**: 扫描目录 → 查找 `.git` → 逐个 `git pull --rebase` → 输出结果

---

## spark git create

将多个仓库整合为一个带有子模块的 Mono 仓库。

| 标志 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--name` | `-n` | `mono-repo` | Mono 仓库名称 |
| `--output` | `-o` | 源路径 | 输出路径 |

```bash
spark git create                              # 默认创建 mono-repo
spark git create -n my-mono -o ./output       # 指定名称和输出路径
spark git create -p ~/workspace -n projects   # 从指定目录创建
```

---

## spark git sync

同步 Mono 仓库中所有子模块到最新版本。

```bash
spark git sync ./my-mono-repo                 # 同步指定 Mono 仓库
```

---

## spark git gitcode

为 GitHub 仓库自动添加 Gitcode 远程地址。

| 标志 | 默认值 | 说明 |
|------|--------|------|
| `--url` | 自动转换 | 自定义 Gitcode URL |

```bash
spark git gitcode                             # 自动转换 GitHub → Gitcode
spark git gitcode --url https://gitcode.com/user/repo
```

---

## spark git config

配置仓库的 Git 用户信息。

| 标志 | 默认值 | 说明 |
|------|--------|------|
| `--username` | 配置文件值 | Git 用户名 |
| `--email` | 配置文件值 | Git 邮箱 |

```bash
spark git config                              # 使用配置文件中的值
spark git config --username "John" --email "john@example.com"
spark git config /path/to/repo                # 配置指定仓库
```

---

## spark git url

获取仓库的远程 URL。

```bash
spark git url                                 # 当前目录
spark git url /path/to/repo                   # 指定仓库
```

---

## spark git clone-org

克隆 GitHub 组织的所有仓库。

| 标志 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--ssh` | | `false` | 使用 SSH URL |
| `--include` | | | 仅包含匹配的仓库（逗号分隔） |
| `--exclude` | | | 排除匹配的仓库（逗号分隔） |
| `--include-forks` | | `false` | 包含 fork 仓库 |
| `--output` | `-o` | `.` | 输出目录 |

```bash
spark git clone-org variableway               # 克隆组织所有仓库
spark git clone-org variableway --ssh         # 使用 SSH
spark git clone-org variableway --include spark --exclude test
spark git clone-org variableway -o ./repos    # 指定输出目录
```

---

## spark git update-org-status

获取组织仓库列表并更新 README.md。

| 标志 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--output` | `-o` | `.github/README.md` | 输出文件路径 |
| `--dry-run` | | `false` | 预览不写入 |
| `--update-dot-github` | | `false` | 直接更新 .github 仓库 |
| `--section` | | `Project List` | 更新的 section 名称 |
| `--skip-push` | | `false` | 跳过 git push |

```bash
spark git update-org-status variableway                    # 更新本地 README
spark git update-org-status variableway --dry-run          # 预览
spark git update-org-status variableway --update-dot-github # 直接推送
spark git update-org-status variableway --section "My Projects"
```

## 相关命令

- [Agent 配置](./agent.md)
- [任务管理](./task.md)
