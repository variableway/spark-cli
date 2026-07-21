# Tracing: Add package-lock.json removal to magic clean command

## Task Entry (2026-07-21 18:22:08)

- **Issue**: #18
- **Title**: Add package-lock.json removal to magic clean command
- **Started At**: 2026-07-21 18:22:08
- **Status**: completed

### Original Task Description

```markdown
在 spark magic clean 命令中增加删除 package-lock.json 文件的能力。当前 clean 命令仅递归删除 node_modules 和 .venv 目录，且只处理目录类型；package-lock.json 是文件，需要扩展遍历逻辑以同时支持文件删除，并将其归入 node 清理模式。
```
- **Completed At**: 2026-07-21 18:24:45

### Implementation Summary

已在 spark magic clean 命令中增加删除 package-lock.json 文件的能力:归入 node 模式,与 node_modules 一并清理;python 模式不受影响。重构出可测函数 cleanPaths 并新增 5 个 Ginkgo BDD 用例,全部测试与 lint、build 通过,端到端冒烟验证行为符合预期。

