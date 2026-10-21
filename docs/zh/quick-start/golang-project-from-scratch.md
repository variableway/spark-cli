# 从零创建一个标准 Go CLI 项目

面向零基础的手把手教程：从一行代码都没有，到一个能构建、能测试、带 Taskfile 的
标准 Go CLI 项目。[Golang CLI 入门 · 第一课](golang-cli-101.md) 讲「是什么」，
本篇讲「怎么做」——所有命令在 Windows / Linux / macOS 上都能照抄执行。

以 spark 项目为模板，学完你将拥有：

1. 一个带 `go.mod` / `go.sum` 的模块化项目
2. Cobra + Viper + PTerm 三件套驱动的命令行工具
3. `cmd/` + `internal/` 的标准分层结构
4. 一份可跨平台运行的 `Taskfile.yml`
5. 一个可以安装给 AI 助手的 SKILL 文档

---

## 0. 准备工作

安装 Go（1.22 以上即可，本项目用 1.27），从 <https://go.dev/dl/> 下载安装包，
装完验证：

```bash
go version
# go version go1.27.0 windows/amd64
```

## 1. 第一步：`go mod init` —— go.mod 是怎么来的

Go 项目的起点不是写代码，而是**声明一个模块**（module）。模块就是「这个项目
的 import 路径前缀」：

```bash
mkdir mycli && cd mycli
go mod init github.com/yourname/mycli
```

生成的 `go.mod` 只有两行：

```
module github.com/yourname/mycli

go 1.27.0
```

| 行 | 含义 |
|----|------|
| `module` | 模块路径。本项目内所有包的 import 路径都以它为前缀，习惯上填仓库地址（spark 填的是 `spark`，本地开发也可以这样简写） |
| `go` | 本项目要求的最低 Go 语言版本 |

此刻还**没有** `go.sum`、没有 `require` 段——它们都是装依赖时自动长出来的：

```bash
go get github.com/spf13/cobra@latest
```

执行后 `go.mod` 多出依赖声明，同时生成 `go.sum`（每个依赖的哈希校验，防篡改，
相当于 Node 的 lockfile）：

```
module github.com/yourname/mycli

go 1.27.0

require github.com/spf13/cobra v1.10.2
```

> 记忆点：**`go mod init` 造骨架，`go get` 添依赖，`go.sum` 是防篡改的小票。**
> `go.mod` 和 `go.sum` 都必须提交进 Git，否则别人 clone 后无法复现构建。

## 2. 第二步：装上 CLI 三件套

一个像样的 CLI 工具离不开这几类轮子。下表是 spark 实际依赖的直接依赖
（见 `go.mod` 的 `require` 段）：

| 依赖 | 作用 | 安装 |
|------|------|------|
| `github.com/spf13/cobra` | 命令 / 子命令 / flag 框架 | `go get github.com/spf13/cobra@latest` |
| `github.com/spf13/viper` | 配置读取（yaml + 环境变量 + flag） | `go get github.com/spf13/viper@latest` |
| `github.com/pterm/pterm` | 终端美化输出（颜色、表格、进度条） | `go get github.com/pterm/pterm@latest` |
| `github.com/charmbracelet/bubbletea`（+ `bubbles` / `lipgloss`） | 交互式 TUI | `go get github.com/charmbracelet/bubbletea@latest` |
| `github.com/onsi/ginkgo/v2` + `gomega` | BDD 测试框架 | `go get github.com/onsi/ginkgo/v2@latest` |
| `modernc.org/sqlite` | 纯 Go 的 SQLite 驱动（`spark git scan` 用） | `go get modernc.org/sqlite@latest` |
| `go.yaml.in/yaml/v3` | YAML 解析（registry 文件） | `go get go.yaml.in/yaml/v3@latest` |

全部装完跑一次整理，把没用的删掉、把缺的校验补齐：

```bash
go mod tidy
```

安装行为发生了什么：源码下载到 `GOMODCACHE`（默认在 C 盘，可 `go env -w`
指到其他盘），`go build` 时**编译进你的二进制**——没有 `node_modules`，
产物仍是一个文件。

## 3. 第三步：标准目录结构

对照 spark 的真实结构（完整版见 [AGENTS.md](../Agents.md)）：

```
mycli/
├── main.go            # 入口：只调 cmd.Execute()，不写业务
├── cmd/               # 「命令层」：每个命令组一个包
│   ├── root.go        #   根命令、全局 flag、配置初始化
│   └── magic/         #   子命令组（spark 有 git/ repo/ magic/ script/ docs/）
│       └── flush_dns.go
├── internal/          # 「业务层」：真正干活的代码，编译器禁止外部 import
│   ├── config/        #   配置加载
│   ├── git/           #   Git 操作封装
│   └── ...
├── pkg/               # 「共享层」：可以被外部项目 import 的公共库
│   └── witr/model/
├── tools/             # 辅助 CLI（spark 的 test-report 渲染器）
├── scripts/           # 安装/校验脚本（bash + powershell 双份）
├── docs/              # 文档站（见「从零创建文档站」教程）
├── go.mod / go.sum    # 依赖清单 + 校验（必须提交）
├── Makefile           # Unix 构建入口
└── Taskfile.yml       # 跨平台构建入口（Windows 首选）
```

