# spark update

批量更新多个 Git 仓库到最新版本。

## 概述

`update` 命令会扫描指定目录中的所有 Git 仓库，并逐个执行 `git pull` 操作将它们更新到最新版本。

## 使用方法

```bash
spark update [flags]
```

## 标志

| 标志 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--path` | `-p` | `.` | 要扫描的目录路径（可多次指定） |
| `--config` | | `$HOME/.spark.yaml` | 配置文件路径 |

## 示例

### 更新当前目录下的所有仓库

```bash
spark update
```

### 更新指定目录下的所有仓库

```bash
spark update -p ~/workspace
```

### 更新多个目录下的仓库

```bash
spark update -p ~/workspace -p ~/projects -p ~/opensource
```

### 使用配置文件

在 `~/.spark.yaml` 中配置默认路径：

```yaml
path:
  - ~/workspace
  - ~/projects
```

然后直接运行：

```bash
spark update
```

## 工作流程

1. **扫描仓库**: 递归扫描指定目录，查找所有包含 `.git` 子目录的文件夹
2. **去重**: 移除重复的仓库路径
3. **更新**: 对每个仓库执行 `git pull --rebase` 操作
4. **报告**: 显示每个仓库的更新结果

## 输出示例

```
Scanning for git repositories in: /Users/you/workspace
Found 5 unique repository(s)

Updating: /Users/you/workspace/project-a
  Success!

Updating: /Users/you/workspace/project-b
  Success!

Updating: /Users/you/workspace/project-c
  Error: conflict detected

Updating: /Users/you/workspace/project-d
  Success!

Updating: /Users/you/workspace/project-e
  Success!
```

## 错误处理

- **仓库不存在**: 跳过并显示警告
- **网络错误**: 显示错误信息，继续处理下一个仓库
- **合并冲突**: 显示错误信息，需要手动解决

## 相关命令

- [create](./create.md) - 创建 Mono 仓库
- [sync](./sync.md) - 同步子模块
