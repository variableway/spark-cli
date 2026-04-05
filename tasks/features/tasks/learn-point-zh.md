# Git-Monolize 项目学习要点

本文档总结了 Git-Monolize 项目的关键技术点和使用方法。

---

## 1. 项目技术栈总结
- **编程语言**: Go 1.24.2
- **CLI 框架**: [Cobra](https://github.com/spf13/cobra) - 强大的 CLI 应用程序构建框架。
- **配置管理**: [Viper](https://github.com/spf13/viper) - 通用的 Go 配置解决方案。
- **测试框架**: [Ginkgo](https://onsi.github.io/ginkgo/) & [Gomega](https://onsi.github.io/gomega/) - BDD 风格的测试框架和断言库。
- **构建系统**: Makefile - 支持多平台（Windows, Linux, macOS）。
- **环境管理**: 通过 `.vscode` 配置实现的 VS Code 集成。

---

## 2. CLI 使用指南（非技术人员）
该工具旨在管理多个 Git 仓库。

### 1. 如何获取帮助？
如果您不确定任何命令的用法，请使用 `-h` 或 `--help` 标志：
```bash
monolize --help
monolize update --help
```

### 2. 传递参数
参数允许您指定命令的运行方式。大多数参数使用 `--key value` 或 `-k value` 格式：
- **路径 (Path)**: 使用 `--path` 或 `-p` 告诉工具您的仓库所在位置。
- **名称 (Name)**: 使用 `--name` 或 `-n` 为新的 mono-repo 指定名称。
- **输出 (Output)**: 使用 `--output` 指定结果保存位置。

### 3. 设置环境变量 (Path)
为了在任何地方都能使用 `monolize`，请将其添加到系统的 PATH 中。
- **Windows**:
    1. 在系统属性中打开“环境变量”。
    2. 编辑“用户变量”下的“Path”。
    3. 添加 `monolize.exe` 所在的文件夹路径。
- **Linux / macOS**:
    1. 打开您的 shell 配置文件（例如 `~/.bashrc` 或 `~/.zshrc`）。
    2. 添加：`export PATH=$PATH:/path/to/your/monolize_folder`
    3. 运行 `source ~/.bashrc` or `source ~/.zshrc`。

### 4. 子命令
`monolize` 使用子命令执行不同的任务：
- `monolize update`: 更新指定路径下的仓库。
- `monolize create`: 从多个子仓库创建一个新的 mono-repo。
- `monolize sync`: 同步 mono-repo 内的子模块。

---

## 3. 核心实现点（附代码示例）

### 1. Cobra 用于 CLI 命令应用
Cobra 定义了命令的结构。
- **文件**: [root.go](file:///d:/workspace/innate/use-cases/daily-use/git-monolize/cmd/root.go)
```go
var rootCmd = &cobra.Command{
    Use:   "monolize",
    Short: "A CLI tool to manage multiple git repositories",
    // ... 逻辑 ...
}
```

### 2. Viper 用于配置文件
Viper 处理从文件或环境变量加载设置。
- **文件**: [config.go](file:///d:/workspace/innate/use-cases/daily-use/git-monolize/internal/config/config.go)
```go
func Load() (*Config, error) {
    var cfg Config
    // ... 设置默认值 ...
    viper.SetDefault("path", ".")
    // ... 解析配置 ...
    if err := viper.Unmarshal(&cfg); err != nil {
        return nil, err
    }
    return &cfg, nil
}
```

### 3. 依赖管理
Go 使用 `go.mod` 跟踪依赖项。
- **文件**: [go.mod](file:///Users/patrick/workspace/innate/git-monolize/go.mod)
```go
module monolize

go 1.24.2

require (
    github.com/spf13/cobra v1.10.2
    github.com/spf13/viper v1.21.0
    // ... 其他包 ...
)
```

**常用 Go Mod 命令**:
- `go mod tidy`: 自动添加代码中使用的依赖，并删除未使用的依赖。
- `go mod vendor`: 将所有依赖项复制到项目的 `vendor` 目录中。
- `go get <package>`: 下载并安装指定的包或依赖。
- `go list -m all`: 列出当前项目的所有依赖模块。

### 4. 关键 Go 语言特性

- **基础语言特性 (类型/变量)**:
  - 示例见 [root.go](file:///Users/patrick/workspace/innate/git-monolize/cmd/root.go#L11): `var cfgFile string`
- **函数 (Functions)**:
  - Go 函数是一等公民，可以有多个返回值。
  - 示例见 [finder.go](file:///Users/patrick/workspace/innate/git-monolize/internal/git/finder.go#L11): `func FindRepositories(rootPath string) ([]string, error)`
- **结构体 (Structures)**:
  - 用于封装数据。Go 没有类（Class），而是使用结构体。
  - 示例见 [config.go](file:///Users/patrick/workspace/innate/git-monolize/internal/config/config.go#L8-L12):
    ```go
    type Config struct {
        Path          string `mapstructure:"path"`
        DefaultBranch string `mapstructure:"default_branch"`
        AutoCommit    bool   `mapstructure:"auto_commit"`
    }
    ```
- **接口 (Interfaces)**:
  - 接口定义了一组方法签名。Go 中最常见的接口是 `error`。
  - 示例见 [updater.go](file:///Users/patrick/workspace/innate/git-monolize/internal/git/updater.go#L12):
    ```go
    // UpdateRepository 返回 error 接口，调用者需处理可能发生的错误
    func UpdateRepository(repoPath string) error {
        // ...
        if err != nil {
            return fmt.Errorf("failed to get current branch: %w", err)
        }
        return nil
    }
    ```
- **包调用 (Package Calls)**:
  - 通过导入路径引用其他包，并调用其导出的（首字母大写）函数或类型。
  - `main.go` 调用 `cmd` 包中的 `Execute()`。
  - 示例见 [main.go](file:///Users/patrick/workspace/innate/git-monolize/main.go#L11): `cmd.Execute()`
- **错误处理 (Error Handling)**:
  - 示例见 [finder.go](file:///Users/patrick/workspace/innate/git-monolize/internal/git/finder.go#L22-L24):
    ```go
    entries, err := os.ReadDir(rootPath)
    if err != nil {
        return nil, err
    }
    ```
- **For 循环**:
  - 示例见 [finder.go](file:///Users/patrick/workspace/innate/git-monolize/internal/git/finder.go#L27):
    ```go
    for _, entry := range entries {
        // ... 循环体 ...
    }
    ```
- **init() 函数**:
  - 用于在 `main()` 或其他函数运行前进行初始化。
  - 示例见 [root.go](file:///Users/patrick/workspace/innate/git-monolize/cmd/root.go#L29-L34):
    ```go
    func init() {
        cobra.OnInitialize(initConfig)
        // ... 设置标志 ...
    }
    ```