| 目录 | 职责 | 一句话 |
|------|------|--------|
| `main.go` | 程序入口 | 只做一件事：调用 `cmd.Execute()` |
| `cmd/` | 命令定义 | Cobra 命令、flag 绑定；薄，不含业务 |
| `internal/` | 业务逻辑 | Go 的硬约束：别的模块 import 不到这里 |
| `pkg/` | 公共库 | 想被别人复用才放这里 |
| `scripts/` | 构建辅助 | 安装二进制、校验 sha256 |

`main.go` 全文（spark 就是这样）：

```go
package main

import "spark/cmd"

func main() {
    cmd.Execute()
}
```

> 记忆点：**命令在 `cmd/`，逻辑在 `internal/`，入口只当传话筒。**

## 4. 第四步：第一个命令

`cmd/root.go` 定义根命令与全局 flag（节选自 spark）：

```go
package cmd

import (
    "github.com/spf13/cobra"
    "github.com/spf13/viper"
)

var rootCmd = &cobra.Command{
    Use:   "mycli",
    Short: "A CLI tool that does useful things",
}

func Execute() {
    if err := rootCmd.Execute(); err != nil {
        return
    }
}

func init() {
    cobra.OnInitialize(initConfig)
    rootCmd.PersistentFlags().StringSliceP("path", "p", []string{"."}, "Directory to scan")
    viper.BindPFlag("repo-path", rootCmd.PersistentFlags().Lookup("path"))
}
```

子命令一个文件一个（模仿 `cmd/magic/flush_dns.go` 的骨架）：

```go
package magic

import (
    "github.com/spf13/cobra"
    "github.com/pterm/pterm"
)

var flushDNSCmd = &cobra.Command{
    Use:   "flush-dns",
    Short: "Flush DNS cache on the current system",
    RunE: func(cmd *cobra.Command, args []string) error {
        pterm.Success.Println("DNS cache flushed!")
        return nil
    },
}

func init() {
    MagicCmd.AddCommand(flushDNSCmd)
}
```

三个关键点：

1. `Use` 是命令名，`RunE` 是执行体（返回 error 而不是自己 `os.Exit`）
2. `func init()` 里 `AddCommand` 把子命令挂到父命令——每个文件自注册，
   不需要中心化的注册表
3. 输出用 `pterm`，用户看到的就是带颜色的成功/警告提示

验证：

```bash
go run . flush-dns
go build -o bin/mycli . && ./bin/mycli --help
```

## 5. 第五步：写 Taskfile 构建脚本

