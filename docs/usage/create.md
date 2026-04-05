# spark create

创建一个 Mono 仓库，将多个 Git 仓库整合为子模块。

## 概述

`create` 命令扫描指定目录中的所有 Git 仓库，创建一个新的 Mono 仓库，并将这些仓库作为 Git 子模块添加进去。这对于统一管理多个相关项目非常有用。

## 使用方法

```bash
spark create [flags]
```

## 标志

| 标志 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--path` | `-p` | `.` | 要扫描的目录路径（可多次指定） |
| `--name` | `-n` | `mono-repo` | Mono 仓库名称 |
| `--output` | `-o` | `.` | Mono 仓库的输出路径 |
| `--config` | | `$HOME/.spark.yaml` | 配置文件路径 |

## 示例

### 创建默认 Mono 仓库

```bash
spark create -p ~/workspace
```

这将在当前目录创建名为 `mono-repo` 的文件夹。

### 指定名称和输出路径

```bash
spark create -p ~/workspace -n my-projects -o ~/repos
```

这将在 `~/repos/my-projects` 创建 Mono 仓库。

### 从多个目录收集仓库

```bash
spark create -p ~/work -p ~/personal -p ~/opensource -n all-projects
```

## 工作流程

1. **扫描仓库**: 递归扫描所有指定目录，查找 Git 仓库
2. **获取远程地址**: 为每个仓库获取其 origin 远程地址
3. **创建目录**: 创建 Mono 仓库目录
4. **初始化 Git**: 执行 `git init`
5. **创建 .gitignore**: 生成默认的忽略文件
6. **添加子模块**: 为每个仓库执行 `git submodule add`
7. **初始化子模块**: 执行 `git submodule update --init --recursive`
8. **创建初始提交**: 提交所有更改

## 生成的文件结构

```
my-mono-repo/
├── .git/
├── .gitignore
├── .gitmodules
├── project-a/      # 子模块
├── project-b/      # 子模块
└── project-c/      # 子模块
```

## .gitignore 内容

```gitignore
# Mono repo artifacts
.gitmodules.backup
```

## 输出示例

```
Scanning for git repositories in: /Users/you/workspace
Found 5 unique repository(s)

Creating mono repo at: ./mono-repo
Adding submodule: project-a
Adding submodule: project-b
Adding submodule: project-c
Adding submodule: project-d
Adding submodule: project-e

Mono repo created successfully!
Location: ./mono-repo

To update all submodules, run:
  cd mono-repo && git submodule update --remote --merge
```

## 注意事项

- 如果 Mono 仓库目录已存在，命令将失败
- 无法获取远程地址的仓库将被跳过
- 子模块添加失败的仓库会显示警告，但不会中断整个过程

## 后续操作

创建 Mono 仓库后，你可以：

1. **更新子模块**:
   ```bash
   cd mono-repo
   git submodule update --remote --merge
   ```

2. **使用 sync 命令**:
   ```bash
   spark sync ./mono-repo
   ```

## 相关命令

- [update](./update.md) - 更新多个仓库
- [sync](./sync.md) - 同步子模块
