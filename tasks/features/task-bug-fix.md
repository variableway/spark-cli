# Task 1: Spark Task Sub Command Bug fix 

## 描述

1. ~~after make build and make install, the command is still using the old verion for spark not the latest spark version~~ **(已修复：见下方说明)**
2. `spark task create "make script issue" --content` 这个命令使用的时候出现一个问题，就是example-feature.md文件内容没有复制到make script issue.md文件中。
   同时文件名需要把描述中的空格变成-
3. create的时候吧content参数的内容也，复制到新创建目录的## 描述 section下面


## 验收标准

- [x] 添加对应的单元测试 (`cmd/version_test.go`：注册、`--version`、`spark version` 输出)
- [x] 更新 README 使用说明 (Taskfile `verify-install`、`spark version`、`--version`)
- [] 更新AGENTS.md文件

### Task 1.1 修复说明（Windows 安装覆盖）

**根因**：`make install` / `task install` 在 Windows 上同时存在两个安装产物：
- `~/.local/bin/spark.exe`（`go build` 的产物）
- `~/.local/bin/spark`（一个去后缀名的旧拷贝，由 `Copy-Item spark.exe ~/.local/bin/spark` 创建）

Bash 在 PATH 中匹配 `spark` 时会先命中**带去后缀名的文件**，所以如果某次构建只更新了 `spark.exe`（例如手动 `cp`、或老 `task install` 失败），旧的 `spark` 影子就会让 `spark` 命令始终指向陈旧二进制。

**改动**：
1. `Taskfile.yml` 与 `Makefile` 的 install 步骤同时原子刷新 `spark.exe` 和 `spark`（去后缀名）；
2. 通过 `-ldflags "-X spark/internal/witr/version.Version=v..."` 把 `internal/witr/version/VERSION` 注入二进制，构建期 `commit`/`build date` 也一并写入；
3. 安装后立即调用 `scripts/verify-install.ps1` / `verify-install.sh` 打印源文件与安装产物的 sha256、字节数、修改时间，**两者必须一致**，否则 install 步骤以非零退出；
4. `cmd/version.go` 注册 `spark version` 子命令 + `rootCmd.Version`，Cobra 自动添加 `--version` / `-v`，用户在升级任何问题出现时一行命令自检：
   ```
   $ spark version
   spark v0.3.2
     commit:     1ef84d7
     build date: 2026-07-10T02:25:51Z
   ```


## Task 2: 使用 Spark task impl 《feature—name》报错

## 描述
使用 Spark task impl 《feature—name》报错运行报错：

```
INFO  Step 1/3: Initializing workflow...

Error creating issue: GitHub API error: 403 - {"message":"Resource not accessible by personal access token","documentation_url":" https://docs.github.com/rest/issues/issues#create-an-issue ","status":"403"}

Error: failed to initialize workflow: exit status 1

Usage:
```

但是直接在kimi-cli中执行，issue是可以创建的，请检查什么地方问题，并且修复.

## Task 3: Fix Resource Top Command K to Kill process

- 在Resource Top 之后，点击K不可以杀死进程，需要修复
