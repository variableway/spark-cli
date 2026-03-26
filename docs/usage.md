# Monolize 使用指南

`Monolize` 是一个用于管理多个 Git 仓库的命令行工具，支持将其合并为单仓（Mono-repo）并同步子模块。

## 基础命令

### 1. 更新所有仓库
扫描指定目录下的所有 Git 仓库并拉取最新更改。支持指定多个路径。
```bash
monolize update --path /your/repos/path1 --path /your/repos/path2
```

### 2. 创建 Mono-repo
将指定目录下的所有仓库作为子模块添加到一个新的 Mono-repo 中。支持单个仓库路径或包含多个仓库的目录。
```bash
# 包含多个仓库的目录
monolize create --path ./my-projects --name my-mono-repo

# 指定多个源（可以是单仓路径或多仓目录）
monolize create -p ./repo1 -p ./projects-dir -n my-mono-repo
```

### 3. 同步子模块
在 Mono-repo 根目录下运行，一次性更新所有子模块到远程最新版本。
```bash
monolize sync
```

## Makefile 使用
项目提供了跨平台的 `Makefile` 以简化日常操作：

| 命令 | 说明 |
| :--- | :--- |
| `make build` | 根据当前系统编译二进制文件 |
| `make test` | 运行所有单元测试 |
| `make test-bdd` | 以 BDD 模式运行测试（输出更详细） |
| `make build-linux` | 交叉编译 Linux 版本 |
| `make build-darwin` | 交叉编译 macOS 版本 |
| `make clean` | 清理编译产物 |

## 配置说明
可以通过 `~/.monolize.yaml` 进行持久化配置：
```yaml
path: /default/path
default_branch: main
auto_commit: true
```
