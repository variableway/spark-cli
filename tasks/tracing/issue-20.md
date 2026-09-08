# Tracing: spark repo: 管理 GitHub 仓库 registry（scan/clone/list）

## Task Entry (2026-09-07 15:26:35)

- **Issue**: #20
- **Title**: spark repo: 管理 GitHub 仓库 registry（scan/clone/list）
- **Started At**: 2026-09-07 15:26:35
- **Status**: completed

### Original Task Description

```markdown
## Task 1: 管理 GitHub 仓库（registry 方式，非 submodule）

背景与目标：
1. 一个目录内可能包含多个 GitHub 仓库，但这些仓库不希望作为 git submodule 管理。
2. 需要一个命令扫描指定目录下的所有 GitHub 仓库，并保存到 registry 文件。
3. 参考实现：innate-workspace/scripts/ 下的 Python 实现（scan.py / clone.py），将其转换为 spark-cli 子命令。

新增子命令 spark repo：
- scan <folder_name>：扫描目录，保存到 registry_<folder_name>.yaml
- clone -r <repo_name> -f registry_<folder_name>.yaml：从 registry 克隆仓库到 <folder_name> 目录
- list -f registry_<folder_name>.yaml：列出 registry 中的仓库

spark-cli 代码位于 innate-apps/tooling/spark-cli。完成后需补充 BDD 测试用例与文档。
```
- **Completed At**: 2026-09-08 13:08:00

### Implementation Summary

已完成 spark repo 子命令（scan/clone/list），用 registry 文件管理目录下多个 GitHub 仓库（替代 submodule）。实现 internal/registry 包（扫描/读写/merge/克隆目标路径），新增 cmd/repo 命令组并注册到根命令；补充 Ginkgo/Gomega BDD 测试（13 个 spec 全部通过）；新增中英文文档（usage/spec/features）并更新 navigation.json 与 AGENTS.md。