**为什么需要 Taskfile**：构建命令很长（ldflags 注入版本号、装到 `~/.local/bin`、
校验 sha256……），每次手敲不现实；Windows 上又常常没有 `make`。
[Task](https://taskfile.dev) 是 Go 写的任务运行器，单个二进制、YAML 声明、
跨平台，正好补位。

先解读 spark 的 `Taskfile.yml` 骨架：

```yaml
version: '3'

vars:                    # 全局变量
  BINARY_NAME: spark
  BIN_DIR: bin
  VERSION:               # 动态变量：冒号后是 shell 命令，取其输出
    sh: cat internal/witr/version/VERSION 2>/dev/null || echo dev

env:
  CGO_ENABLED: '0'       # 纯 Go 构建，产出可移植的静态二进制

tasks:
  build:
    desc: Build for current OS into bin/, stamp version, install to ~/.local/bin
    cmds:
      - task: prepare-bin          # 引用另一个 task（先建 bin/ 目录）
      - cmd: '{{.GO}} build -ldflags="-s -w -X spark/internal/witr/version.Version=v{{.VERSION}}" -o {{.BIN_DIR}}/{{.BINARY_NAME}}{{exeExt}} main.go'
      - cmd: powershell -NoProfile -ExecutionPolicy Bypass -File scripts/install-binary.ps1 ...
        platforms: [windows]       # 平台分派：同一 task 里 Windows/Linux 各跑各的
      - cmd: bash scripts/install-binary.sh ...
        platforms: [linux, darwin]

  cross-build:           # 内部 task：不显示在 task --list，供交叉编译复用
    internal: true
    requires:
      vars: [GOOS, GOARCH, OUTPUT]   # 调用方必须提供这三个变量
    env:
      GOOS: '{{.GOOS}}'              # 跨平台编译只需这两个环境变量
      GOARCH: '{{.GOARCH}}'
    cmds:
      - '{{.GO}} build -o {{.OUTPUT}} main.go'

  build:linux:           # 对外目标：填好变量再调 cross-build
    cmds:
      - task: cross-build
        vars: { GOOS: linux, GOARCH: amd64, OUTPUT: 'bin/spark_linux' }
```

要点逐条：

- **`vars`**：静态值直接写；`sh:` 开头表示运行 shell 命令取结果
- **`cmds`**：按顺序执行；`task:` 引用别的任务（相当于函数调用）
- **`platforms`**：同一条目按操作系统分派，这是跨平台的核心
- **`internal: true`**：内部任务，`task --list` 不显示
- **`requires.vars`**：强制调用方传参，漏了会直接报错
- **`{{exeExt}}`**：Task 内置变量，Windows 上是 `.exe`，其他平台空串
- **`ignore_error: true`**：容忍失败继续（如 `test-report` 里先跑完所有测试再出报告）

最小可用模板（新项目直接抄）：

```yaml
version: '3'

vars:
  BINARY_NAME: mycli
  BIN_DIR: bin

tasks:
  build:
    desc: Build for the current OS
    cmds:
      - go build -o {{.BIN_DIR}}/{{.BINARY_NAME}}{{exeExt}} .

  test:
    desc: Run all tests
    cmds:
      - go test ./...

  lint:
    desc: Run go vet
    cmds:
      - go vet ./...

  clean:
    desc: Remove build artifacts
    cmds:
      - cmd: powershell -NoProfile -Command "Remove-Item -Recurse -Force {{.BIN_DIR}}"
        platforms: [windows]
      - cmd: rm -rf {{.BIN_DIR}}
        platforms: [linux, darwin]
```

安装 Task 本体：`go install github.com/go-task/task/v3/cmd/task@latest`，
然后 `task --list` 查看全部目标，`task build` 开始使用。
Makefile 与 Taskfile 在本项目中目标一一对应，Linux/macOS 用户用 `make` 也行。

## 6. 收尾：提交前的清单

```text
✅ go.mod / go.sum 已提交（绝不能进 .gitignore）
✅ bin/ 已加入 .gitignore（构建产物不入库）
✅ go mod tidy 跑过，没有多余依赖
✅ go vet ./... 通过
✅ go test ./... 通过
```

Windows 安装到 `~/.local/bin` 时，记得同时放 `mycli.exe` 与无后缀的
`mycli` 两份（bash 优先命中后者），这是 spark 的 `install-binary.ps1` 的做法。

---

## 附录：SKILL —— golang-project-from-scratch

保存为 `SKILL.md`（如 `.claude/skills/golang-project-from-scratch/SKILL.md`），
AI 助手即可按 spark 的标准流程帮你从零创建 Go CLI 项目：

```markdown
---
name: golang-project-from-scratch
description: 按标准流程从零创建一个 Go CLI 项目（go mod init、Cobra/Viper/PTerm
  三件套、cmd+internal 分层、Taskfile 构建）。当用户要求"新建 Go CLI 项目 /
  搭 Go 项目骨架 / 标准化 Go 项目结构"时使用。
---

# 从零创建标准 Go CLI 项目

按以下顺序执行，每步完成后向用户确认再继续：

1. **模块初始化** — `go mod init <module-path>`（模块路径用仓库地址）；
   解释 go.mod 的 module/go 行，声明 go.mod 与 go.sum 必须提交。
2. **依赖安装** — 按需 `go get`：cobra（命令）、viper（配置）、pterm（输出）、
   bubbletea（TUI）、ginkgo+gomega（BDD 测试）；收尾 `go mod tidy`。
3. **目录分层** — main.go 只调 cmd.Execute()；cmd/ 定义命令（每个子命令一个
   文件，init() 里 AddCommand 自注册）；业务逻辑全部进 internal/；需要被外部
   复用的才进 pkg/；构建辅助脚本进 scripts/。
4. **第一个命令** — 根命令 + 一个演示子命令（Use/Short/RunE 三件套，RunE 返回
   error）；`go run .` 验证后 `go build -o bin/<name> .`。
5. **Taskfile** — 写 Taskfile.yml（vars/cmds/platforms 三要素；交叉编译用
   GOOS/GOARCH + requires.vars 的内部 cross-build task；{{exeExt}} 处理后缀）；
   提供 build/test/lint/clean 四个基础目标。
6. **收尾** — .gitignore 掉 bin/；跑 go vet ./... 与 go test ./...。

参考实现：github.com/variableway/spark-cli（Cobra+Viper+PTerm，Makefile 与
Taskfile 双入口）。构建细节参考其 docs/zh/usage/how-to-build.md。
```

---

## 延伸阅读

- [Golang CLI 入门 · 第一课](golang-cli-101.md) —— 概念课，先学这个再看本篇
- [How to Build — 构建指南](../usage/how-to-build.md) —— 已有项目的构建、交叉编译与 pnpm 环境
- [从零创建文档站](docs-site-from-scratch.md) —— 本项目的另一半：Node 体系
