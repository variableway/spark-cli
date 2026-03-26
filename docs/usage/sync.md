# monolize sync

同步 Mono 仓库中的所有子模块到最新版本。

## 概述

`sync` 命令用于更新 Mono 仓库中的所有 Git 子模块，将它们同步到各自的最新版本。这是 `create` 命令创建 Mono 仓库后的常用维护操作。

## 使用方法

```bash
monolize sync <mono-repo-path>
```

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `mono-repo-path` | 是 | Mono 仓库的路径 |

## 示例

### 同步 Mono 仓库

```bash
monolize sync ./mono-repo
```

### 使用绝对路径

```bash
monolize sync /Users/you/repos/my-projects
```

## 工作流程

1. **验证路径**: 检查指定路径是否为有效的 Mono 仓库
2. **更新子模块**: 执行 `git submodule update --remote --merge`
3. **报告结果**: 显示同步状态

## 执行的 Git 命令

```bash
git submodule update --remote --merge
```

此命令会：
- 获取每个子模块的最新提交
- 将子模块更新到远程分支的最新提交
- 使用 merge 策略合并更改

## 输出示例

```
Syncing all submodules in: ./mono-repo
All submodules synced successfully!
```

## 使用场景

### 定期同步

建议定期运行此命令以保持所有子模块为最新版本：

```bash
# 每日同步
monolize sync ~/repos/mono-repo
```

### 团队协作

当团队成员需要获取最新的子模块状态时：

```bash
# 在 Mono 仓库中工作前先同步
cd ~/repos/mono-repo
monolize sync .
```

### CI/CD 集成

在持续集成流程中使用：

```bash
# 在构建前同步所有依赖
monolize sync ./dependencies
```

## 故障排除

### 子模块未初始化

如果子模块未初始化，先运行：

```bash
cd mono-repo
git submodule update --init --recursive
```

### 合并冲突

如果同步时出现合并冲突：

1. 进入冲突的子模块目录
2. 手动解决冲突
3. 提交解决后的更改

### 网络问题

如果网络连接不稳定，可以：

1. 检查网络连接
2. 重试命令
3. 配置 Git 代理

## 相关命令

- [create](./create.md) - 创建 Mono 仓库
- [update](./update.md) - 更新多个仓库
