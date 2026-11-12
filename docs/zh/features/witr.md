# 进程诊断

## 功能概述

`spark witr`（Why Is This Running）回答"这个进程或端口为什么在运行"。它不只报出一个 PID，而是把进程的来龙去脉摊开：谁启动了它、由哪个服务管理器托管、跑在哪个容器里、监听了哪些端口、打开了哪些文件。

平时排查这些问题需要来回切换 `ps`、`lsof`、`docker ps`、`systemctl`、launchd 等工具再人工拼接。witr 把这些来源合并成一次查询，顺带给出风险提示，例如进程以 root 运行、工作目录可疑、监听在公开接口、环境变量里出现了 `LD_PRELOAD`。

## 核心能力

### 祖先链与来源识别

witr 从目标进程向上追溯父进程链，把"谁启动了谁"直接列出来。链条的源头还会被识别成一个具体的来源类型：

| 来源类型 | 说明 |
|----------|------|
| `container` | 进程由容器运行时拉起 |
| `systemd` | 由 systemd 单元管理 |
| `launchd` | 由 launchd 服务管理（macOS） |
| `bsdrc` | 由 BSD rc 脚本启动 |
| `supervisor` | 由 supervisor 等进程管理器拉起 |
| `cron` | 由定时任务拉起 |
| `ssh` | 由 SSH 会话拉起 |
| `shell` | 由交互式 shell 拉起 |
| `windows_service` | 由 Windows 服务拉起 |
| `init` | 由系统 init 进程拉起 |

识别不出已知来源时，来源标记为 `unknown`，并作为一条警告提示"没有检测到已知的服务管理器或进程管理器"。

### 采集的数据

一次查询会覆盖以下几类信息：

- **进程**：PID、PPID、命令、完整命令行、可执行文件路径、启动时间、运行用户、工作目录、所属的 Git 仓库与分支、容器、服务名、健康状态、是否 fork
- **网络**：进程持有的全部 socket（协议与状态，例如 `LISTEN`、`ESTABLISHED`、`CLOSE_WAIT`、`TIME_WAIT`）。按端口查询时还会给出该端口 socket 状态的解释与规避建议，例如 `TIME_WAIT` 会说明"等待约 60 秒由操作系统释放，或在代码中启用 `SO_REUSEADDR`"
- **容器**：容器运行时、ID、名称、镜像、命令、状态、创建与启动时间、网络、挂载点、端口映射，以及 compose 项目与服务名
- **环境变量**：进程的环境变量列表（`--env`）
- **扩展信息**（`--verbose`）：内存明细、I/O 统计、文件描述符列表、fd 数量与上限、子进程、线程数；macOS 上还包含能耗影响、是否阻止系统睡眠、thermal 状态、CPU 与内存占用
- **文件上下文**：打开的文件数、fd 上限、进程持有的文件锁、监听的目录

### 风险提示

witr 会把可疑之处汇总成警告列表：

- 进程或祖先重启超过 5 次
- 僵尸进程（`zombie`）、已停止的进程（`stopped`）、高 CPU、高内存
- 监听在公开接口（`0.0.0.0` 或 `::`）
- 以 root 运行，或持有危险 capabilities（如 `CAP_SYS_ADMIN`、`CAP_SYS_PTRACE`）
- 运行超过 90 天
- 工作目录可疑（`/`、`/tmp`、`/var/tmp`）
- 从已删除的可执行文件运行
- 容器缺少 healthcheck（尽力而为的检查，snap 与 flatpak 除外）
- 服务名与进程名不匹配
- 环境变量可疑：`LD_PRELOAD` 或 `DYLD_*` 形式的库注入

### 查询目标

除了直接给出进程名，还支持四种标志查找方式：

| 目标 | 方式 | 说明 |
|------|------|------|
| 进程名 | 位置参数 | 默认按子串匹配进程名与命令行；`--exact` 改为精确匹配命令行中的完整词元 |
| PID | `--pid` | 直接指定 PID，PID 必须是正整数 |
| 端口 | `--port` | 查找监听该端口的进程，端口范围 1–65535 |
| 文件 | `--file` | 查找打开该文件的进程，Windows 上不支持 |
| 容器 | `--container` | 按名称、镜像或命令匹配容器，覆盖 docker、podman、nerdctl、crictl 与 jail |

同一命令里可以混用多种目标，多个目标按命令行顺序依次处理。

### 机器可读输出

`--json` 把结果转成 JSON，便于脚本消费：单个目标输出对象，多个目标输出数组，查询失败的项以 `{"Target": ..., "Error": ...}` 并入数组。配合 `--short`、`--tree`、`--warnings`、`--env` 时，JSON 的结构相应收窄，只保留对应视图需要的字段。

### 典型场景

- 端口被占用、服务起不来：`spark witr --port 8080`，看清是谁占着端口、它由谁拉起
- 后台进程来源不明：`spark witr node --tree`，展开整条父子链
- 容器排查：`spark witr --container redis`，拿到镜像、端口映射和 compose 归属
- 文件锁冲突：`spark witr --file /var/lib/dpkg/lock`，定位持锁进程
- 进程环境变量核对：`spark witr --pid 1234 --env`
- 接入自动化流水线：`spark witr --port 8080 --json`，交给 `jq` 或其他脚本处理

## 使用参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--pid` | strings | | 按 PID 查询，可重复传入 |
| `--port` | strings | | 按端口查询，可重复传入 |
| `--file` | strings | | 按打开的文件查询，可重复传入 |
| `--container` | strings | | 按容器查询，可重复传入 |
| `--json` | bool | `false` | 输出机器可读的 JSON |

完整标志列表见命令规格页。

## 相关文档

- [Witr 命令规格](../spec/witr.md)
- [Witr 使用指南](../usage/witr.md)
