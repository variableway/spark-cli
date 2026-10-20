# Golang CLI 入门 · 第一课

面向零基础：用 spark 项目当例子，搞懂「一个 Go 命令行工具是怎么炼成的」。
学完你应该能回答四个问题：

1. Go 写 CLI 的**基本技术**是什么？
2. 怎么**使用第三方仓库**（别人写好的轮子）？
3. 怎么**管理依赖**（版本锁定、升级、清理）？
4. **Makefile / Taskfile** 是干什么用的？

---

## 1. 基本技术：一个 CLI = 一个 Go 程序

Go 编译出来的是**单一可执行文件**，不需要用户装运行时。一个 CLI 项目的
骨架通常是：

```
main.go            入口：一行调用 cmd.Execute()
cmd/               每个「命令 / 子命令」一个文件
internal/          业务逻辑（外部看不到，强制你分层）
go.mod             依赖清单（像购物小票）
go.sum             依赖的校验和（防篡改）
```

以 spark 为例，`main.go` 只有几行：

```go
package main

import "spark/cmd"

func main() {
    cmd.Execute()
}
```

命令怎么定义？靠第三方库 **Cobra**——「命令 + 子命令 + flag」三件套：

```go
var flushDNSCmd = &cobra.Command{
    Use:   "flush-dns",
    Short: "Flush DNS cache",
    RunE: func(cmd *cobra.Command, args []string) error {
        return magic.FlushDNS()   // 真正干活的逻辑放 internal/
        },
}
```

配置怎么读？靠 **Viper**——自动从 `~/.spark.yaml`、环境变量、命令行 flag
按优先级取值（命令行 > 配置文件 > 环境变量）。

终端好看的表格/颜色？**PTerm**。交互式 TUI？**Bubble Tea**。

> 记忆点：**Cobra 管命令，Viper 管配置，PTerm 管输出，internal/ 管逻辑。**

## 2. 使用第三方仓库

Go 的第三方包就是「一个 Git 仓库」，导入路径 = 仓库地址：

```go
import (
    "github.com/spf13/cobra"   // 命令行框架
    "github.com/spf13/viper"   // 配置读取
    "github.com/pterm/pterm"   // 终端美化
)
```

安装（下载并登记到 go.mod）：

```bash
go get github.com/spf13/cobra@latest
```

然后 `go build` 时会自动把这些源码编译进你的二进制——**没有 node_modules，
产物还是一个文件**。

怎么找轮子？记住三个高频关键词：`cobra`（CLI 框架）、`viper`（配置）、
`bubbletea`（TUI）。

## 3. 如何管理依赖

| 文件 | 作用 | 类比 |
|------|------|------|
| `go.mod` | 项目声明：模块名、Go 版本、依赖列表 | Node 的 `package.json` |
| `go.sum` | 每个依赖的哈希校验 | Node 的 `pnpm-lock.yaml` |

常用命令：

```bash
go get  <pkg>@latest   # 添加/升级某个依赖
go mod tidy            # 自动补缺失的、删没用到的（最常用）
go mod download        # 只下载依赖到本地缓存
go list -m all         # 看当前所有依赖及版本
```

三条好习惯：

1. **`go.mod`/`go.sum` 一定要提交进 Git**（别人 clone 后才能复现构建）
2. 升级依赖优先 `go get pkg@latest` 而不是手改版本号
3. 发现依赖太多时跑一次 `go mod tidy`，它会帮你清理

缓存在 `GOCACHE`/`GOMODCACHE`（默认 C 盘），构建换机器不用重新下载。

## 4. Makefile / Taskfile 是干什么的

把「常用的长命令」变成「一个短命令」的任务清单，**不是编程语言，
只是命令的快捷方式**。

| 你想做的事 | 不用 Makefile | 用 Makefile / Taskfile |
|------------|---------------|------------------------|
| 构建 | `go build -ldflags='...' -o spark.exe main.go` | `make build` / `task build` |
| 测试 | `go test ./... -v` | `make test` / `task test` |
| 交叉编译 | `GOOS=windows GOARCH=amd64 go build ...` | `task build:windows` |
| 清理 | 手动删文件 | `make clean` / `task clean` |

- **Makefile**：Unix 世界标配（`make`），Linux/macOS 自带；
  Windows 上需要额外安装，所以本项目提供等价的——
- **Taskfile.yml**：Go 写的任务工具（`task`），跨平台，Windows 上体验更好。

两者在本项目中目标一一对应（`build` / `test` / `lint` / `clean`…），
挑一个用就行。打开 `Taskfile.yml` 看一眼，每个 `tasks:` 下的 `cmds:`
就是「按下这个按钮时执行哪些命令」。

---

## 5. 那文档站呢？（Node 体系）

`docs/` 文档站是另一个世界：**Node + pnpm + docmd**，构建思路和 Go 一样——
`pnpm install`（≈ go mod tidy）→ `pnpm build`（≈ go build）→ 产物在 `site/`。
详细对照表见 [How to Build](../usage/how-to-build.md)。

---

## 附录 A：课程 Prompt（复制给 AI 助手即可开课）

```text
你是我的 Go CLI 入门导师。我是零基础，请用 spark-cli 项目作为教材，
按下面四课教我，每课：概念一句话 + 一个能跑的小例子 + 一个小练习。
1) 基本技术：main.go / cmd/ / internal/ 分层，Cobra 命令与 flag，Viper 配置
2) 使用第三方仓库：import 路径 = 仓库地址，go get 用法
3) 依赖管理：go.mod / go.sum 的作用，go mod tidy，版本升级
4) Makefile 与 Taskfile：为什么需要任务清单，怎么读懂 target
要求：一次只讲一课；优先用项目里的真实文件举例；练习题要能在 Windows
上 5 分钟内做完；我答完再进下一课。
```

## 附录 B：Skill（SKILL.md，可安装为 Agent 技能）

保存为 `SKILL.md`（如放到 `~/.codex/skills/golang-cli-101/SKILL.md` 或
`.claude/skills/golang-cli-101/SKILL.md`）即可作为「CLI 第一课」技能调用：

```markdown
---
name: golang-cli-101
description: Go CLI 零基础入门第一课。当用户想学习用 Go 写命令行工具、
  看懂 go.mod/Cobra/Makefile，或要求"CLI 入门/第一课"时使用。
---

# Go CLI 入门第一课

用项目真实文件做教材，按顺序教四课，每课一个 5 分钟练习：

1. **基本技术** — 读 `main.go`、`cmd/`（Cobra 命令）、`internal/`（业务逻辑）；
   讲清「命令 → flag → 业务函数」的调用链。
2. **第三方仓库** — 以 `github.com/spf13/cobra`、`spf13/viper`、`pterm/pterm`
   为例：import 路径即仓库地址，`go get` 安装后编译进单个二进制。
3. **依赖管理** — `go.mod`（清单）+ `go.sum`（校验）；演示 `go mod tidy`
   与 `go get pkg@latest`；强调两个文件必须提交。
4. **Makefile / Taskfile** — 打开 `Makefile` 与 `Taskfile.yml` 对照
   `build/test/lint/clean` 目标，解释它们只是命令快捷方式。

教学规则：一次一课；中文讲解、代码保持英文；每课结束出 1 道练习并等待
作答；全部完成后给出「继续深入」的三个方向（flag 绑定、表驱动测试、交叉编译）。
```

---

下一步：跑一遍 `task build`（Windows）或 `make build`，再执行
`spark version` 验证——你就完成了第一课的毕业构建。
