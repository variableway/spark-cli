# spark script — 脚本管理

管理和执行自定义脚本。

## 命令速查

```bash
spark script list                             # 列出所有可用脚本
spark script run <name> [args...]             # 执行脚本
```

---

## spark script list

列出所有可用的脚本。脚本来源有两个：

1. **配置文件** `~/.spark.yaml` 中的 `spark.scripts`
2. **脚本目录** 项目根目录下的 `scripts/` 文件夹

配置文件中的脚本优先。

```bash
spark script list
```

---

## spark script run

执行指定脚本，支持传递参数。

```bash
spark script run hello                        # 运行 hello 脚本
spark script run deploy prod                  # 带参数运行
spark script run copy-template my-feature     # 多参数
```

## 配置示例

在 `~/.spark.yaml` 中定义脚本：

```yaml
spark:
  scripts:
    - name: hello
      content: |
        #!/bin/bash
        echo "Hello, $1!"
```

或在 `scripts/` 目录下放置可执行脚本文件。

## 相关命令

- [任务管理](./task.md)
- [文档管理](./docs-cmd.md)
