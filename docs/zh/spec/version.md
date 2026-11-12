# spark version — 命令规格

打印 spark 二进制的版本、源码提交和构建日期。用于确认 PATH 上的 spark 二进制与最新源码构建一致。

## 父命令

```
spark version
```

无参数，无标志。

---

## spark version

```
spark version [flags]
```

| 标志 | 简写 | 类型 | 默认值 | 必填 | 说明 |
|------|------|------|--------|------|------|
| `--help` | `-h` | bool | `false` | 否 | 显示帮助 |

无参数。

---

## spark --version

根命令带有一个版本标志，输出简短的版本信息。

| 标志 | 简写 | 类型 | 默认值 | 必填 | 说明 |
|------|------|------|--------|------|------|
| `--version` | `-v` | bool | `false` | 否 | 打印 spark 版本 |

---

## 输出格式

`spark version` 输出版本号、提交哈希、构建日期，以及构建信息里的 VCS 时间：

```
spark v0.3.3
  commit:     25d5128
  build date: 2026-11-01T04:26:58Z
  vcs.time:   2026-11-01T04:26:58Z (dirty)
```

- 第一行是 `spark` 加版本号。
- `commit` 是源码提交的短哈希。
- `build date` 是构建时间，UTC。
- `vcs.time` 来自 Go 的构建信息（`debug.ReadBuildInfo()`），仅在该字段存在时打印。构建信息里没有 `vcs.time` 但有 `vcs.revision` 时，这一行改为打印提交哈希的前 7 位。
- `(dirty)` 后缀表示构建时工作区有未提交的改动，仅在 `vcs.modified` 为 `true` 时出现。

`spark --version` 输出简短形式：

```
spark version v0.3.3
```

---

## 版本号来源

版本号在构建时注入，不是运行时计算的。

版本字面量存放在 `internal/witr/version/VERSION` 文件中，内容为：

```
0.3.3
```

`Makefile` 在构建时读取该文件，并把版本号、提交哈希和构建日期通过 `-ldflags` 注入到 `spark/internal/witr/version` 包的变量中：

```
VERSION ?= $(shell cat internal/witr/version/VERSION 2>/dev/null || echo dev)
COMMIT  ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo unknown)
DATE    ?= $(shell date -u +%Y-%m-%dT%H:%M:%SZ)
LDFLAGS := -s -w \
    -X "spark/internal/witr/version.Version=v$(VERSION)" \
    -X "spark/internal/witr/version.Commit=$(COMMIT)" \
    -X "spark/internal/witr/version.BuildDate=$(DATE)"
```

`Taskfile.yml` 的构建任务使用同样的三个变量和同样的注入方式。

没有提供 `-ldflags` 时（例如 Debian 打包或 `go install`），`internal/witr/version/version.go` 会回退到内置的 VERSION 文件和 VCS 构建信息：

- 版本号来自 `//go:embed VERSION` 嵌入的文件内容，并补上 `v` 前缀
- 提交哈希取自 `vcs.revision` 的前 7 位
- 构建日期取自 `vcs.time`
- 三者仍为空时，依次回退为 `v0.0.0-dev`、`unknown`、`unknown`

---

## 相关文档

- [命令总览](../usage/usage.md)
- [Witr 使用指南](../usage/witr.md)
