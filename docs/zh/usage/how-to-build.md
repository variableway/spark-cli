# How to Build — 构建指南

spark 项目里有**两种产物、两套构建体系**，思路其实一样——都是
「安装工具链 → 拉依赖 → 编译/打包 → 产物放好」：

| 产物 | 体系 | 依赖管理 | 任务入口 | 产物 |
|------|------|----------|----------|------|
| `spark` 命令行 | **Go** | `go.mod` / `go.sum` | `Makefile` / `Taskfile.yml` | 单个二进制 `spark(.exe)` |
| 文档站 | **Node** | `package.json` / `pnpm-lock.yaml` | `package.json` 的 scripts | 静态站点 `site/` |

> 换个说法：Go 构建的是「一个可执行文件」，Node（文档站）构建的是「一堆 HTML 页面」。
> Go 用 `go build`，Node 用 `docmd build`，只是工具名字不同。

---

## 一、Go 二进制（golang 体系）

### 构建并安装

```bash
# Linux / macOS
make build

# Windows（make 不可用时用 task，二者等价）
task build
```

执行内容：

1. `go build -ldflags='...version stamp...' -o bin/spark.exe main.go`
   —— 产物统一落在项目的 `bin/` 目录；version / commit / build date 编译进二进制
2. `scripts/install-binary.ps1`（或 `.sh`）安装到 `~/.local/bin/`
   Windows 下会同时写 `spark.exe` 与无后缀的 `spark`（bash 优先命中后者，两者必须一致）
3. `scripts/verify-install.ps1` 做 sha256 一致性校验

自检：

```bash
spark version    # -> spark v0.3.2 / commit xxx / build date ...
spark --version  # -> spark version v0.3.2
```

### 交叉编译

Go 交叉编译只需换环境变量，不需要额外工具链：

```bash
task build:windows        # bin/spark_windows.exe       (amd64)
task build:windows:arm64  # bin/spark_windows_arm64.exe (arm64)
task build:linux          # bin/spark_linux
task build:darwin         # bin/spark_darwin
task build:all            # 全平台，产物都在 bin/（gitignore 掉，不入库）
```

### 测试与静态检查

```bash
task test           # go test ./...
task test-bdd       # ginkgo BDD 测试
task lint           # go vet ./...
```

---

## 二、文档站（Node 体系）

文档站是标准的 Node 项目，和「golang 用 go.mod 管依赖」完全对等：

| Go | Node（本项目） | 作用 |
|----|----------------|------|
| `go.mod` | `package.json` | 声明项目与依赖 |
| `go.sum` | `pnpm-lock.yaml` | 锁定依赖版本 |
| `go get <pkg>` | `pnpm add <pkg>` | 添加依赖 |
| `go mod tidy` | `pnpm install` | 按声明安装依赖 |
| `go build` | `pnpm build`（`docmd build`） | 编译/生成产物 |
| `go run` | `pnpm dev` | 本地跑起来看效果 |
| `~/.cache/go-build` | `D:\.pnpm-store` | 依赖缓存（省磁盘，可指到 D 盘） |

### 构建命令

```bash
pnpm install    # 安装依赖（硬链接自 pnpm store）
pnpm build      # docmd build -> site/（zh 在根，en 在 /en/）
pnpm dev        # 本地开发预览
pnpm preview    # 构建后静态预览 site/
```

构建结果：`site/` 下 50+ 静态页面，含搜索索引、sitemap、llms.txt。
配置在 `docmd.config.js`（`i18n.default: 'zh'`：中文渲染在根 URL，英文在 `/en/`）。

---

## 三、Bun：Node 体系也能 build binary

