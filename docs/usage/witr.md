# spark witr — 进程诊断

检查进程或端口为何在运行，追溯进程祖先链。witr（Why Is This Running）是集成在 Spark 中的进程诊断工具。

## 命令速查

```bash
spark witr nginx                              # 按名称检查进程
spark witr --pid 1234                         # 按 PID 检查
spark witr --port 8080                        # 按端口查找进程
spark witr --file /var/lib/dpkg/lock          # 查找占用文件的进程
spark witr --container redis                  # 检查容器
spark witr nginx --tree                       # 显示进程树
spark witr nginx --env                        # 显示环境变量
spark witr nginx --json                       # JSON 输出
spark witr nginx --short                      # 单行输出
spark witr nginx --warnings                   # 仅显示警告
spark witr nginx --verbose                    # 扩展信息
spark witr --port 8080 --env --json           # 组合标志
```

---

## 基本用法

### 按名称查找

```bash
spark witr nginx
spark witr nginx --exact                      # 精确匹配，不模糊搜索
```

### 按 PID 查找

```bash
spark witr --pid 1234
spark witr --pid 1234,5678                    # 多个 PID
```

### 按端口查找

```bash
spark witr --port 8080
spark witr --port 8080,3000                   # 多个端口
```

### 按文件查找

```bash
spark witr --file /var/lib/dpkg/lock
```

### 按容器查找

```bash
spark witr --container redis
```

---

## 输出模式

| 标志 | 简写 | 说明 |
|------|------|------|
| `--tree` | `-t` | 仅显示进程祖先树 |
| `--short` | `-s` | 简短单行输出 |
| `--env` | | 显示进程环境变量 |
| `--verbose` | | 显示扩展信息（内存、I/O、文件描述符） |
| `--warnings` | | 仅显示警告（可疑环境、参数、父进程） |
| `--json` | | JSON 格式输出 |
| `--no-color` | | 禁用颜色（适合 CI 或管道） |

---

## 混合查询

支持同时查询多个目标：

```bash
spark witr nginx node                         # 多个进程名称
spark witr --port 8080 --port 3000            # 多个端口
spark witr --pid 1234 --pid 5678              # 多个 PID
spark witr nginx --pid 1234 --port 8080       # 混合查询
```

---

## 交互模式

无参数或仅使用交互标志时启动 TUI：

```bash
spark witr                                    # 启动交互式 TUI
spark witr --interactive                      # 显式启动 TUI
spark witr -i                                 # 简写
```

## 相关命令

- [系统工具](./magic.md)
- [Git 管理](./git.md)
