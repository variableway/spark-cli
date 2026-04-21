# Subcommand Design Rules

Go CLI 应用的子命令设计规范和最佳实践。

## 命令层级设计

### 三层结构

```
app                    # Level 0: 根命令
├── domain             # Level 1: 领域/功能域
│   ├── action         # Level 2: 动作/操作
│   └── action2
└── domain2
    └── action
```

### 实际示例（spark-cli）

```
spark                            # 根命令
├── git                          # 领域：Git 仓库管理
│   ├── update                   # 动作：更新仓库
│   ├── mono                     # 子领域：Mono 仓库
│   │   ├── add                  # 动作：添加子模块
│   │   └── sync                 # 动作：同步子模块
│   ├── config                   # 动作：配置
│   ├── url                      # 动作：获取 URL
│   ├── batch-clone              # 动作：批量克隆
│   ├── update-org-status        # 动作：更新组织状态
│   └── issues                   # 动作：管理 Issues
├── task                         # 领域：任务管理
│   ├── init                     # 动作：初始化
│   ├── list                     # 动作：列出
│   ├── create                   # 动作：创建
│   ├── delete                   # 动作：删除
│   ├── impl                     # 动作：实现
│   ├── dispatch                 # 动作：分发
│   └── sync                     # 动作：同步
├── agent                        # 领域：AI 代理配置
│   ├── list
│   ├── view
│   ├── edit
│   ├── reset
│   └── profile                  # 子领域
│       ├── list
│       ├── add
│       └── edit
├── script                       # 领域：脚本管理
│   ├── list
│   └── run
├── magic                        # 领域：系统工具
│   ├── flush-dns
│   ├── pip                      # 子领域：pip 镜像
│   │   ├── list
│   │   ├── use
│   │   └── current
│   ├── go                       # 子领域：Go 代理
│   └── node                     # 子领域：npm 镜像
└── docs                         # 领域：文档
    ├── init
    └── site
```

## 命名约定

### 命令名称

| 层级 | 风格 | 示例 | 说明 |
|------|------|------|------|
| Level 1 | 名词 | `git`, `task`, `agent` | 表示功能域 |
| Level 2 | 动词 | `list`, `create`, `delete` | 表示操作 |
| Level 2（子域） | 名词 | `mono`, `profile`, `pip` | 嵌套功能域 |
| Level 3 | 动词 | `add`, `sync` | 子域操作 |

### 常用动作词

| 动词 | 用途 | 示例 |
|------|------|------|
| `list` | 列出资源 | `spark task list` |
| `create` | 创建资源 | `spark task create my-task` |
| `delete` | 删除资源 | `spark task delete my-task` |
| `init` | 初始化 | `spark task init` |
| `update` | 更新 | `spark git update` |
| `sync` | 同步 | `spark task sync` |
| `view` / `show` | 查看 | `spark agent view claude-code` |
| `edit` | 编辑 | `spark agent edit claude-code` |
| `run` | 执行 | `spark script run deploy` |
| `dispatch` | 分发 | `spark task dispatch my-task` |
| `impl` | 实现 | `spark task impl my-feature` |
| `reset` | 重置 | `spark agent reset claude-code` |
| `use` | 切换/应用 | `spark magic pip use tsinghua` |
| `current` | 显示当前 | `spark magic pip current` |
| `add` | 添加 | `spark git mono add` |
| `flush` | 清除 | `spark magic flush-dns` |

### 复合命令命名

多个单词用 `-` 连接：
- `batch-clone`（批量克隆）
- `flush-dns`（刷新 DNS）
- `update-org-status`（更新组织状态）

### Flag 命名

```go
// 长标志：kebab-case
--task-dir
--work-dir
--dry-run
--skip-push

// 短标志：单字母（常用缩写）
-o  // --output
-p  // --path
-s  // --ssh

// 布尔标志：正面表述
--force      // 不是 --no-confirm
--tui        // 不是 --no-cli
--dry-run    // 不是 --no-write
```

## 代码组织

### 文件结构

每个一级命令一个目录，二级命令一个文件：

```
cmd/
├── root.go                 # 根命令
├── task.go                 # spark task（Level 1）
├── agent.go                # spark agent（Level 1）
├── git/                    # spark git（Level 1 目录）
│   ├── git.go              # 父命令 + init()
│   ├── update.go           # spark git update
│   ├── config.go           # spark git config
│   ├── mono.go             # spark git mono
│   ├── mono_add.go         # spark git mono add
│   └── batch_clone.go      # spark git batch-clone
├── magic/                  # spark magic
│   ├── magic.go
│   ├── flush_dns.go
│   └── pip.go
└── script/                 # spark script
    ├── script.go
    ├── list.go
    └── run.go
```

### 注册模式

```go
// cmd/git/git.go
package git

var GitCmd = &cobra.Command{
    Use:   "git",
    Short: "Git repository management commands",
}

func init() {
    // 子命令通过各自的 init() 自动注册
}
```

```go
// cmd/git/update.go
package git

var updateCmd = &cobra.Command{
    Use:   "update",
    Short: "Update all repos to latest version",
    RunE: func(cmd *cobra.Command, args []string) error {
        return nil
    },
}

func init() {
    GitCmd.AddCommand(updateCmd)
}
```

```go
// cmd/root.go
func init() {
    rootCmd.AddCommand(git.GitCmd)
    rootCmd.AddCommand(magic.MagicCmd)
    rootCmd.AddCommand(script.ScriptCmd)
}
```

## Flag 分类

### Persistent vs Local

```go
// Persistent: 所有子命令继承
taskCmd.PersistentFlags().BoolVar(&useTUI, "tui", false, "Enable TUI mode")
taskCmd.PersistentFlags().StringVar(&taskDir, "task-dir", "", "Task directory")

// Local: 仅当前命令
taskCreateCmd.Flags().String("content", "", "Custom content")
taskDeleteCmd.Flags().Bool("force", false, "Force deletion")
```

### 配置绑定

```go
// Flag → Viper → YAML
taskCmd.PersistentFlags().StringVar(&taskDir, "task-dir", "", "Task directory")
viper.BindPFlag("task_dir", taskCmd.PersistentFlags().Lookup("task-dir"))

// ~/.spark.yaml 中对应:
// task_dir: /path/to/tasks
```

## 帮助文本规范

```go
var cmd = &cobra.Command{
    Use:   "command <required-arg> [optional-arg]",
    Short: "一句话描述",   // 出现在父命令的帮助中
    Long: `详细描述，可以多行。

包含：
- 功能说明
- 使用前提
- 注意事项`,
    Example: `  spark task create my-feature
  spark task create my-feature --content "Custom description"`,
    Args: cobra.ExactArgs(1), // 或 MaximumNArgs(1), NoArgs 等
}
```
