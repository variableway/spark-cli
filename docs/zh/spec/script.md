# spark script — 命令规格

自定义脚本管理命令组。

## 父命令

```
spark script
```

无参数，无标志。

---

## spark script list

列出所有可用的脚本。脚本来源：
- `~/.spark.yaml` 中的 `spark.scripts` 或顶层 `scripts` 配置
- 项目 `scripts/` 目录下的可执行文件

```
spark script list
```

无标志，无参数。

---

## spark script run

执行指定的脚本。

```
spark script run <script-name> [args...]
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `script-name` | string | 是 | 脚本名称 |
| `args` | string[] | 否 | 传递给脚本的参数 |

无标志。