前面说「Go 出二进制、Node 出 HTML」——**不完全对**。用
[Bun](https://bun.sh) 的 `bun build --compile`，TypeScript/JavaScript 也能
编译成**自带运行时的单个二进制**，和 Go 的产物一样拿到任何机器直接跑：

```bash
bun build src/index.ts --compile --outfile mycli        # 当前平台
bun build src/index.ts --compile --target bun-windows-x64 --outfile mycli.exe
bun build src/index.ts --compile --target bun-darwin-arm64 --outfile mycli-mac
bun build src/index.ts --compile --target bun-linux-x64 --outfile mycli-linux
```

真实的例子：`innate-fe-cli`（25 个模块、零 npm 运行时依赖）一条命令打出
约 96MB 的 `innate-fe-cli.exe`，装进 `~/.local/bin` 后全局可用：

```bash
cd innate-fe-cli && bun install && bun run build:exe:win
cp ../../bin/innate-fe-cli.exe ~/.local/bin/

# Windows：多个命令名共享一份磁盘数据（NTFS 硬链接）
cd ~/.local/bin
fsutil hardlink create innate-fe innate-fe-cli.exe
fsutil hardlink create innate-fe.exe innate-fe-cli.exe
```

| | Go | Bun (`--compile`) | Node（docmd 这类） |
|--|----|-------------------|--------------------|
| 产物 | 单二进制 | 单二进制 | 需要 `node`/`pnpm` 运行 |
| 交叉编译 | `GOOS/GOARCH` | `--target bun-<os>-<arch>` | 无（纯 JS 包） |
| 体积 | ~17MB | ~96MB（含 Bun 运行时） | KB 级 + node_modules |
| 适用 | 系统工具 CLI | 前端工程 CLI | 文档站 / 构建脚本 |

> 记忆点：**Go 和 Bun 都能「编译出一个文件发给大家」；普通 Node 项目只能
> 「发源码 + node_modules」**。选型看分发方式。

---

## 四、Windows 上的 pnpm 环境（省 C 盘）

目标：pnpm 全局可用，且 **store / 全局包 / 全局 bin 都落在 D 盘**。

```bash
npm i -g pnpm@latest     # pnpm CLI 本体很小，留在 Node 全局前缀即可

pnpm config set store-dir      "D:\.pnpm-store"  --global
pnpm config set global-dir     "D:\pnpm\global"  --global
pnpm config set global-bin-dir "D:\pnpm\bin"     --global
```

校验：

```bash
pnpm store path   # -> D:\.pnpm-store\v11
pnpm root -g      # -> D:\pnpm\global\v11
pnpm bin -g       # -> D:\pnpm\bin
```

Windows 环境变量：

| 变量 | 值 |
|------|----|
| `PNPM_HOME`（用户级） | `D:\pnpm` |
| `Path`（用户级） | 以 `D:\pnpm\bin` 开头（替换旧的 `%LOCALAPPDATA%\pnpm*` 条目） |

```powershell
[Environment]::SetEnvironmentVariable('PNPM_HOME', 'D:\pnpm', 'User')
$p = [Environment]::GetEnvironmentVariable('Path', 'User')
$parts = $p -split ';' | Where-Object { $_.Trim() -ne '' -and $_ -notlike '*\AppData\Local\pnpm*' }
$parts = @('D:\pnpm\bin') + $parts
[Environment]::SetEnvironmentVariable('Path', ($parts -join ';'), 'User')
```

> **注意**：不要用 `setx` 改 PATH——超过 1024 字符会被截断，长 PATH 会被破坏。
> 请用 `[Environment]::SetEnvironmentVariable(...)`；过滤路径用 `-notlike`
> 而不是 `-notmatch`（正则里的 `\L` 是非法转义，会把条目全部滤掉）。
> 改完需**重开终端**。

---

## 五、常见问题

| 现象 | 处理 |
|------|------|
| `pnpm bin -g` 报 `ERR_PNPM_GLOBAL_BIN_DIR_NOT_IN_PATH` | 把 `D:\pnpm\bin` 加入 PATH 后重开终端 |
| `setx PATH` 后工具链大面积找不到 | PATH 被截断，按上文用 `[Environment]::SetEnvironmentVariable` 重建 |
| PowerShell 过滤 PATH 报“无法识别的转义序列” | 改用 `-notlike '*\AppData\Local\pnpm*'` |
| docmd 提示 Rust engine not supported | 自动回退 JS 引擎，可正常构建；如需原生引擎，放开 `pnpm-workspace.yaml` 中 `@docmd/engine-rust` 的 `allowBuilds` |
| `make` 不存在（Windows） | 用 `task`（`Taskfile.yml` 提供等价目标） |
