# 脚本管理

## 功能概述

`spark script` 管理和执行自定义自动化脚本。脚本可以来自配置文件声明，也可以是 `scripts/` 目录下的可执行文件。

## 核心能力

### 脚本发现

自动发现两种来源的脚本：
1. **配置文件脚本**：`~/.spark.yaml` 中的 `spark.scripts` 或顶层 `scripts` 配置
2. **目录脚本**：项目 `scripts/` 目录下的可执行文件

配置文件脚本优先级高于目录脚本。

```bash
spark script list
```

### 脚本执行

通过名称执行已注册的脚本，支持传递额外参数。

```bash
spark script run my-script
spark script run deploy -- --env production
```

## 使用参数

| 命令 | 参数 | 说明 |
|------|------|------|
| `list` | 无 | 列出所有可用脚本 |
| `run` | `<name> [args...]` | 执行脚本并传递参数 |

## 配置示例

```yaml
# ~/.spark.yaml
spark:
  scripts:
    - name: hello
      description: Say hello
      command: echo "Hello, World!"
```

## 相关文档

- [Script 命令规格](../spec/script.md)
