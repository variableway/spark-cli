# spark witr — 命令规格

进程诊断命令。解释某个进程或端口为什么在运行，追溯它的祖先链。

## 父命令

```
spark witr
```

无参数，无标志。直接执行 `spark witr` 会启动交互式 TUI。

---

## spark witr

```
spark witr [process name...] [flags]
```

| 标志 | 简写 | 类型 | 默认值 | 必填 | 说明 |
|------|------|------|--------|------|------|
| `--container` | `-c` | strings | | 否 | 要查找的容器名，可重复传入 |
| `--env` | | bool | `false` | 否 | 显示进程环境变量 |
| `--exact` | `-x` | bool | `false` | 否 | 精确匹配名称，不做子串搜索 |
| `--file` | `-f` | strings | | 否 | 进程打开的文件路径，可重复传入 |
| `--help` | `-h` | bool | `false` | 否 | 显示帮助 |
| `--interactive` | `-i` | bool | `false` | 否 | 交互模式（TUI） |
| `--json` | | bool | `false` | 否 | 以 JSON 输出结果 |
| `--no-color` | | bool | `false` | 否 | 禁用彩色输出 |
| `--pid` | | strings | | 否 | 要查找的 PID，可重复传入 |
| `--port` | `-o` | strings | | 否 | 要查找的端口，可重复传入 |
| `--short` | `-s` | bool | `false` | 否 | 只显示祖先链 |
| `--tree` | `-t` | bool | `false` | 否 | 只以树形显示祖先链 |
| `--verbose` | | bool | `false` | 否 | 显示进程扩展信息 |
| `--version` | `-v` | bool | `false` | 否 | 显示 witr 自身的版本 |
| `--warnings` | | bool | `false` | 否 | 只显示警告 |

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `process name` | string[] | 否 | 按名称查找的进程名，可传多个 |

`--pid`、`--port`、`--file`、`--container` 都是可重复的字符串切片标志，既可以重复传入该标志，也可以用逗号分隔多个值：

```bash
spark witr --port 8080 --port 3000
spark witr --pid 1234,5678
```

查询目标按命令行中出现的先后顺序处理，多个目标可以混合使用：

```bash
spark witr nginx --pid 1234 --port 8080
```

`--file` 在 Windows 上不受支持，会返回 `finding process by file is not supported on Windows`。

### TUI 触发条件

满足下列任一条件时进入交互式 TUI，而不是打印文本结果：

- 显式传入 `--interactive` / `-i`
- 完全没有提供查询目标：既没有 `--pid`、`--port`、`--file`、`--container`，也没有 `--env`，并且没有位置参数

仅给出显示类标志（例如 `--json`、`--tree`、`--short`）仍然会进入 TUI，因为这些标志不构成查询目标。

只给 `--env` 而不给任何目标时不进入 TUI，命令报错退出：

```
must specify --pid, --port, --file, --container, or a process name
```

### 输出格式

默认文本输出按以下顺序打印字段：`Target`、`Process`、`User`、`Container`、`Service`、`Command`、`Started`、`Why It Exists`（祖先链）、`Source`、`Description`、`Sockets`、`Warnings`。

`--short` 只输出单行祖先链，进程之间用 `→` 连接：

```
launchd (pid 1)
```

`--tree` 只输出树形结构，根节点是目标进程，下面列出它的子进程：

```
launchd (pid 1)
  ├─ /usr/libexec/logd (pid 341)
  ├─ /usr/libexec/smd (pid 342)
```

`--warnings` 只输出进程信息与警告列表。

`--env` 只输出进程信息与环境变量。

`--json` 输出机器可读的 JSON。单目标时输出一个对象，多目标时输出 JSON 数组；失败的查询以 `{"Target": ..., "Error": ...}` 条目并入数组。JSON 的结构随显示标志变化：

| 组合 | JSON 结构 |
|------|------|
| `--json` | 完整结果对象：`Target`、`ResolvedTarget`、`Process`、`RestartCount`、`Ancestry`、`Source`、`Warnings`，以及按需出现的 `Children`、`SocketInfo`、`ResourceContext`、`FileContext` |
| `--json --short` | 祖先链数组，元素为 `{"PID": ..., "Command": ...}` |
| `--json --tree` | `{"Ancestry": [...], "Children": [...]}`，元素为 `{"PID": ..., "Command": ...}` |
| `--json --warnings` | `{"PID": ..., "Process": ..., "Command": ..., "Warnings": [...]}` |
| `--json --env` | `{"PID": ..., "Process": ..., "Command": ..., "Env": [...]}` |

`Target` 对象包含 `Type` 和 `Value` 两个字段，`Type` 取值为 `name`、`pid`、`port`、`file`、`container` 之一。

`--env` 的优先级最高：一旦设置，就只输出环境变量，其余显示标志被忽略。

`--no-color` 关闭颜色输出，适合 CI 与管道场景。

### 退出码

| 退出码 | 含义 |
|--------|------|
| `0` | 查询成功且没有警告 |
| `1` | 存在警告，或发生内部错误 |
| `2` | 未找到匹配的进程 |
| `3` | 权限不足，例如端口存在但无法定位属主进程 |
| `4` | 输入无效，例如没有给出任何查询目标，或同时匹配到多个进程 |

多个目标时取所有目标退出码中的最大值。

当名称匹配到多个进程时，命令列出候选并提示用 `--pid` 重新指定：

```
Multiple matching processes found:

[1] nginx (pid 1234)
    /usr/sbin/nginx -g daemon on; master_process on;

Re-run with:
  witr --pid <pid>
```

### 相关文档

- [Witr 使用指南](../usage/witr.md)
- [Witr 功能说明](../features/witr.md)
