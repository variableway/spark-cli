# monolize gitcode

为 GitHub 仓库添加 Gitcode 作为远程地址。

## 概述

`gitcode` 命令扫描指定目录中的所有 Git 仓库，为每个使用 GitHub 作为 origin 的仓库添加 Gitcode 作为另一个远程地址。这对于需要同时在 GitHub 和 Gitcode 上维护镜像的用户非常有用。

## 使用方法

```bash
monolize gitcode [flags]
```

## 标志

| 标志 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--path` | `-p` | `.` | 要扫描的目录路径（可多次指定） |
| `--url` | | | 自定义 Gitcode URL（默认自动转换） |
| `--config` | | `$HOME/.monolize.yaml` | 配置文件路径 |

## 工作原理

1. **扫描仓库**: 递归扫描指定目录，查找所有 Git 仓库
2. **检查远程**: 检查仓库是否已有 `gitcode` 远程
3. **获取 origin**: 获取仓库的 origin 远程地址
4. **转换 URL**: 将 GitHub URL 转换为 Gitcode URL
5. **添加远程**: 执行 `git remote add gitcode <url>`

## URL 转换规则

| GitHub URL | Gitcode URL |
|------------|-------------|
| `https://github.com/user/repo.git` | `https://gitcode.com/user/repo.git` |
| `git@github.com:user/repo.git` | `git@gitcode.com:user/repo.git` |

## 示例

### 基本使用

```bash
monolize gitcode -p ~/workspace
```

**输出示例**:

```
Scanning for git repositories in: /Users/you/workspace
Found 3 unique repository(s)

Processing: /Users/you/workspace/project-a
  Origin:   https://github.com/myuser/project-a.git
  Gitcode:  https://gitcode.com/myuser/project-a.git
  Successfully added gitcode remote!

Processing: /Users/you/workspace/project-b
  Gitcode remote already exists, skipping...

Processing: /Users/you/workspace/project-c
  Origin:   git@github.com:myuser/project-c.git
  Gitcode:  git@gitcode.com:myuser/project-c.git
  Successfully added gitcode remote!
```

### 扫描多个目录

```bash
monolize gitcode -p ~/work -p ~/personal -p ~/opensource
```

### 使用自定义 Gitcode URL

```bash
monolize gitcode -p ~/workspace --url https://custom.gitcode.net/user/repo.git
```

## 验证结果

添加远程后，可以验证：

```bash
cd ~/workspace/project-a
git remote -v
```

输出：

```
origin   https://github.com/myuser/project-a.git (fetch)
origin   https://github.com/myuser/project-a.git (push)
gitcode  https://gitcode.com/myuser/project-a.git (fetch)
gitcode  https://gitcode.com/myuser/project-a.git (push)
```

## 推送到 Gitcode

添加远程后，可以推送代码：

```bash
# 推送当前分支
git push gitcode main

# 推送所有分支
git push gitcode --all

# 推送所有标签
git push gitcode --tags
```

## 使用场景

### 镜像仓库

保持 GitHub 和 Gitcode 上的仓库同步：

```bash
# 添加 Gitcode 远程
monolize gitcode -p ~/workspace

# 在每个仓库中推送到两个远程
cd ~/workspace/my-project
git push origin main
git push gitcode main
```

### 国内访问优化

对于国内开发者，Gitcode 可能比 GitHub 访问更快：

```bash
# 从 Gitcode 克隆
git clone git@gitcode.com:user/repo.git

# 添加 GitHub 作为上游
git remote add upstream https://github.com/user/repo.git

# 同步上游更新
git fetch upstream
git merge upstream/main
```

## 跳过条件

命令会自动跳过以下情况：

1. **已有 gitcode 远程**: 如果仓库已有名为 `gitcode` 的远程
2. **无 origin 远程**: 如果仓库没有 origin 远程地址
3. **无法获取 URL**: 如果无法读取远程 URL

## 故障排除

### 远程已存在

```
Gitcode remote already exists, skipping...
```

这是正常的跳过提示，无需处理。

### 无 origin 远程

```
Error: failed to get origin URL: exit status 128
```

检查仓库是否有 origin 远程：

```bash
git remote -v
```

如果没有，先添加 origin：

```bash
git remote add origin https://github.com/user/repo.git
```

### 权限问题

确保对仓库目录有读写权限。

## 相关命令

- [update](./update.md) - 更新多个仓库
- [create](./create.md) - 创建 Mono 仓库
